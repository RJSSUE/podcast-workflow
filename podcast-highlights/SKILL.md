---
name: podcast-highlights
description: >
  Create highlight video clips from podcast recordings. Use when the user wants clips, highlights, reels, or short-form content from podcast video — "cut a clip", "make a highlight", "create a reel", "extract that section", "clip where they talked about X". Takes video + processed audio + transcript, cuts clips at specified sections, replaces audio track, and generates subtitle files.
---

# Podcast Highlights

Cuts highlight video clips from podcast recordings with processed audio and subtitle support.

**Input:** Video file (MP4/MOV), processed audio (WAV), transcript with timestamps, highlight sections to extract
**Output:** `podcast_output/highlight_<name>.mp4` + `podcast_output/srt_<name>.srt` per clip

---

## Setup

### Prerequisites
```bash
brew install ffmpeg
```

### Optional (for burned-in subtitles)
```bash
brew install libass
# Then rebuild ffmpeg with --enable-libass
```

Without `libass`, subtitles are provided as sidecar `.srt` files (works with most players and platforms like YouTube, Instagram).

---

## Workflow

### 1. Identify highlight sections from transcript

Search the formatted transcript for the requested topic/moment. Record:
- **Start timestamp** — where the section begins (from `[HH:MM:SS]` in transcript)
- **End timestamp** — where the section naturally concludes
- **Transcript lines** — the line range for subtitle generation
- **Clip name** — descriptive slug (e.g., `36chambers`, `innerchild`, `origin_story`)

**Tips for finding good clip boundaries:**
- Start 1-2 segments before the core content for context (e.g., include the host's question)
- End at a natural conclusion — a laugh, a summary statement, or a pause
- Ideal clip length: 1-5 minutes for social media, up to 10 minutes for YouTube
- Avoid cutting mid-sentence

### 2. Generate SRT subtitle files

Create an SRT file for each clip with timestamps zeroed to the clip start:

```
1
00:00:00,000 --> 00:00:05,000
Speaker: First line of dialogue.

2
00:00:05,000 --> 00:00:10,000
Speaker: Second line of dialogue.
```

**Rules:**
- Subtract the clip's start timestamp from each segment timestamp to zero-base them
- Keep lines to ~2 lines max per subtitle entry (split long segments)
- Include speaker labels for multi-speaker clips
- Use segment timestamps from the transcript for timing

**Output:** `podcast_output/srt_<clip_name>.srt`

### 3. Cut video clips with processed audio

Use the **normalized (not pause-trimmed)** audio to keep timestamps in sync with the video.

```bash
ffmpeg -ss <START> -to <END> \
  -i "<VIDEO_FILE>" \
  -ss <START> -to <END> \
  -i "<PROCESSED_AUDIO_WAV>" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 192k \
  -shortest \
  "podcast_output/highlight_<clip_name>.mp4" \
  -y
```

**Key parameters:**
- `-ss` before each `-i` enables fast seeking (avoids decoding from start)
- Both inputs need the same `-ss`/`-to` to stay in sync
- `-map 0:v:0 -map 1:a:0` takes video from input 0, audio from input 1
- `-shortest` ensures the output matches the shorter stream
- `CRF 20` balances quality vs file size for social media clips

**Why not pause-trimmed audio:** Pause trimming removes silence and shifts all timestamps, breaking sync with the video. Always use the denoised+normalized audio (before pause trimming) for video clips.

### 4. Burn in subtitles (if libass available)

```bash
ffmpeg -ss <START> -to <END> \
  -i "<VIDEO_FILE>" \
  -ss <START> -to <END> \
  -i "<PROCESSED_AUDIO_WAV>" \
  -filter_complex "[0:v]subtitles=filename='<SRT_PATH>':force_style='FontSize=14\,FontName=Arial\,PrimaryColour=&H00FFFFFF\,OutlineColour=&H00000000\,Outline=2\,Shadow=1\,MarginV=30'[v]" \
  -map "[v]" -map 1:a:0 \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 192k \
  -shortest \
  "podcast_output/highlight_<clip_name>.mp4" \
  -y
```

**Note:** Commas in `force_style` must be escaped as `\,` to avoid ffmpeg filter parsing issues.

**Check if subtitles filter is available:**
```bash
ffmpeg -filters 2>/dev/null | grep subtitles
```

If not available, deliver the `.srt` files as sidecar subtitles instead.

### 5. Verify clips

```bash
# Check duration and file size
ffprobe -v quiet -show_entries format=duration,size \
  -of default=noprint_wrappers=1 \
  "podcast_output/highlight_<clip_name>.mp4"
```

---

## Complete Example

```bash
# 1. Identify sections (from formatted transcript)
# 36 Chambers story: 00:35:22 - 00:40:52 (5m30s)
# Inner child talk:  01:08:38 - 01:11:31 (2m53s)

# 2. Generate SRT files (see format above)
# → podcast_output/srt_36chambers.srt
# → podcast_output/srt_innerchild.srt

# 3. Cut clips with processed audio
ffmpeg -ss 00:35:22 -to 00:40:52 \
  -i "video_enhanced.mp4" \
  -ss 00:35:22 -to 00:40:52 \
  -i "podcast_output/audio_normalized.wav" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 192k -shortest \
  "podcast_output/highlight_36chambers.mp4" -y

# 4. Verify
ffprobe -v quiet -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 \
  "podcast_output/highlight_36chambers.mp4"
```

---

## Delivery

Report to the user for each clip:
- Clip name and topic
- Duration
- File size
- Whether subtitles are burned in or sidecar `.srt`
- File paths for video and subtitle files

---

## Known Pitfalls

1. **Audio/video sync**: Always use non-pause-trimmed audio. Pause trimming shifts timestamps and breaks sync.
2. **Subtitle filter missing**: `subtitles` filter requires `libass`. Check with `ffmpeg -filters | grep subtitles`. Fall back to sidecar `.srt` files.
3. **Force_style escaping**: Commas in ffmpeg's `force_style` parameter must be escaped as `\,` or the filter parser treats them as parameter separators.
4. **Dual -ss for two inputs**: Both `-i` inputs need their own `-ss`/`-to` flags. Without this, the audio stream won't seek and will be out of sync.
5. **Proportional timestamps**: If transcript timestamps were estimated proportionally (not from ASR word-level timing), clip boundaries may be slightly off. Add a few seconds of buffer on each side.
