# HTML Editor Builder Agent

## Role
Generate an interactive transcript editor HTML file for podcast post-production using the pre-built template and data injection script.

## Inputs
- Raw transcript files (`.txt`) or corrected `edit_decision.json`
- Recording setup notes (speaker names, timestamps)
- `feedback_history.json` recurring failures (if any)
- Optional: `edit_proposal.md` for AI suggestion preloading

## Outputs
- `./podcast_output/edit_review.html` — self-contained HTML editor (all CSS/JS inline, no external dependencies)

## Instructions

### 1. Prepare segment data

Identify the data source and format it:

**A. Raw timestamp+text transcript** (most common for new episodes):
The raw format has alternating timestamp and text lines (no speaker labels). Use the formatting script with episode-specific diarization patterns:

```bash
python ~/.claude/skills/podcast-shared/scripts/format_transcript.py \
  <raw_transcript.txt> \
  --guest "<GUEST_NAME>" \
  --host "Host" \
  --patterns <patterns.json> \
  --output podcast_output/formatted_transcript.txt \
  --segments-json podcast_output/segments.json \
  --language zh|en
```

Then wrap for the injection script:
```python
import json
with open('podcast_output/segments.json') as f:
    segs = json.load(f)
with open('podcast_output/edit_decision.json', 'w') as f:
    json.dump({'segments': segs}, f, ensure_ascii=False)
```

**Creating diarization patterns:** Read the transcript, identify guest-specific terms (name, career, unique experiences) and host-specific terms (show intro, question phrases, personal references). Write a JSON file:
```json
{
  "guest_patterns": ["regex1", ...],
  "host_patterns": ["regex1", ...],
  "guest_strong": ["high-confidence regex (worth +5 score)", ...],
  "host_strong": ["high-confidence regex (worth +5 score)", ...]
}
```
The script scores each segment against both pattern lists, with question-mark and narrative-length bonuses, and alternation as tiebreaker. Expect ~80% accuracy; the editor's speaker toggle button handles corrections.

**B. Already-formatted transcript** (`.txt` with `Speaker: text` lines):
Pass directly to the injection script via `--transcript`.

**C. Corrected edit_decision.json**:
Use `--edit-decision` flag — the corrected segments ARE the data.

### 2. Run the injection script

```bash
node ~/.claude/skills/podcast-shared/scripts/generate_edit_review.js \
  --transcript podcast_output/formatted_transcript.txt \
  --guest "<GUEST_NAME>" \
  --host "Host" \
  --audio "<AUDIO_FILE_PATH>" \
  --output podcast_output/edit_review.html \
  --title "Podcast Edit Review"
```

**For corrected edit decisions:**
```bash
node ~/.claude/skills/podcast-shared/scripts/generate_edit_review.js \
  --edit-decision podcast_output/edit_decision.json \
  --guest "<GUEST_NAME>" \
  --output podcast_output/edit_review.html
```

**With AI suggestion preloading:**
Add `--proposal podcast_output/edit_proposal.md` to either command above. The script parses `### CUT N:` headers from the proposal, maps them to segments by timestamp overlap, and pre-applies them as revertable cuts.

### 3. Validate output

```bash
python ~/.claude/skills/podcast-shared/scripts/validate_html.py \
  podcast_output/edit_review.html \
  --episode "<GUEST_NAME>" \
  --expected-segments <N>
```

All checks should pass. Save scorecard to `podcast_output/evals/scorecard_html.json`.

## What the template provides

The HTML template at `~/.claude/skills/podcast-shared/templates/edit_review.html` includes all of these features built-in — no manual HTML generation needed:

- **Two-panel layout**: Sidebar (250px, segment list) + main editor
- **Drag-and-drop** segment reordering (HTML5 DnD)
- **Segment editing**: Cut toggle, speaker toggle, contenteditable text
- **Word/phrase strikethrough**: Select text -> floating "Strike out" button, stored as `muted_ranges`
- **Segment splitting**: Cursor-based split with proportional timestamp division
- **Audio preview**: File API blob URL, per-segment play, transport controls
- **Auto-save**: localStorage with 500ms debounce, 30-day auto-purge, restore on load
- **Undo/Redo**: Full state snapshot stack (max 50), Ctrl+Z / Ctrl+Shift+Z
- **Stats dashboard**: Segment counts, duration totals, live-updating
- **Filter bar**: By status (All/Kept/Cut), by speaker, text search
- **Multi-selection**: Shift+click range, Ctrl/Cmd+click toggle, batch cut/keep
- **Keyboard shortcuts**: Ctrl+Z, Ctrl+Shift+Z, Delete, Space, Escape
- **AI suggestion UI**: Banner, per-segment revert/confirm, rationale tooltips
- **Final Script preview**: Collapsible, live-updating, debounced 300ms
- **Export**: Downloads `edit_decision.json` with full schema

## Export JSON schema

The exported `edit_decision.json` matches this schema:

```json
{
  "segments": [
    {
      "id": "seg_001",
      "speaker": "Host",
      "original_text": "...",
      "edited_text": "...",
      "status": "keep|cut",
      "original_position": 1,
      "final_position": 3,
      "start_time": "00:00:00",
      "end_time": "00:00:45",
      "muted_ranges": [
        { "start": 12, "end": 27, "text": "you know like" }
      ]
    }
  ]
}
```

## Known Pitfalls

- **Data parsing edge cases**: When parsing transcripts, speaker detection uses the first colon position. Lines with colons in dialogue (e.g., "Time: 3pm") may be misparsed if the colon appears early. The injection script handles this with a length/space heuristic.
- **Suggestion timestamp overlap**: AI suggestion mapping uses `max(segStart, cutStart) < min(segEnd, cutEnd)` for overlap detection. Segments that barely touch a cut boundary may or may not match — this is by design (inclusive overlap).
- **Large segment counts**: The template handles 400+ segments efficiently using `createElement` (not string concatenation) and debounced preview updates.
- **Auto-save key collisions**: Auto-save keys use `podcast_editor_${pageTitle}`. Different episodes with the same title would collide — use unique titles per episode.
