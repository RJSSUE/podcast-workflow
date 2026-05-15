---
name: podcast-normalize
description: >
  Equalize volume levels between podcast speakers by applying loudness normalization. Use when the user wants to balance host and guest audio levels — "normalize the audio", "equalize the volume", "balance the speakers", "make them the same volume", "loudness normalization". Works standalone on any audio files or as part of the full podcast pipeline.
---

# Podcast Normalize

Equalizes volume levels between podcast speakers using integrated loudness normalization (LUFS).

**Input:** One or more audio files (WAV/m4a/mp3) — per-speaker tracks or a single mixed recording
**Output:** Normalized WAV files in `podcast_output/` (e.g. `normalized_zoom1.wav`, `normalized_inperson.wav`)

---

## Setup

### Prerequisites
```bash
brew install ffmpeg   # or ensure ffmpeg is available
```

---

## When to Run

**Run early — before Round 1.** The normalized audio is what the user previews in the HTML editor and what the audio compiler cuts from. Normalizing early ensures the audio preview sounds like the final product.

---

## How It Works

Different recording setups produce different volume levels — a host on a condenser mic vs. a guest on a laptop mic, or two Zoom tracks with different gain settings. This module normalizes each track to the same integrated loudness target so they sound balanced when combined.

**Target:** -16 LUFS (integrated) — the standard for podcasts.

---

## Process

### 1. Analyze current loudness
```bash
ffmpeg -i "<input_track>" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1
```
This prints the measured input loudness, true peak, and LRA. Report these to the user so they can see the before/after difference.

### 2. Noise reduction
Remove background noise (hum, room tone, HVAC, etc.) before loudness normalization. This prevents the normalizer from boosting noise floor along with speech.

```bash
# Extract noise profile from a silent segment (first/last 2 seconds, or user-specified)
ffmpeg -i "<input_track>" -ss 0 -t 2 -y /tmp/noise_sample.wav

# Apply noise gate + highpass to remove low-frequency rumble and steady-state noise
ffmpeg -i "<input_track>" \
  -af "highpass=f=80,afftdn=nf=-25,anlmdn=s=7:p=0.002" \
  -c:a pcm_s24le -ar 48000 \
  /tmp/denoised_<name>.wav
```

If `afftdn` is not available, fall back to a simpler chain:
```bash
ffmpeg -i "<input_track>" \
  -af "highpass=f=80,lowpass=f=14000,anlmdn=s=7" \
  -c:a pcm_s24le -ar 48000 \
  /tmp/denoised_<name>.wav
```

Use the denoised file as input for the next steps.

### 3. Two-pass loudness normalization
Single-pass `loudnorm` can overshoot. Use two-pass for precision:

**Pass 1 — measure:**
```bash
ffmpeg -i /tmp/denoised_<name>.wav \
  -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json \
  -f null - 2>&1
```
Extract `measured_I`, `measured_TP`, `measured_LRA`, `measured_thresh` from JSON output.

**Pass 2 — apply with measured values:**
```bash
ffmpeg -i /tmp/denoised_<name>.wav \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=<val>:measured_TP=<val>:measured_LRA=<val>:measured_thresh=<val>:linear=true" \
  -c:a pcm_s24le -ar 48000 \
  ./podcast_output/normalized_<name>.wav
```

### 4. Force mono (if needed)
If tracks have different channel counts (stereo Zoom vs mono in-person), force all to mono to prevent concat artifacts. Add `-ac 1` to the pass 2 command.

### 5. Dynamic compression (single-track episodes)
When both speakers share a single recording (e.g. one in-person mic), use dynamic compression to equalize their levels since per-track normalization isn't possible:
```bash
ffmpeg -i ./podcast_output/normalized_<name>.wav \
  -af "compand=attacks=0.05:decays=0.3:points=-80/-80|-20/-12|0/-6:gain=2" \
  -c:a pcm_s24le \
  ./podcast_output/normalized_<name>.wav
```

### 6. Acoustic cohesion filtering (multi-track only)
When mixing tracks from very different recording environments (Zoom vs room mic), apply a baseline EQ/compression pass for more uniform sound:
```bash
ffmpeg -i normalized_<name>.wav \
  -af "highpass=f=80,lowpass=f=12000,acompressor=threshold=-20dB:ratio=3:attack=5:release=50" \
  -c:a pcm_s24le \
  ./podcast_output/normalized_<name>_eq.wav
```

### Timestamp preservation
The normalized output MUST have identical duration and timestamp alignment as the source file. All filters used (loudnorm, noise reduction, compression) are time-preserving — they modify amplitude only, not timing. Verify after normalization:
```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "<source>"
ffprobe -v error -show_entries format=duration -of csv=p=0 "./podcast_output/normalized_<name>.wav"
# Durations must match within 0.1s
```

---

## Output

Report to the user:
- Original loudness of each track (LUFS)
- Normalized loudness (-16 LUFS)
- Channel count (mono/stereo) and whether mono was forced
- File paths of normalized outputs
