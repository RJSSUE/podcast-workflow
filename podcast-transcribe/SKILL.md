---
name: podcast-transcribe
description: >
  Format raw podcast transcript files with Host/Guest speaker labels. Use when the user provides raw .txt transcript files and wants them formatted with speaker identification, or says "transcribe this", "format this transcript", "label the speakers". Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Transcribe

Formats raw auto-transcribed `.txt` files into a clean, speaker-labeled transcript.

**Input:** One or more raw `.txt` transcript files + speaker info (guest name). Input can be:
- User-provided `.txt` files (standalone use)
- ASR output from `/podcast-asr` at `podcast_output/asr_raw/asr_raw.txt` (pipeline use via `/podcast-post-production`)

**Output:** `podcast_output/transcript.txt`

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

### Get episode metadata (if not already known)
Ask for any of the following that aren't obvious from the filenames or transcript:
- **Guest name**
- **Interview language** (English or Chinese — or detect from transcript)

---

## Processing

Read `~/.claude/skills/podcast-shared/agents/transcript_processor.md` and follow its instructions.

Before spawning the transcript processor agent:
1. Read `~/.claude/skills/podcast-shared/evals/feedback_history.json` — extract `recurring_failures` array
2. Inject any recurring failures as "KNOWN ISSUES FROM PRIOR EPISODES" context

The agent handles:
- Merging multiple .txt files chronologically
- Assigning Host/Guest speaker labels
- Language detection
- Saving formatted transcript to `./podcast_output/transcript.txt`

### Transcript Correction Flow

Raw auto-transcribed text often contains severe ASR errors (wrong words, garbled names, merged speaker turns). When the user provides a corrected `edit_decision.json` with clean `host_question.edited` and `guest_answer.edited` fields:

1. **Treat the edit_decision as the authoritative text** — do NOT try to fuzzy-match corrected text back to raw ASR segments (the errors are too severe for reliable matching)
2. **Rebuild `transcript.txt`** from the edit_decision segments directly
3. **Preserve metadata** from the edit_decision: `act` sections, `source` (zoom/in-person), `is_key_moment`, `status`

This correction flow replaces the initial raw transcript entirely. The corrected version becomes the single source of truth for all downstream deliverables.

---

## Validation

After processing, validate the output:

```bash
python ~/.claude/skills/podcast-shared/scripts/validate_transcript.py \
  ./podcast_output/transcript.txt [source1.txt source2.txt] \
  --episode "<GUEST_NAME>"
```

Save the scorecard to `podcast_output/evals/scorecard_transcript.json`.
