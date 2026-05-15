# HTML Editor Builder Agent

## Role
Create a fully functional, self-contained HTML file that serves as an interactive transcript editor for podcast post-production. The editor allows the user to review, reorder, cut, and fine-tune segments before audio compilation.

## Inputs
- Raw transcript files (`.txt`) — to be parsed into segments
- Recording setup notes (speaker names, timestamps)
- `feedback_history.json` recurring failures (if any)

## Outputs
- `./podcast_output/edit_review.html` — self-contained HTML editor (all CSS/JS inline, no external dependencies)

## Instructions

### 1. Parse transcripts into segments
Read the raw transcript files and break them into segments:
- Each segment = one speaker's continuous turn
- Assign speaker labels: Host (The Try Girl) / Guest ([Guest Name])
- When a raw block contains both speakers, split at the speaker change
- Each segment gets: `id`, `speaker`, `text`, `start_time`, `end_time`, `original_position`

### 2. Build the HTML editor

**Layout: Two panels**
- **Left panel (sidebar, ~250px):** Numbered segment list, scrollable. Each item: segment number, speaker badge (H=blue, G=green), first ~8 words. Click to scroll right panel. Cut segments shown muted/strikethrough.
- **Right panel:** Segment editor blocks + collapsible Final Script preview below.

**Segment-level editing:**
- Each segment is a draggable block (HTML5 drag-and-drop)
- Header: speaker label + timestamp
- Body: full segment text (contenteditable)
- "Cut" toggle (red button) — marks for full deletion (red tint, strikethrough in sidebar)
- Drag handle (grip dots) on left side
- If dragged to new position: amber highlight with "moved from #N" label

**Word/phrase-level editing:**
- User selects text within a segment → floating "Strike out" button appears
- Clicking wraps selection in `<del>` tag with strikethrough + pink background
- Clicking struck-out text removes the `<del>` tag (toggle)
- Stored as `muted_ranges` (character start/end positions) in the export

**Segment splitting:**
- When cursor is inside segment text: show floating "Split here" button
- Splits segment into two at cursor position
- Both inherit speaker label; timestamps split proportionally by character count
- Both independently editable and draggable

**Final Script preview (collapsible):**
- Shows only kept segments in current order
- Struck-out phrases shown inline with strikethrough
- Updates live as user drags/cuts/strikes (debounced 300ms)

**Export:**
- Fixed bottom-right "Export Edit Decision" button
- Downloads `edit_decision.json`

### 3. Export JSON schema

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

### 4. Styling
- Clean, modern, light background
- Host segments: left border `#3b82f6` (blue)
- Guest segments: left border `#10b981` (green)
- Cut segments: `#fef2f2` background, text strikethrough
- Moved segments: `#fffbeb` background (amber)
- Drag handle: `⠿` grip dots
- Optimize for desktop (1200px+)

### 5. Performance
- The interview may have 200+ segments — use efficient DOM operations
- Debounce Final Script preview updates (300ms)
- Embed transcript data directly as a JavaScript array in the HTML

### 6. Audio Preview

Allow the user to load the source audio file and hear the edited result live in the browser.

**UI:**
- Audio load bar (below toolbar): file input accepting `audio/*`, shows filename once loaded
- Transport controls (appear after load): Play/Pause toggle, Stop, clickable progress bar, elapsed/total time display
- Per-segment ▶ play button on each segment header — plays just that one segment
- Currently-playing segment gets a pulsing blue border + sidebar highlight with auto-scroll

**Playback logic:**
- Use a hidden `<audio>` element with File API blob URL (NOT Web Audio API — avoids decoding 1GB+ into memory)
- `getMutedTimeRanges(seg)` — converts character-based `muted_ranges` to proportional time ranges within the segment
- `buildSegSubQueue(seg, segIdx)` — splits a segment into playable sub-segments that skip muted time ranges
- `buildQueue()` — iterates kept segments in display order, calls `buildSegSubQueue` for each, flattens into one array of `{start, end, segIdx}`
- `playAll()` — builds queue, starts at index 0, seeks audio to first sub-segment start
- `timeupdate` handler — when `currentTime >= sub-segment.end`, advance to next queue item (seek + play). Works identically for both single and full playback modes.
- `playSingle(segIdx)` — builds sub-queue for just that segment (respecting muted ranges), plays through its sub-segments
- `seekProgress(e)` — click on progress bar to jump to a position within the edited timeline
- Queue rebuilds on every cut/reorder/undo/strikethrough so preview always reflects current state

**Segment splitting:**
- When splitting a segment, proportionally divide timestamps: `splitTime = start + (charPos / textLength) * (end - start)`
- First half: `(start_time, splitTime)`, second half: `(splitTime, end_time)`
- Use `fmtTimeHMS(seconds)` to convert back to `HH:MM:SS` format

**CSS:**
- `.segment.playing` — pulsing box-shadow animation
- `.sidebar-item.playing` — blue highlight
- `.audio-bar` — light blue background strip
- `.seg-play-btn` — small play icon, hover turns blue

## Quality Criteria
1. **Segment count match** — HTML segment count matches the number of speaker turns in the transcript
2. **Export JSON schema valid** — exported JSON matches the edit_decision.json schema exactly
3. **Feature completeness** — all required interactions present: drag-drop, strikethrough, split, export, sidebar, preview
4. **Speaker labels present** — every segment has speaker label and timestamp
5. **No JS errors** — file loads without console errors in a modern browser

## Rebuilding from Corrected Edit Decisions

When the user provides a corrected `edit_decision.json` with clean text, rebuild the HTML editor from it rather than the raw ASR transcript:

1. **Extract segments** from each edit_decision entry: `host_question.edited` → Host segment, `guest_answer.edited` → Guest segment
2. **Preserve metadata**: `act`, `source` (zoom/in-person), `is_key_moment`, `status` (keep/cut/move)
3. **Show act headers** as visual section dividers in both the sidebar and editor
4. **Mark key moments** with a badge/star in the sidebar and a gold border in the editor
5. **Show source labels** (zoom/in-person) on each segment
6. The corrected segments ARE the data — embed them as the JS data array, not the raw transcript

### 7. Preloading Edit Suggestions

When an `edit_proposal.md` exists alongside the transcript, preload its recommended cuts into the editor as **AI suggestions** that are pre-applied but revertable.

**How it works:**
1. Parse `### CUT N: <label> (start – end)` entries from the proposal, extracting cut number, label, timestamp range, and rationale
2. Map each cut to segments by timestamp overlap (segment overlaps with cut range → mark as suggested cut)
3. Set `status: 'cut'`, `suggested: true`, and `suggestion_info: {cut_num, label, rationale}` on matched segments

**Suggestion UI elements:**
- **Banner** (top of editor): Shows count of active suggestions, "Accept All" / "Revert All" / "Show Rationales" buttons
- **Per-segment tag**: Amber `✨ CUT N — AI Suggested` badge in segment header
- **Per-segment actions**: "↩ Revert" (restores to keep) and "✓ Confirm" (accepts, removes suggestion marker) buttons
- **Rationale tooltip**: Collapsible rationale text below each suggested-cut segment
- **Sidebar**: Suggested segments get amber left border + `.suggested` class

**CSS classes:**
- `.segment.suggested-cut` — amber background `#fefce8`, amber left border, 0.7 opacity, strikethrough text
- `.suggestion-tag` — amber badge with uppercase text
- `.suggestion-rationale` — light yellow info box below segment body
- `.suggestion-banner` — amber strip at top of editor
- `.sidebar-item.suggested` — amber left border

**JS functions:**
- `revertSuggestion(idx)` — restores segment to `keep`, clears `suggested` flag
- `acceptSuggestion(idx)` — keeps as `cut`, clears `suggested` flag (becomes a confirmed cut)
- `revertAllSuggestions()` / `acceptAllSuggestions()` — batch operations
- `toggleSuggestionDetails()` — shows/hides rationale text on all suggested segments
- `updateSuggestionBanner()` — updates count, hides banner when no suggestions remain
- Called from `renderAll()` to stay in sync

**Export behavior:**
- Accepted suggestions export as normal `status: 'cut'` segments
- Reverted suggestions export as `status: 'keep'` segments
- The `suggested` and `suggestion_info` fields are NOT included in the export JSON (they're editor-only state)

**Implementation:** Use `preload_suggestions.py` in the podcast_output directory — it parses both files and injects the suggestion data + UI into the HTML. Can be run as a post-processing step after building the base editor.

## Known Pitfalls

- **Python f-strings vs JavaScript**: Never use Python f-strings for HTML/JS templates containing curly braces. Use `json.dumps()` for data embedding + plain string concatenation for the template.
- **innerHTML security hook**: The security hook flags innerHTML usage. Document that data is local-only and all text is escaped via `escHtml()` / DOM `textContent`. Keep the security comment in the script.
- **Large segment counts**: With 400+ segments, use efficient DOM construction (createElement, not string concatenation). Debounce preview updates.
- **Split must update timestamps**: When splitting a segment, both halves must get proportionally divided timestamps — NOT the parent's full range. Use `splitTime = start + (charPos / textLen) * duration`.
- **Audio preview must respect muted_ranges**: Struck-out text = muted audio. Convert character-based muted_ranges to proportional time ranges, then build sub-segments that skip muted windows during playback. Both `playSingle()` and `buildQueue()` must use `buildSegSubQueue()`.
- **Need `fmtTimeHMS()`**: Include a helper that formats seconds back to `HH:MM:SS` (for split timestamps). `fmtTime()` only does `M:SS`.
- **Suggestion preload must not pollute export**: The `suggested` and `suggestion_info` fields are editor-only state. The `exportJSON()` function must strip them — only `status`, `muted_ranges`, and standard fields go into the export.
- **Suggestion revert must call renderAll()**: After reverting a suggestion, the sidebar, segments, stats, and banner all need to update. Always end suggestion operations with `renderAll(); updateSuggestionBanner();`.
- **DOM ordering in renderSegments**: When using `header.insertBefore(sugTag, actions)` for suggestion UI, `actions` must already be a child of `header`. Always call `header.appendChild(handle/speaker/time/sid/actions)` BEFORE the `if (seg.suggested)` block that uses `insertBefore`. Reversing this order causes a NotFoundError that silently kills the forEach loop after the first suggested segment.
- **str.replace() without count=1**: Python's `str.replace()` replaces ALL occurrences by default. When patching HTML/JS, always pass `count=1` (or use `re.sub` with `count=1`) to avoid duplicating injected blocks — duplicate suggestion UI blocks cause cascading DOM errors.
- **Idempotent function replacement**: When using marker-based whole-function replacement, `strip_markers` removes the entire function (not just the additions). On re-runs, the function won't exist to find. The script must handle both cases: (1) original function present → replace it, (2) function already stripped → insert before the next known anchor (e.g., `function renderAll()`).
- **renderAll patch must use regex**: The `renderAll()` function body may have trailing whitespace that varies between the original HTML and post-injection state. Use `re.sub()` with a flexible whitespace pattern instead of literal `str.replace()` to inject `updateSuggestionBanner()` into `renderAll()`.
