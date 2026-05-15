---
name: podcast-audio
description: >
  Compile final edited podcast audio from an edit_decision.json and raw audio files. Use when the user provides edit decisions and wants the final audio compiled — "compile the audio", "build the final episode", "create the edited wav", "combine the audio". Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Audio

Compiles the final edited interview audio from edit decisions and raw audio tracks.

**Input:** `edit_decision.json` + audio files (WAV/m4a)
**Output:** `podcast_output/interview_edited.wav` (lossless PCM WAV, 24-bit/48kHz)

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for audio format policy and shared configuration.

### Prerequisites
```bash
brew install ffmpeg   # or ensure ffmpeg is available
pip install edge-tts --break-system-packages -q   # for TTS-regenerated segments
```

---

## Human Confirmation Required

Before starting compilation, present the user with a summary:
- Total kept segments (count)
- Any reordered segments (old -> new position)
- Any segments with muted phrases (word-level edits)
- Any TTS-regenerated segments (text was edited — these will sound different from original voice)
- Estimated output duration

Ask: "Does this look right? Reply 'go' to start audio compilation."

Do not proceed until the user confirms.

---

## Compilation Steps

### 1. Parse decisions
Read `edit_decision.json` — kept segments in final_position order, muted_ranges, text edits.

### 2. Use normalized tracks
Tracks should already be normalized in Stage 0.5 (see `/podcast-normalize`). Use `podcast_output/normalized_<name>.wav` as the source. If normalized files don't exist, run `/podcast-normalize` first.

### 3. Extract kept segments
Force mono on all segments (`-ac 1`) to prevent channel-count concat artifacts:
```bash
ffmpeg -i "./podcast_output/normalized_<speaker>.wav" \
  -ss <start_time> -to <end_time> \
  -ac 1 -c:a pcm_s24le \
  ./podcast_output/segments/seg_XXX.wav
```

### 4. Clean each segment (uses `/podcast-clean` logic)
Apply filler removal and pause trimming per segment. See `/podcast-clean` for details.

### 5. Apply muted_ranges
For each muted range, silence that audio span:
```bash
ffmpeg -i ./podcast_output/segments/seg_XXX.wav \
  -af "volume=enable='between(t,1.2,2.8)':volume=0" \
  -c:a pcm_s24le \
  ./podcast_output/segments/seg_XXX_muted.wav
```

### 6. Text-edited segments (TTS regeneration)
Regenerate with edge-tts in the matching language:
```bash
# English:
edge-tts --voice "en-US-JennyNeural" --text "<edited_text>" --write-media seg_XXX_tts.wav
# Chinese:
edge-tts --voice "zh-CN-XiaoxiaoNeural" --text "<edited_text>" --write-media seg_XXX_tts.wav
```
Flag all TTS-regenerated segments clearly.

### 7. Concatenate
```bash
ffmpeg -f concat -safe 0 \
  -i ./podcast_output/concat_list.txt \
  -c:a pcm_s24le -ar 48000 \
  ./podcast_output/interview_edited.wav
```

---

## Post-Compilation: Final Transcript

After `interview_edited.wav` is produced, generate `transcript_final.txt` — a transcript that matches the edited episode exactly.

### Process
1. Walk the kept segments from `edit_decision.json` in `final_position` order
2. For each segment, get its actual duration from the extracted WAV file:
   ```bash
   ffprobe -v error -show_entries format=duration -of csv=p=0 ./podcast_output/segments/seg_XXX.wav
   ```
3. Compute cumulative timestamps: segment N starts where segment N-1 ended
4. Use `edited_text` (not `original_text`) for each segment's content
5. Apply any `muted_ranges` — remove struck-out text from the final transcript
6. Format with speaker labels and new timestamps:
   ```
   [Host - The Try Girl] [00:00:00 - 00:01:23]
   Welcome back to the show...

   [Guest - Peter Lee] [00:01:23 - 00:03:45]
   Thanks for having me...
   ```
7. Save to `podcast_output/transcript_final.txt`

This is the authoritative text for the published episode — show notes, articles, and platform uploads reference this file.

---

## Alternative: Voice-Cloned TTS Regeneration

When source recordings come from very different environments, offer a **voice-cloned regeneration** option:

1. Use a voice cloning TTS service (ElevenLabs, Fish Audio, or OpenAI TTS) to create voice profiles from short audio samples
2. Regenerate all segments from the corrected transcript using the cloned voices
3. Save as `interview_replicated.wav` alongside `interview_edited.wav` for comparison
4. Flag clearly that the output is AI-generated voice

This is especially useful for episodes mixing free Zoom with in-person room mics.
