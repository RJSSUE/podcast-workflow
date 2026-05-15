---
name: podcast-videoclip
description: >
  Cut a video clip from a podcast recording, align a separate audio track, enhance video quality, generate bilingual transcripts (English + Simplified Chinese), and produce an Instagram-ready MP4 with burned-in English subtitles and a 2-second outro. Use when the user says "cut a clip", "extract this section", "clip from X to Y", "make an instagram video", "burn subtitles", or provides a video file with timestamps and an audio offset. Handles cases where video and audio come from separate files with different starting offsets.
---

# Podcast Video Clip

Four-phase workflow: plan clips from transcript → verify timestamps → batch render → subtitle.

**Phase 0 — PLAN**: Analyze transcript → suggest highlights → verify timestamps in clip_planner.html
**Phase 1 — CUT**: For each clip, extract + enhance + speed → `clip_clean.mp4` (multi-agent, parallel)
**Phase 2 — SUBTITLE**: Transcribe, align, burn subtitles → final Instagram MP4

---

## Tools

- **`clip_planner.html`** (`/Users/jrui7/Downloads/podcast/clip_planner.html`) — transcript analysis, clip selection, timestamp verification, audio alignment. Exports `clip_plan.json`.
- **`clip_editor.html`** (`/Users/jrui7/Downloads/podcast/clip_editor.html`) — per-clip segment fine-tuning, subtitle alignment, preview. Used in Phase 2.
- **`render_clean.py`** — renders the clean clip from `clip_decisions.json` (concatenate keeps + speed + intro/outro).
- **moviepy + PIL subtitle burn** — burns subtitles onto clean clip. Produces EN and/or ZH versions.

---

## Inputs

- **Video file** (MP4/MOV) — the source recording
- **Audio file** (optional) — separate audio track. If omitted, the video's own audio is used.
- **Clip name** — slug for output files (e.g. `10years_to_teach`)
- **Outro image** (PNG/JPG) — shown for 2s at the end (podcast cover art)
- **Output directory** (default: `podcast_output/clip_<name>/`)

---

## Outputs (all in output dir)

- `clip_clean.mp4` — clean video with aligned audio, speed applied, intro/outro (no subtitles)
- `clip_<name>_instagram_final.mp4` — EN subtitles burned in
- `clip_<name>_instagram_final_zh.mp4` — ZH + EN bilingual subtitles burned in
- `clip_decisions.json` — full decisions (keeps, speed, offsets, subtitles)
- `transcript_en.srt` / `transcript_zh.srt` — standalone subtitle files
- `video_enhanced.mp4` / `audio_clip.m4a` — intermediate files (optional, for debugging)

---

## Prerequisites

```bash
brew install ffmpeg
pip3 install openai-whisper moviepy pillow
```

---

## Phase 0: PLAN

Goal: from a transcript, identify highlights, verify timestamps, and produce clip_plan.json.

### 0.1 Transcript → clip_suggestions.json (in terminal)

User provides transcript text or SRT file. Claude analyzes and identifies 5–10 highlight segments:
- Emotionally resonant moments, quotable statements, clear narrative arcs, humor
- Estimate start/end timestamps from SRT timing (or mark "[verify]" if from plain text)

Output a markdown table for the user + save `clip_suggestions.json`:
```json
{
  "clips": [
    {
      "title": "10_years_before_teaching",
      "video_start": "01:57:39",
      "video_end": "02:00:24",
      "notes": "Powerful statement about mastery — quotable punchline at end",
      "phase": "plan"
    }
  ]
}
```

### 0.2 Verify & manage clips (clip_planner.html — control config)

Open `clip_planner.html` in a browser:
1. Drop in video + (optional audio) + `clip_suggestions.json`
2. If separate audio: adjust **audio offset slider** until speech syncs with lips
3. For each clip row, play to the desired start → click **[IN]** → V.Start fills, Audio Start auto-computes
4. Play to end → click **[OUT]** → V.End fills, Duration updates
5. Edit **Title** column — becomes the output folder name (`podcast_output/<title>/`)
6. Add/delete clips as needed
7. Track progress via **phase badges**: `plan → verified → cut → subtitled → rendered`
8. After subtitle work, upload each clip's `clip_decisions.json` via the **+ decisions.json** button per row
9. **Export** → downloads `clip_plan.json` (full state: timestamps, phases, embedded decisions)

Keyboard: `I` = set in, `O` = set out, `Space` = play/pause, `↑↓` = select, `←→` = seek

**clip_planner.html is the control config** — one file that tracks all clips through every pipeline phase. Re-import it anytime to see current state.

### 0.3 Export format (`clip_plan.json`)

```json
{
  "audio_offset_seconds": -2.3,
  "clips": [
    {
      "title": "10_years_before_teaching",
      "video_start": "01:57:39",
      "video_end": "02:00:24",
      "audio_start": "01:57:36",
      "duration_sec": 165,
      "notes": "Hook — powerful opening statement"
    }
  ]
}
```

---

## Phase 1: CUT (multi-agent, parallel)

Goal: for each clip in `clip_plan.json`, extract, enhance, and render a clean `clip_clean.mp4`.

When the user provides a `clip_plan.json`, spawn **one Agent per clip in parallel** (single message with multiple Agent tool calls, `run_in_background: true`).

Each agent receives a self-contained prompt:
```
You are processing clip "{title}" from a podcast recording.

Source video: {VIDEO_PATH}
Source audio: {AUDIO_PATH}  (or "use video audio" if none)
Video start: {video_start}
Video end: {video_end}
Audio start: {audio_start}
Output dir: podcast_output/{title}/

Steps:
1. mkdir -p podcast_output/{title}
2. Cut & enhance video segment (ffmpeg, no audio)
3. Cut audio segment (ffmpeg, from audio_start for same duration)
4. Merge video + audio
5. Report: "clip_clean ready at podcast_output/{title}/clip_source.mp4"

Do NOT transcribe or add subtitles — stop after merging.
```

After all agents complete, report the list of ready clips. The user then:
- Opens each in `clip_editor.html` for segment fine-tuning (if needed) or subtitle work
- Or triggers Phase 2 per clip

### 1.1 Prepare source (optional: enhance + separate audio)

If video and audio are separate files with different start offsets:

```bash
DURATION="00:03:03"

# Cut & enhance video (parallel)
ffmpeg -y -ss $VIDEO_START -t $DURATION -i "$VIDEO" -an \
  -vf "hqdn3d=4:3:6:4.5,unsharp=5:5:0.8:3:3:0.0" \
  -c:v libx264 -crf 18 -preset slow "$OUT/video_enhanced.mp4" &

# Cut audio segment (parallel)
ffmpeg -y -ss $AUDIO_START -t $DURATION -i "$AUDIO" \
  -c:a aac -b:a 192k "$OUT/audio_clip.m4a" &
wait

# Merge
ffmpeg -y -i "$OUT/video_enhanced.mp4" -i "$OUT/audio_clip.m4a" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
  "$OUT/clip_source.mp4"
```

If video already has good audio, skip this — use the video file directly as source.

**Enhancement filters (optional):**
- `hqdn3d=4:3:6:4.5` — temporal + spatial denoising
- `unsharp=5:5:0.8:3:3:0.0` — luma sharpening

### 1.2 Select segments in clip_editor.html

Open `clip_editor.html` in a browser:
1. Drop in the source video (+ optional audio, SRT, decisions)
2. Click "Open Editor"
3. Use **Mark In** (`I` key) and **Mark Out** (`O` key) to select segments
4. Drag timeline handles to fine-tune edges
5. Toggle segments on/off, adjust speed (1.0x–1.5x)
6. Hit **Preview** (`P` key) to watch the concatenated result
7. Click **Export** → downloads `clip_decisions.json`

The editor only requires the video file. Audio, subtitles, and previous decisions are all optional.

**clip_decisions.json format:**
```json
{
  "title": "You need 10 years before you teach",
  "speed": 1.25,
  "audio_offset_seconds": 0,
  "subtitle_offset_seconds": 0,
  "keeps": [
    { "start": 0.0, "end": 5.16, "label": "hook" },
    { "start": 26.17, "end": 48.28, "label": "transformation" }
  ],
  "subtitles_en": [],
  "subtitles_zh": []
}
```

### 1.3 Render clean clip

```python
# render_clean.py reads clip_decisions.json and produces clip_clean.mp4
# - Concatenates keep segments from source
# - Applies pitch-preserving speed (ffmpeg atempo/WSOLA)
# - Adds intro title card (2s) + outro cover card (2s)
# - NO subtitles
python3 render_clean.py
```

The script reads from `clip_decisions.json` in the same directory. Key config at the top:
- `SRC` — source video path
- `COVER_IMG` — outro/intro image
- `W, H` — output dimensions (detected from source, or set to 1080x1920 for Instagram)

**Output:** `clip_clean.mp4` (~60s for Instagram Reels)

---

## Phase 2: SUBTITLE

Goal: transcribe the clean clip and burn in aligned subtitles.

### 2.1 Transcribe (Whisper)

```python
import whisper, json

model = whisper.load_model("small.en")  # or "medium.en" for noisy audio
result = model.transcribe("clip_clean.mp4", language="en", word_timestamps=True)

# Save raw JSON
with open("clip_clean_whisper.json", "w") as f:
    json.dump(result["segments"], f, indent=2)

# Generate SRT
def ts(sec):
    h,m,s,ms = int(sec//3600),int((sec%3600)//60),int(sec%60),int((sec-int(sec))*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

srt = []
for i, seg in enumerate(result["segments"], 1):
    srt += [str(i), f"{ts(seg['start'])} --> {ts(seg['end'])}", seg["text"].strip(), ""]

with open("clip_clean_en.srt", "w") as f:
    f.write("\n".join(srt))
```

**Model choice:** `small.en` balances speed and accuracy. Use `medium.en` for heavy accents or noisy recordings. Avoid `base` — it misses words.

### 2.2 Translate to Chinese

```bash
cat clip_clean_en.srt | claude -p "Translate each subtitle to Simplified Chinese (简体中文). \
Keep the SRT format with identical timestamps. Natural, conversational tone. \
Output only the SRT." > clip_clean_zh.srt
```

Or translate per-segment via JSON for more control:

```python
import subprocess, json, re

with open("clip_clean_whisper.json") as f:
    segments = json.load(f)

seg_texts = json.dumps([s["text"].strip() for s in segments], ensure_ascii=False)
prompt = f"""Translate each English subtitle to Simplified Chinese (简体中文).
Return ONLY a JSON array of strings, same count and order, concise subtitle length.

{seg_texts}"""

result = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True)
zh_segs = json.loads(re.search(r'\[.*\]', result.stdout.strip(), re.DOTALL).group())

srt = []
for i, (seg, zh) in enumerate(zip(segments, zh_segs), 1):
    srt += [str(i), f"{ts(seg['start'])} --> {ts(seg['end'])}", zh, ""]

with open("clip_clean_zh.srt", "w", encoding="utf-8") as f:
    f.write("\n".join(srt))
```

### 2.3 Align subtitles in clip_editor.html

Open `clip_editor.html` again:
1. Drop in `clip_clean.mp4` (video only — no separate audio needed)
2. Optionally drop in `clip_clean_en.srt` and/or `clip_clean_zh.srt`
3. Or drop in a decisions JSON that already has subtitles
4. Switch to **Subtitles** tab → edit text, adjust individual timestamps
5. Use **sub offset** slider for global alignment
6. Toggle **CC** button to preview overlay on video
7. Switch between **EN** / **中文** tabs — both are fully editable
8. **Export** → downloads decisions with subtitles baked to the correct timeline

The export bakes the subtitle offset into timestamps (so `subtitle_offset_seconds` is always 0 in the output). This means the exported subtitles work directly with the target video.

### 2.4 Render final with subtitles

Burn subtitles onto `clip_clean.mp4`:

```python
import json, numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip

SRC = "clip_clean.mp4"
W, H = 1080, 1920  # or detect from source
FONT_EN = "/System/Library/Fonts/Avenir Next Condensed.ttc"
FONT_ZH = "/System/Library/Fonts/STHeiti Light.ttc"
BOTTOM_MARGIN = 200

with open("clip_decisions.json") as f:
    data = json.load(f)

# --- EN version ---
def make_sub_en(text):
    font_size, stroke_w, pad = 60, 4, 24
    max_w = W - pad * 2
    font = ImageFont.truetype(FONT_EN, font_size, index=4)
    dummy = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    # Word-wrap
    words, lines, cur = text.split(), [], []
    for w in words:
        test = ' '.join(cur + [w])
        bx = dummy.textbbox((0, 0), test, font=font, stroke_width=stroke_w)
        if bx[2] - bx[0] > max_w and cur:
            lines.append(' '.join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur: lines.append(' '.join(cur))
    # Render
    lh = font_size + stroke_w * 2 + 8
    img = Image.new('RGBA', (W, lh * len(lines) + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = pad
    for line in lines:
        bx = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)
        x = (W - (bx[2] - bx[0])) // 2
        draw.text((x, y), line, font=font, fill=(0,0,0,255),
                  stroke_width=stroke_w, stroke_fill=(0,0,0,255))
        draw.text((x, y), line, font=font, fill=(255,255,255,255))
        y += lh
    return np.array(img)

def render_with_subs(subs, out_path, make_img_fn):
    video = VideoFileClip(SRC)
    sub_clips = []
    for sub in subs:
        arr = make_img_fn(sub['text'])
        sh = arr.shape[0]
        sub_clips.append(
            ImageClip(arr, is_mask=False)
            .with_start(sub['start'])
            .with_duration(sub['end'] - sub['start'])
            .with_position(('center', H - sh - BOTTOM_MARGIN))
        )
    final = CompositeVideoClip([video] + sub_clips, size=(W, H))
    final = final.with_audio(video.audio)
    final.write_videofile(out_path, fps=30, codec='libx264', audio_codec='aac',
                          bitrate='4000k', audio_bitrate='192k', threads=4, logger=None)
    video.close(); final.close()

render_with_subs(data['subtitles_en'], 'clip_instagram_final.mp4', make_sub_en)
# render_with_subs(data['subtitles_zh'], 'clip_instagram_final_zh.mp4', make_sub_zh)
```

**ZH subtitle style:** Yellow text (255, 220, 0), STHeiti font, 52px, with smaller EN text below in gray. See `render_60s.py` for the bilingual `make_sub_zh()` function.

---

## Key Decisions

| Decision | Default | Notes |
|----------|---------|-------|
| Speed | 1.25x | Pitch-preserving via ffmpeg atempo/WSOLA. 1.0x for normal speed. |
| Dimensions | Detect from source | Override to 1080x1920 for Instagram portrait |
| Whisper model | `small.en` | `medium.en` for noisy audio; avoid `base` |
| Intro card | 2s, title text + logo | Set in render_clean.py |
| Outro card | 2s, cover image | Podcast cover art, full-frame |
| Subtitle font | Avenir Next Condensed Bold, 60px | White with 4px black stroke |
| Bottom margin | 200px | Distance from frame bottom to subtitle baseline |

---

## Quick Reference: Full Pipeline

```
transcript.srt
    │
    ├─ [Phase 0.1] /podcast-videoclip in terminal → clip_suggestions.json
    │
    ├─ [Phase 0.2] clip_planner.html (video + audio + suggestions)
    │              → verify timestamps, set titles → clip_plan.json
    │
source_video.mp4 + clip_plan.json
    │
    ├─ [Phase 1] multi-agent per clip → podcast_output/<title>/clip_source.mp4
    │
    ├─ [Phase 1.2-1.3] clip_editor.html per clip → clip_decisions.json → render_clean.py → clip_clean.mp4
    │
    ├─ [Phase 2.1] Whisper → clip_clean_en.srt
    │
    ├─ [Phase 2.2] Claude → clip_clean_zh.srt
    │
    ├─ [Phase 2.3] clip_editor.html → clip_decisions.json (+ subtitles)
    │
    ├─ [Phase 2.4] Bake subtitles:  intro (title card) → main clip (EN or EN+ZH) → outro (cover)
    │              → clip_instagram_final.mp4 (EN)
    │              → clip_instagram_final_zh.mp4 (ZH+EN)
    │
    └─ [Control] clip_planner.html tracks all clips through all phases
                 Upload clip_decisions.json per clip → export full clip_plan.json
```

---

## Pitfalls

1. **Separate audio alignment**: When video and audio come from different recordings, the user provides both timestamps. Fine-tune with the audio offset slider in clip_editor.html.
2. **Subtitle offset is baked on export**: The editor bakes `subtitle_offset_seconds` into the timestamps when exporting. Imported decisions always have offset=0 and absolute times.
3. **Re-transcribe after cutting**: Don't try to remap original SRT timestamps to the cut timeline. Transcribe `clip_clean.mp4` directly — Whisper produces perfectly aligned timestamps.
4. **moviepy instead of ffmpeg drawtext**: This ffmpeg build (Homebrew) lacks `drawtext`/`libass`. The moviepy + PIL approach works universally.
5. **Speed affects duration math**: The editor's header shows estimated final duration accounting for speed + 4s (intro/outro). Target ~60s for Instagram Reels, ~90s for longer clips.
6. **Outro silence**: `AudioArrayClip(np.zeros(...))` ensures the outro card has a silent audio track — platforms reject files where audio ends before video.
7. **Video dimensions vary**: The source might be 1080x1920 (portrait), 1080x1440 (4:3), or 1920x1080 (landscape). The render scripts and subtitle rendering should use the actual dimensions, not hardcoded values.
