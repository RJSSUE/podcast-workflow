---
name: podcast-editor
description: >
  Build an interactive HTML transcript editor for podcast post-production review. Use when the user wants a drag-and-drop editor for reviewing and reordering transcript segments — "build the editor", "create the HTML editor", "make the edit review page". Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Editor

Creates a self-contained, interactive HTML transcript editor for reviewing, reordering, and fine-tuning podcast segments before audio compilation.

**Input:** Raw transcript (`.txt` with timestamps), formatted transcript, or `edit_decision.json` + audio file info
**Output:** `podcast_output/edit_review.html` (exports `edit_decision.json` via browser)

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

### Get episode metadata (if not already known)
- **Guest name**
- **Audio file names and which speaker/session each covers**

---

## Processing

### 0. Format raw transcript (if starting from raw timestamp+text file)

Most episodes start with a raw transcript in alternating `MM:SS\ntext` format (no speaker labels). Use the formatting script:

1. **Read the transcript** and create episode-specific diarization patterns (guest-specific terms, host question patterns) in a JSON file. See `~/.claude/skills/podcast-shared/agents/html_editor_builder.md` for the pattern format.

2. **Run the formatter:**
```bash
python ~/.claude/skills/podcast-shared/scripts/format_transcript.py \
  <raw_transcript.txt> \
  --guest "<GUEST_NAME>" \
  --patterns podcast_output/diarization_patterns.json \
  --output podcast_output/formatted_transcript.txt \
  --segments-json podcast_output/segments.json \
  --language zh|en
```

3. **Wrap for injection:** The injection script expects `{segments: [...]}` format:
```bash
python3 -c "
import json
with open('podcast_output/segments.json') as f: segs = json.load(f)
with open('podcast_output/edit_decision.json', 'w') as f: json.dump({'segments': segs}, f, ensure_ascii=False)
"
```

Speaker diarization is ~80% accurate via text patterns. The editor's speaker toggle button (↹) handles corrections.

### 1. Generate HTML

Use the template-based injection script to produce the editor:

```bash
node ~/.claude/skills/podcast-shared/scripts/generate_edit_review.js \
  --edit-decision podcast_output/edit_decision.json \
  --guest "<GUEST_NAME>" \
  --host "Host" \
  --audio "<AUDIO_FILE_PATH>" \
  --output podcast_output/edit_review.html \
  --title "Podcast Edit Review"
```

For additional options and formats, read `~/.claude/skills/podcast-shared/agents/html_editor_builder.md`.

### 2. AI suggestion preloading (optional)

If `edit_proposal.md` exists, add `--proposal podcast_output/edit_proposal.md` to the command above. This pre-applies AI-recommended cuts as revertable suggestions with rationale tooltips.

### 3. Rebuilding from corrected edit decisions

When the user provides a corrected `edit_decision.json`, use `--edit-decision` instead of `--transcript`:

```bash
node ~/.claude/skills/podcast-shared/scripts/generate_edit_review.js \
  --edit-decision podcast_output/edit_decision.json \
  --guest "<GUEST_NAME>" \
  --output podcast_output/edit_review.html
```

---

## Delivery

Present the HTML and tell the user:

> "Open this file in your browser. The editor includes:
> - **Drag-and-drop** to reorder segments
> - **Strike out** words/phrases by selecting text
> - **Split** segments at cursor position
> - **Cut** entire segments with the red button
> - **Multi-select** with Shift+click or Ctrl+click for batch operations
> - **Undo/Redo** with Ctrl+Z / Ctrl+Shift+Z
> - **Filter** by speaker or status using the top bar
> - **Auto-save** — your edits persist across browser refreshes
> - **Audio preview** — load your audio file to hear segments
>
> When you're happy with the Final Script preview, click **Export Edit Decision** and send me the `edit_decision.json`."

---

## Validation

After processing, validate the output:

```bash
python ~/.claude/skills/podcast-shared/scripts/validate_html.py \
  ./podcast_output/edit_review.html \
  --episode "<GUEST_NAME>" \
  --expected-segments <N>
```

Save the scorecard to `podcast_output/evals/scorecard_html.json`.
