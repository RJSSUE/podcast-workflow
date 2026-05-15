# Podcast Shared Configuration

Shared defaults for all podcast modules. Each module SKILL.md references this file.

---

## Show Defaults

| Field | Value |
|-------|-------|
| Show name | YOUR_SHOW_NAME |
| Host name | YOUR_HOST_NAME |
| Publication credit | YOUR_HOST_NAME |
| Platform | Apple Podcasts |

Use these everywhere — transcripts, articles, show notes, Instagram — unless the user overrides for a specific episode.

> **Setup:** Replace `YOUR_SHOW_NAME` and `YOUR_HOST_NAME` above with your actual show name and host name after installation.

---

## Two-Show Language Logic (Optional)

If you produce bilingual shows, the two shows can mirror each other: each publishes the native-language interview plus an AI-generated version in the other language.

| Interview language | Primary show | AI-generated version |
|---|---|---|
| **English** | YOUR_ENGLISH_SHOW | YOUR_OTHER_LANGUAGE_SHOW (AI summary audio + written content) |
| **Other language** | YOUR_OTHER_LANGUAGE_SHOW | YOUR_ENGLISH_SHOW (English AI summary audio + written content) |

Detect interview language from the provided transcript. This determines which show gets the "primary" deliverables vs the "AI summary" deliverables.

> **Note:** If you only produce one show, you can remove this section.

---

## Audio Format Policy

All audio outputs use **lossless PCM WAV (24-bit / 48kHz)**. Preserve original quality through every edit. If the user later needs a compressed format for platform upload, offer a separate compressed copy on request — never make it the default.

**Loudness target:** -16 LUFS (integrated), TP -1.5 dB, LRA 11 dB — the standard for podcasts.

For multi-track recordings, use the per-speaker Zoom tracks (not the room mic) as the primary source for audio extraction. The in-person track can serve as a quality reference or fallback.

---

## TTS Voice Options

| Language | Female | Male |
|----------|--------|------|
| English | `en-US-JennyNeural` | `en-US-GuyNeural` |
| Chinese | `zh-CN-XiaoxiaoNeural` | `zh-CN-YunxiNeural` |

---

## Dependencies

```bash
pip install edge-tts --break-system-packages -q
brew install ffmpeg   # or: pip install ffmpeg-python
```

---

## Multi-Track Convention

- `[Name] Zoom 1.m4a` — first speaker's Zoom track (often host) or first free-tier split
- `[Name] Zoom 2.m4a` — second speaker's Zoom track (often guest) or second free-tier split
- `[Name] in-person.m4a` — room/ambient mic (backup or blended reference)

**Zoom free-tier splits:** Two consecutive Zoom files are sequential recordings (40-min limit), NOT per-speaker tracks. Both contain all speakers.

---

## Shared Resource Paths

All paths relative to `~/.claude/skills/podcast-shared/`:

| Resource | Path |
|----------|------|
| Transcript processor agent | `agents/transcript_processor.md` |
| Story analyst agent | `agents/story_analyst.md` |
| HTML editor builder agent | `agents/html_editor_builder.md` |
| Grader agent | `agents/grader.md` |
| Article style guide | `references/article_style_guide.md` |
| Eval schemas | `references/eval_schemas.md` |
| Transcript formatter | `scripts/format_transcript.py` |
| HTML editor generator | `scripts/generate_edit_review.js` |
| HTML editor template | `templates/edit_review.html` |
| Suggestion preloader | `scripts/preload_suggestions.py` |
| Transcript validator | `scripts/validate_transcript.py` |
| Edit proposal validator | `scripts/validate_edit_proposal.py` |
| HTML validator | `scripts/validate_html.py` |
| Score aggregator | `scripts/aggregate_scores.py` |
| Feedback history | `evals/feedback_history.json` |

---

## Notes & Edge Cases

- **Code-switching interviews** (English/Chinese mixed): Transcribe as-is, preserving both languages. Produce full bilingual deliverables for both shows regardless.
- **No guest name provided**: Ask before writing any content.
- **Long interviews (>90 min)**: Warn the user — processing will take longer.
- **Music / intro / outro**: Don't transcribe music. Mark as `[INTRO MUSIC]` / `[OUTRO MUSIC]` in transcript.
- **In-person track**: Use as a quality reference or blended ambient layer, not as the primary cut source (individual Zoom tracks are cleaner).
- **Multi-track alignment**: If timestamps between tracks are misaligned, use a shared audio event (e.g. a clap or clear start phrase) to sync them before cutting.
