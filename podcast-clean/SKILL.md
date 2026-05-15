---
name: podcast-clean
description: >
  Clean podcast audio by removing filler words (口癖) and trimming long pauses. Use when the user wants cleaner audio — "remove fillers", "cut the ums", "remove 口癖", "trim pauses", "clean up the audio", "cut dead air", "remove long silences". Works standalone on any audio files or as part of the full podcast pipeline.
---

# Podcast Clean

Removes filler words (口癖) and trims long pauses from podcast audio for a smoother listening experience.

**Input:** Audio file(s) (WAV) — typically already normalized
**Output:** Cleaned audio file(s) in `podcast_output/`

---

## Setup

### Prerequisites
```bash
brew install ffmpeg
```

---

## Long Pause Trimming

Trims pauses longer than ~0.8s down to a natural breath gap (~0.3s). Does NOT eliminate all silence — short pauses between sentences are natural and important for rhythm.

### Per-segment approach
```bash
ffmpeg -i <input>.wav \
  -af "silenceremove=stop_periods=-1:stop_duration=0.8:stop_threshold=-40dB,apad=pad_dur=0.3" \
  -c:a pcm_s24le \
  <output>_trimmed.wav
```

### Full-file approach
For a single continuous file, apply the same filter:
```bash
ffmpeg -i ./podcast_output/<input>.wav \
  -af "silenceremove=stop_periods=-1:stop_duration=0.8:stop_threshold=-40dB,apad=pad_dur=0.3" \
  -c:a pcm_s24le -ar 48000 \
  ./podcast_output/<input>_clean.wav
```

**Tuning parameters:**
- `stop_duration=0.8` — pauses shorter than 0.8s are kept (natural breath). Increase for more aggressive trimming.
- `stop_threshold=-40dB` — audio below -40dB is considered silence. Adjust for noisy recordings.
- `apad=pad_dur=0.3` — inserts a 0.3s pad after each trimmed silence for natural breathing room.

---

## Filler Word Removal (口癖)

Verbal tics should be **reduced but NOT all removed** — some fillers are natural speech rhythm.

### Common fillers by language

**English:** "umm", "uhh", "uh", "you know", "you know what I mean", "like", "I mean", "basically", "actually", "right", "so"

**Chinese:** "然后", "就是", "那个", "嗯", "对", "其实", "这个", "反正"

### Guidelines
- **Cut** fillers that create stuttering or break flow (e.g., "I — umm — I think" -> "I think")
- **Keep** fillers that serve as natural transitions or thinking pauses between ideas
- **Keep** fillers that are part of the speaker's personality/cadence
- **Keep** "you know" when it's genuinely conversational, not a tic

### Method

Filler removal requires **word-level timestamps** from ASR or forced alignment. Without word-level timing, focus on pause trimming only.

**With word-level timestamps:**
1. Identify filler word spans from the transcript with timestamps
2. For each filler to remove, silence that audio span:
```bash
ffmpeg -i <input>.wav \
  -af "volume=enable='between(t,<start>,<end>)':volume=0" \
  -c:a pcm_s24le \
  <output>_defilled.wav
```
3. Then run the silence trimmer to collapse the silenced gaps

**Without word-level timestamps:**
1. Use the character-to-time ratio from the segment duration and text length as an approximation
2. Apply muting at approximate positions
3. Run silence trimmer to clean up

---

## Combined Workflow

For best results, run in this order:
1. **Filler removal** first (silence the filler spans)
2. **Pause trimming** second (collapse the silenced gaps + natural long pauses)

```bash
# Step 1: Remove fillers (creates silent gaps where fillers were)
ffmpeg -i input.wav \
  -af "volume=enable='between(t,1.2,1.8)':volume=0,volume=enable='between(t,5.3,5.9)':volume=0" \
  -c:a pcm_s24le temp_defilled.wav

# Step 2: Trim all long silences (both natural pauses and filler gaps)
ffmpeg -i temp_defilled.wav \
  -af "silenceremove=stop_periods=-1:stop_duration=0.8:stop_threshold=-40dB,apad=pad_dur=0.3" \
  -c:a pcm_s24le output_clean.wav
```

---

## Output

Report to the user:
- Original duration
- Cleaned duration
- Time saved (seconds/percentage)
- Number of pauses trimmed
- Number of fillers removed (if applicable)
