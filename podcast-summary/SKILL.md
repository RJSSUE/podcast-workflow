---
name: podcast-summary
description: >
  Generate an AI summary audio in the opposite language from the interview. Use when the user wants a spoken summary for the cross-language show — "generate the Chinese summary", "create the AI summary audio", "make the summary for 舞所不谈". Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Summary

Generates a 3-5 minute spoken summary of the interview in the opposite language, for the cross-language show.

**Input:** Edited transcript + interview language
**Output:** `podcast_output/summary_XX.txt` + `podcast_output/summary_audio_XX.wav`

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for language logic, TTS voice options, and shared configuration.

### Prerequisites
```bash
pip install edge-tts --break-system-packages -q
```

---

## Step 1 — Write the Summary Script

Based on the edited transcript, write a **3-5 minute spoken summary** that captures:
- Who the guest is and their dance background
- 3-5 key stories or insights from the interview
- A compelling closing that invites listeners to hear the full episode

Write in the **target language** (opposite of interview language):
- English interview -> Chinese summary (`summary_zh.txt`)
- Chinese interview -> English summary (`summary_en.txt`)

Save to `./podcast_output/summary_XX.txt`.

---

## Step 2 — Generate Audio with edge-tts

```bash
# English summary:
edge-tts --voice "en-US-JennyNeural" \
  --text "$(cat ./podcast_output/summary_en.txt)" \
  --write-media ./podcast_output/summary_audio_en.wav

# Chinese summary:
edge-tts --voice "zh-CN-XiaoxiaoNeural" \
  --text "$(cat ./podcast_output/summary_zh.txt)" \
  --write-media ./podcast_output/summary_audio_zh.wav
```
