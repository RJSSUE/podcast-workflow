---
name: podcast-post-production
description: >
  Full post-production pipeline for The Try Girl's two podcast shows — 舞所不谈 (Chinese platform) and Dance Chat (Apple Podcasts). Use this skill whenever the user provides raw audio files from a podcast interview and wants the complete end-to-end workflow. The user only needs to provide audio file(s) and guest name — ASR transcription is handled automatically. Trigger on: "process this episode", "produce the podcast", "full post-production", or any request for the complete pipeline. For individual tasks (just transcribe, just normalize, just write show notes), use the standalone module skills instead.
---

# Podcast Post-Production — Orchestrator

Chains all podcast module skills into the full end-to-end pipeline. Each module can also be invoked standalone — see individual skill descriptions.

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults, language logic, and audio format policy.

---

## Pipeline Overview

```
Stage 0 (sequential):
  /podcast-asr         →  asr_raw.txt + asr_metadata.json
  /podcast-normalize   →  normalized_<name>.wav (denoise + equalize + timestamp-matched)

Round 1 (concurrent):
  /podcast-transcribe  →  transcript.txt
  /podcast-storyline   →  edit_proposal.md
  /podcast-editor      →  edit_review.html

  ⏸ PAUSE — user reviews HTML editor (audio preview uses normalized file), returns edit_decision.json

Round 2 (sequential + concurrent):
  /podcast-audio       →  interview_edited.wav  (cuts from normalized tracks, uses /podcast-clean internally)
  /podcast-transcript-sync → transcript_final.txt (timestamps aligned to edited audio)
  /podcast-summary     →  summary_audio_XX.wav
  ── then concurrently ──
  /podcast-articles    →  article_en.md + article_zh.md
  /podcast-shownotes   →  shownotes_en.md + shownotes_zh.md
  /podcast-instagram   →  instagram_post.txt
```

---

## Step 0 — Setup & Validation

### Locate input files
The user will provide:
- One or more **audio files** (`.m4a`, `.mp3`, `.wav`) — typically 2–3 tracks (Zoom per-speaker or sequential splits, plus optional in-person mic)
- Optionally, **transcript files** (`.txt`) — if provided, skip Stage 0 (ASR) and go directly to Round 1

Confirm all files exist. Ask the user to clarify which audio track belongs to which speaker if not obvious from filenames.

### Get episode metadata
Ask for anything not obvious from filenames/transcript:
- **Guest name** (required)
- **Host name** (defaults to "The Try Girl")
- **Interview language** (English or Chinese — or auto-detected by ASR)

### Install dependencies (if missing)
```bash
python3 -c "import whisper" 2>/dev/null || pip install openai-whisper --break-system-packages -q
pip install edge-tts --break-system-packages -q
brew install ffmpeg
```

---

## Stage 0 — ASR (Automatic Speech Recognition)

**Skip this stage if** the user provided `.txt` transcript files — go directly to Round 1.

Run `/podcast-asr` to transcribe audio files to text:
- Input: audio file(s) + speaker names
- Output: `podcast_output/asr_raw/asr_raw.txt` + `podcast_output/asr_raw/asr_metadata.json`
- Whisper model: `medium` by default (user can override)

After ASR completes, validate:
```bash
python ~/.claude/skills/podcast-shared/scripts/validate_asr.py \
  ./podcast_output/asr_raw/asr_raw.txt \
  --audio "path/to/audio.m4a" \
  --episode "<GUEST_NAME>"
```

The `asr_raw.txt` file becomes the input for `/podcast-transcribe` in Round 1.
The `asr_metadata.json` provides language detection and speaker names for downstream modules.

---

## Stage 0.5 — Audio Normalization (before Round 1)

**Run immediately after Stage 0** (or after setup if ASR was skipped). The normalized audio becomes the single source file for all downstream use — both the HTML editor's audio preview and the final audio compilation.

Run `/podcast-normalize` on each source audio file:
- Denoise (remove background hum, room tone, HVAC)
- Two-pass loudness normalization to -16 LUFS
- Dynamic compression for single-track episodes (both speakers on one mic)
- Force mono if needed
- Output: `podcast_output/normalized_<name>.wav`

**Verify timestamp preservation** — normalized file duration must match source within 0.1s. All segment timestamps in the transcript remain valid against the normalized file.

```bash
# Quick duration check
ffprobe -v error -show_entries format=duration -of csv=p=0 "<source_audio>"
ffprobe -v error -show_entries format=duration -of csv=p=0 "./podcast_output/normalized_<name>.wav"
```

The normalized file is what users should load in the HTML editor's audio preview, and what `/podcast-audio` cuts segments from in Round 2.

---

## Round 1 — Transcript + Story + Editor

### Input source
- If Stage 0 ran: use `podcast_output/asr_raw/asr_raw.txt` as the raw transcript input
- If user provided `.txt` files: use those directly

### Preparation
1. Read `~/.claude/skills/podcast-shared/evals/feedback_history.json` — extract `recurring_failures` array
2. For each sub-agent, inject recurring failures as "KNOWN ISSUES FROM PRIOR EPISODES" context
3. Pass speaker names (from `asr_metadata.json` or user input) to all agents

### Launch concurrently

Spawn 3 agents in parallel — they are independent:

| Module | Skill | Agent definition | Output |
|--------|-------|-----------------|--------|
| Transcript | `/podcast-transcribe` | `podcast-shared/agents/transcript_processor.md` | `podcast_output/transcript.txt` |
| Storyline | `/podcast-storyline` | `podcast-shared/agents/story_analyst.md` | `podcast_output/edit_proposal.md` |
| Editor | `/podcast-editor` | `podcast-shared/agents/html_editor_builder.md` | `podcast_output/edit_review.html` |

### Post-completion evaluation

After each agent finishes, validate its output:

```bash
# Transcript
python ~/.claude/skills/podcast-shared/scripts/validate_transcript.py \
  ./podcast_output/transcript.txt [source1.txt source2.txt] --episode "<NAME>"

# Edit proposal
python ~/.claude/skills/podcast-shared/scripts/validate_edit_proposal.py \
  ./podcast_output/edit_proposal.md --episode "<NAME>"

# HTML editor
python ~/.claude/skills/podcast-shared/scripts/validate_html.py \
  ./podcast_output/edit_review.html --episode "<NAME>" --expected-segments <N>
```

Save scorecards to `podcast_output/evals/scorecard_<agent>.json`.

Optionally spawn the grader agent (`podcast-shared/agents/grader.md`) for human-judgment metrics, then aggregate:

```bash
python ~/.claude/skills/podcast-shared/scripts/aggregate_scores.py \
  ./podcast_output/evals --episode "<NAME>" \
  --history-path ~/.claude/skills/podcast-shared/evals/feedback_history.json
```

Evaluation does NOT gate delivery — outputs go to the user immediately.

### Notify user

Play a notification sound when all 3 Round 1 agents have completed:

```bash
ffplay -nodisp -autoexit -t 2 "/Users/jrui7/Downloads/podcast/片头片尾.mp3" 2>/dev/null &
```

### Deliver Round 1

Present to the user:
1. `transcript.txt` — formatted Host/Guest transcript
2. `edit_review.html` — interactive editor (tell user to open in browser)
3. Edit proposal summary — inline in chat

> "Open the HTML file in your browser to review your edits. Drag segments to reorder, strike out words or phrases, or split segments. When ready, click **Export Edit Decision** and send me the `edit_decision.json`."

**PAUSE — wait for `edit_decision.json` before proceeding to Round 2.**

---

## Round 2 — Audio + Content

When the user provides `edit_decision.json`:

### Audio pipeline (sequential)

1. **Compile audio** — `/podcast-audio`
   - Parse edit decisions, extract kept segments from **already-normalized** tracks (from Stage 0.5)
   - Apply `/podcast-clean` per segment (filler removal + pause trimming)
   - Apply muted ranges, handle TTS-regenerated segments
   - Concatenate to `interview_edited.wav`
   - **Requires human confirmation before rendering** (see `/podcast-audio` for confirmation flow)

2. **Generate final transcript** — `/podcast-transcript-sync`
   - Build a new transcript aligned to `interview_edited.wav`
   - Walk the kept segments in final order, compute cumulative timestamps based on each segment's actual duration in the edited audio
   - Format: same Host/Guest speaker labels as `transcript.txt`, but with timestamps matching the final episode
   - Output: `podcast_output/transcript_final.txt`
   - This transcript is used by `/podcast-shownotes` for chapter timestamps, by platform uploads that require synced transcripts, and as the authoritative text reference for the published episode

3. **AI summary** — `/podcast-summary`
   - Write 3–5 min summary script in the opposite language
   - Generate audio with edge-tts → `summary_audio_XX.wav`

### Content generation (concurrent, after audio)

Launch these 3 concurrently — they are independent:

| Module | Skill | Output |
|--------|-------|--------|
| Articles | `/podcast-articles` | `article_en.md` + `article_zh.md` |
| Show notes | `/podcast-shownotes` | `shownotes_en.md` + `shownotes_zh.md` |
| Instagram | `/podcast-instagram` | `instagram_post.txt` |

### Deliver Round 2

Present all files:
1. `interview_edited.wav`
2. `transcript_final.txt` — synced transcript matching the edited audio
3. `summary_audio_[lang].wav`
4. `article_en.md` + `article_zh.md`
5. `shownotes_en.md` + `shownotes_zh.md`
6. `instagram_post.txt`

Note any segments that were TTS-regenerated due to text edits.

---

## Transcript Correction Flow

When the user provides a corrected `edit_decision.json` with clean `host_question.edited` and `guest_answer.edited` fields:

1. Treat the edit_decision as the authoritative text (raw ASR errors are too severe for fuzzy matching)
2. Rebuild `transcript.txt` using `/podcast-transcribe` correction mode
3. Rebuild `edit_review.html` using `/podcast-editor` with the corrected segment data
4. Preserve metadata: `act` sections, `source`, `is_key_moment`, `status`

---

## Feedback Loop (3 tiers)

- **Tier 1 — Context injection** (every episode): Inject `recurring_failures` into agent prompts before spawning. Automatic.
- **Tier 2 — Agent definition updates** (after 3+ episodes): If a metric fails in >=2 of last 5 episodes, propose updating the relevant agent `.md` file. User approves first.
- **Tier 3 — Skill updates** (rare): Fundamental pipeline design gaps flagged for user review.

See `podcast-shared/references/eval_schemas.md` for JSON schema details.

---

## Available Modules (standalone)

Each module can be invoked independently:

| Skill | What it does |
|-------|-------------|
| `/podcast-asr` | Transcribe audio files to timestamped text (Whisper) |
| `/podcast-transcribe` | Format raw transcript with Host/Guest labels |
| `/podcast-storyline` | Analyze story arc, propose edit plan |
| `/podcast-editor` | Build interactive HTML transcript editor |
| `/podcast-normalize` | Equalize speaker volume levels (-16 LUFS) |
| `/podcast-clean` | Remove fillers (口癖) and trim long pauses |
| `/podcast-audio` | Compile final edited audio from edit decisions |
| `/podcast-summary` | Generate AI summary audio in the other language |
| `/podcast-articles` | Write bilingual feature articles |
| `/podcast-shownotes` | Generate show notes for both platforms |
| `/podcast-instagram` | Write Instagram captions + hashtags |

---

## Notes & Edge Cases

- **Multi-track alignment**: Use a shared audio event (clap, start phrase) to sync misaligned tracks before cutting.
- **Code-switching interviews** (English/Chinese mixed): Transcribe as-is. Produce full bilingual deliverables regardless.
- **No guest name provided**: Ask before writing any content.
- **Long interviews (>90 min)**: Warn the user — processing takes longer.
- **Music / intro / outro**: Mark as `[INTRO MUSIC]` / `[OUTRO MUSIC]` in transcript.
- **In-person track**: Quality reference or ambient layer, not primary cut source.
