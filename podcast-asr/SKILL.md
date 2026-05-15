---
name: podcast-asr
description: >
  Transcribe raw podcast audio files to timestamped text using OpenAI Whisper. Use when the user provides audio files (.m4a, .mp3, .wav) and needs speech-to-text before formatting. Trigger on: "transcribe this audio", "ASR this file", or automatically as Stage 0 in the full podcast-post-production pipeline. Works standalone or as the first step in the pipeline.
---

# Podcast ASR

Transcribes raw audio files into timestamped text using OpenAI Whisper (local).

**Input:** One or more audio files (`.m4a`, `.mp3`, `.wav`) + speaker names (host + guest)
**Output:** `podcast_output/asr_raw/asr_raw.txt` + `podcast_output/asr_raw/asr_metadata.json`

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

### Dependencies

```bash
python3 -c "import whisper" 2>/dev/null || pip install openai-whisper --break-system-packages -q
brew list ffmpeg &>/dev/null || brew install ffmpeg
```

### Get episode metadata (if not already known)
- **Guest name** (required)
- **Host name** (defaults to "The Try Girl" from config)
- **Whisper model** (defaults to `medium` — best accuracy/speed tradeoff on CPU; user can request `base`, `small`, `large`, or `turbo`)

---

## Processing

### 1. Detect audio file layout

Determine whether the provided audio files are:
- **Sequential Zoom splits** — filenames like `Name Zoom 1.m4a`, `Name Zoom 2.m4a` (40-min free-tier limit). Both contain all speakers. Process sequentially, offset timestamps.
- **Per-speaker tracks** — separate files per speaker from paid Zoom. Process independently.
- **Single file** — one recording with all speakers.

### 2. Run Whisper ASR

For each audio file, run Whisper:

```python
import whisper
import json
import os

model = whisper.load_model("medium")  # or user-specified model

# For sequential files, track cumulative offset
cumulative_offset = 0.0
all_segments = []
detected_language = None

for audio_path in audio_files:  # sorted by filename/number
    result = model.transcribe(audio_path, language=None, verbose=False)

    if detected_language is None:
        detected_language = result["language"]

    for seg in result["segments"]:
        all_segments.append({
            "start": seg["start"] + cumulative_offset,
            "end": seg["end"] + cumulative_offset,
            "text": seg["text"].strip(),
            "source_file": os.path.basename(audio_path)
        })

    # Get duration of this file for offset calculation
    cumulative_offset += result["segments"][-1]["end"] if result["segments"] else 0
```

### 3. Write outputs

Create `podcast_output/asr_raw/` directory.

**`asr_raw.txt`** — one segment per line, timestamped:
```
[00:00 - 00:04] I'm going to start recording.
[00:04 - 00:09] And also another thing maybe because this is like Zoom 3 version...
[00:09 - 00:11] to like a 40 minute.
```

Format: `[MM:SS - MM:SS] text` (minutes:seconds for both start and end).

For interviews longer than 60 minutes, use `[HH:MM:SS - HH:MM:SS]` format.

**`asr_metadata.json`**:
```json
{
  "model": "medium",
  "language": "en",
  "duration_seconds": 2056.7,
  "segment_count": 408,
  "audio_files": ["Melanie Zoom 1.m4a"],
  "layout": "single",
  "host_name": "The Try Girl",
  "guest_name": "Melanie"
}
```

### 4. Multi-file timestamp handling

For **sequential Zoom splits**:
- Process files in filename order (Zoom 1, Zoom 2, etc.)
- Add the previous file's duration as offset to all subsequent timestamps
- Note file boundaries in `asr_raw.txt` with a marker: `=== [Source: Zoom 2.m4a, offset: 34:16] ===`

For **per-speaker tracks**:
- Process each track independently
- Interleave segments by timestamp in the final `asr_raw.txt`
- Tag each segment with its source in `asr_metadata.json`

---

## Validation

After processing, validate the output:

```bash
python ~/.claude/skills/podcast-shared/scripts/validate_asr.py \
  ./podcast_output/asr_raw/asr_raw.txt \
  --audio "path/to/audio.m4a" \
  --episode "<GUEST_NAME>"
```

Save the scorecard to `podcast_output/evals/scorecard_asr.json`.

---

## Downstream Handoff

The `asr_raw.txt` file is consumed by `/podcast-transcribe` as its input. The transcript processor agent will:
1. Read `asr_raw.txt` as the raw text source
2. Assign Host/Guest speaker labels using content heuristics + provided names
3. Output the formatted `transcript.txt`

The `asr_metadata.json` is consumed by `/podcast-post-production` orchestrator for:
- Passing speaker names to downstream skills
- Language detection (determines bilingual content direction)
- Duration awareness (warn if >90 min)

---

## Notes

- **CPU performance:** `medium` model processes ~34 min audio in ~3-5 min on Apple Silicon, ~8-15 min on Intel. The `base` model is 5x faster but less accurate on proper nouns.
- **Proper noun accuracy:** Whisper struggles with names, studios, and dance terms. These get corrected in the HTML editor review step — don't try to fix them here.
- **Language detection:** Whisper auto-detects. For code-switching interviews (mixed English/Chinese), it picks the dominant language. Override with `language="en"` or `language="zh"` if detection is wrong.
- **Memory:** `medium` model needs ~5GB RAM. `large` needs ~10GB. If memory is tight, fall back to `small`.
