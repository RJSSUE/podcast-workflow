#!/usr/bin/env python3
"""
Preload edit suggestions from edit_proposal.md into edit_review.html.

Uses a complete function replacement strategy instead of fragile inline patching.
The entire renderSegments function is replaced with a version that includes
suggestion UI code, wrapped in markers for idempotent cleanup.
"""

import json
import re
import sys
from pathlib import Path


def parse_time(ts: str) -> float:
    parts = [float(p) for p in ts.strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def parse_cuts_from_proposal(proposal_path: str) -> list[dict]:
    with open(proposal_path, "r") as f:
        text = f.read()
    cuts = []
    pattern = r"###\s+CUT\s+(\d+):\s+(.+?)\s*\((\d[\d:]+)\s*[–\-]\s*(\d[\d:]+)\)"
    for m in re.finditer(pattern, text):
        after = text[m.end():]
        rat_match = re.search(r"\*\*Rationale:\*\*\s*(.+?)(?=\n\*\*Saves:)", after, re.DOTALL)
        cuts.append({
            "cut_num": int(m.group(1)),
            "label": m.group(2).strip(),
            "start": parse_time(m.group(3)),
            "end": parse_time(m.group(4)),
            "rationale": rat_match.group(1).strip() if rat_match else "",
        })
    return cuts


def map_cuts_to_segments(cuts, segments):
    result = {}
    for i, seg in enumerate(segments):
        seg_start = parse_time(seg["start_time"])
        seg_end = parse_time(seg["end_time"])
        for cut in cuts:
            if max(seg_start, cut["start"]) < min(seg_end, cut["end"]):
                result[i] = {
                    "cut_num": cut["cut_num"],
                    "label": cut["label"],
                    "rationale": cut["rationale"],
                }
                break
    return result


# ── Markers ────────────────────────────────────────────────────────────────
MS = "<!-- __SUGGEST_"
ME = " -->"
M = lambda name: (f"{MS}{name}_START__{ME}", f"{MS}{name}_END__{ME}")
M_CSS = M("CSS")
M_BANNER = M("BANNER")
# JS markers use // comments
MJS = lambda name: (f"// __SUGGEST_{name}_START__", f"// __SUGGEST_{name}_END__")
M_JS = MJS("JS")
M_RENDER = MJS("RENDER")  # wraps entire renderSegments replacement

ALL_MARKERS = [M_CSS, M_BANNER, M_JS, M_RENDER]


def strip_markers(html: str) -> str:
    """Remove all marked injection blocks."""
    for start_m, end_m in ALL_MARKERS:
        pat = re.escape(start_m) + r".*?" + re.escape(end_m)
        html = re.sub(pat, "", html, flags=re.DOTALL)

    # Remove legacy unmarked blocks from earlier versions
    html = re.sub(
        r"\n*// ── Suggestion Management ─+\nvar showRationales.*?"
        r"(?=\n// ── |\n</script>)",
        "", html, flags=re.DOTALL,
    )
    html = re.sub(r"<div class=\"suggestion-banner\"[^>]*>.*?</div>", "", html, flags=re.DOTALL)
    html = re.sub(r"\n\s*// Suggestion UI\n\s*if \(seg\.suggested\).*?\}\n", "\n", html, flags=re.DOTALL)
    html = re.sub(r"\n\s*// Suggestion rationale\n\s*if \(seg\.suggested.*?\}\n", "\n", html, flags=re.DOTALL)

    # Revert sidebar if patched without markers
    html = html.replace(
        "') + (seg.suggested ? ' suggested' : '');",
        "');",
    )
    # Revert renderAll if patched (with or without markers)
    html = html.replace("    updateSuggestionBanner();\n", "")

    # Fix any collapsed lines from prior stripping
    html = re.sub(r"(div\.appendChild\(body\));(container\.appendChild)", r"\1;\n\n        \2", html)

    # Clean up excessive blank lines
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


# ── The complete renderSegments function with suggestion UI built in ───────
RENDER_SEGMENTS_FN = """{M_RENDER_START}
function renderSegments() {{
    var container = document.getElementById('segmentsContainer');
    while (container.firstChild) container.removeChild(container.firstChild);
    segments.forEach(function(seg, idx) {{
        var isCut = seg.status === 'cut';
        var isMoved = seg.original_position !== (idx + 1);
        var cls = 'segment ' + seg.speaker.toLowerCase();
        if (isCut) cls += ' cut';
        if (isMoved && !isCut) cls += ' moved';

        var div = document.createElement('div');
        div.className = cls;
        div.id = 'seg-' + idx;
        div.draggable = true;
        div.setAttribute('data-idx', idx);
        div.addEventListener('dragstart', onDragStart);
        div.addEventListener('dragover', onDragOver);
        div.addEventListener('dragleave', onDragLeave);
        div.addEventListener('drop', onDrop);
        div.addEventListener('dragend', onDragEnd);

        // Header
        var header = document.createElement('div');
        header.className = 'seg-header';
        var handle = document.createElement('span');
        handle.className = 'drag-handle';
        handle.textContent = '\\u2807';
        var speaker = document.createElement('span');
        speaker.className = 'seg-speaker ' + seg.speaker.toLowerCase();
        speaker.textContent = seg.speaker === 'Host' ? 'Host (The Try Girl)' : 'Guest (Peter Lee)';
        var time = document.createElement('span');
        time.className = 'seg-time';
        time.textContent = seg.start_time + ' \\u2013 ' + seg.end_time;
        var sid = document.createElement('span');
        sid.className = 'seg-id';
        sid.textContent = seg.id;
        var actions = document.createElement('div');
        actions.className = 'seg-actions';

        var spkBtn = document.createElement('button');
        spkBtn.className = 'btn btn-secondary btn-sm';
        spkBtn.textContent = '\\u21C4 Speaker';
        (function(i){{ spkBtn.onclick = function(){{ toggleSpeaker(i); }}; }})(idx);

        var cutBtn = document.createElement('button');
        cutBtn.className = 'btn btn-sm ' + (isCut ? 'btn-danger active' : 'btn-danger');
        cutBtn.textContent = isCut ? '\\u2713 Cut' : '\\u2702 Cut';
        (function(i){{ cutBtn.onclick = function(){{ toggleCut(i); }}; }})(idx);

        var playBtn = document.createElement('button');
        playBtn.className = 'seg-play-btn';
        playBtn.textContent = '\\u25B6';
        playBtn.title = 'Preview this segment';
        (function(i){{ playBtn.onclick = function(e){{ e.stopPropagation(); playSingle(i); }}; }})(idx);

        actions.appendChild(playBtn);
        actions.appendChild(spkBtn);
        actions.appendChild(cutBtn);

        header.appendChild(handle);
        header.appendChild(speaker);
        header.appendChild(time);
        header.appendChild(sid);
        header.appendChild(actions);

        // Suggestion UI — revert/confirm buttons for AI-suggested cuts
        if (seg.suggested) {{
            div.classList.add('suggested-cut');
            var sugTag = document.createElement('span');
            sugTag.className = 'suggestion-tag';
            sugTag.textContent = '\\u2728 CUT ' + (seg.suggestion_info ? seg.suggestion_info.cut_num : '?') + ' \\u2014 AI Suggested';
            header.insertBefore(sugTag, actions);

            var revertBtn = document.createElement('button');
            revertBtn.className = 'btn btn-secondary btn-sm';
            revertBtn.textContent = '\\u21A9 Revert';
            revertBtn.title = 'Revert this AI suggestion (keep segment)';
            (function(i){{ revertBtn.onclick = function(e){{ e.stopPropagation(); revertSuggestion(i); }}; }})(idx);
            actions.appendChild(revertBtn);

            var acceptBtn = document.createElement('button');
            acceptBtn.className = 'btn btn-primary btn-sm';
            acceptBtn.textContent = '\\u2713 Confirm';
            acceptBtn.title = 'Accept this cut (remove suggestion marker)';
            (function(i){{ acceptBtn.onclick = function(e){{ e.stopPropagation(); acceptSuggestion(i); }}; }})(idx);
            actions.appendChild(acceptBtn);
        }}

        // Body
        var body = document.createElement('div');
        body.className = 'seg-body';
        var textDiv = document.createElement('div');
        textDiv.className = 'seg-text';
        textDiv.contentEditable = isCut ? 'false' : 'true';
        textDiv.setAttribute('data-idx', idx);

        var rawText = seg.edited_text || seg.text;
        var muted = seg.muted_ranges || [];
        if (muted.length > 0) {{
            muted.sort(function(a,b){{ return a.start - b.start; }});
            var lastEnd = 0;
            muted.forEach(function(r) {{
                if (r.start > lastEnd) {{
                    textDiv.appendChild(document.createTextNode(rawText.substring(lastEnd, r.start)));
                }}
                var struck = document.createElement('span');
                struck.className = 'struck';
                struck.textContent = rawText.substring(r.start, r.end);
                textDiv.appendChild(struck);
                lastEnd = r.end;
            }});
            if (lastEnd < rawText.length) {{
                textDiv.appendChild(document.createTextNode(rawText.substring(lastEnd)));
            }}
        }} else {{
            textDiv.textContent = rawText;
        }}

        (function(i, s){{
            textDiv.addEventListener('input', function() {{
                s.edited_text = this.textContent;
                schedulePreview();
                renderSidebar();
            }});
        }})(idx, seg);
        textDiv.addEventListener('mouseup', onTextSelect);

        body.appendChild(textDiv);
        div.appendChild(header);
        div.appendChild(body);

        // Suggestion rationale tooltip
        if (seg.suggested && seg.suggestion_info && seg.suggestion_info.rationale) {{
            var ratDiv = document.createElement('div');
            ratDiv.className = 'suggestion-rationale';
            ratDiv.textContent = '\\uD83D\\uDCA1 ' + seg.suggestion_info.label + ': ' + seg.suggestion_info.rationale;
            if (!showRationales) ratDiv.style.display = 'none';
            div.appendChild(ratDiv);
        }}

        container.appendChild(div);
    }});
}}
{M_RENDER_END}"""


def inject_suggestions(html_path: str, proposal_path: str, output_path: str):
    cuts = parse_cuts_from_proposal(proposal_path)
    print(f"Parsed {len(cuts)} cuts from proposal")

    with open(html_path, "r") as f:
        html = f.read()

    # ── 1. Strip all previous injections ───────────────────────────────
    html = strip_markers(html)

    # ── 2. Clean and update INITIAL_DATA ───────────────────────────────
    match = re.search(r"var INITIAL_DATA = (\[.*?\]);\s*\n", html, re.DOTALL)
    if not match:
        print("ERROR: INITIAL_DATA not found"); sys.exit(1)

    segments = json.loads(match.group(1))
    print(f"Found {len(segments)} segments")

    for seg in segments:
        seg.pop("suggested", None)
        seg.pop("suggestion_info", None)
        seg["status"] = "keep"

    suggestions = map_cuts_to_segments(cuts, segments)
    print(f"Mapped {len(suggestions)} segments to cuts")

    for idx, info in suggestions.items():
        segments[idx]["status"] = "cut"
        segments[idx]["suggested"] = True
        segments[idx]["suggestion_info"] = {
            "cut_num": info["cut_num"],
            "label": info["label"],
            "rationale": info["rationale"],
        }

    new_json = json.dumps(segments, ensure_ascii=False)
    html = html[:match.start(1)] + new_json + html[match.end(1):]

    # ── 3. Inject CSS ──────────────────────────────────────────────────
    css = f"""
{M_CSS[0]}
.segment.suggested-cut {{ background: #fefce8; border-left-color: #f59e0b !important; opacity: 0.7; }}
.segment.suggested-cut .seg-text {{ text-decoration: line-through; color: #a1a1aa; }}
.suggestion-tag {{ display: inline-flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 700; color: #d97706; background: #fef3c7; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }}
.suggestion-rationale {{ font-size: 11px; color: #92400e; background: #fef9c3; padding: 6px 10px; border-radius: 4px; margin: 4px 14px 8px; line-height: 1.5; }}
.suggestion-banner {{ display: flex; align-items: center; gap: 12px; padding: 10px 24px; background: #fefce8; border-bottom: 1px solid #fde68a; font-size: 13px; color: #92400e; flex-wrap: wrap; }}
.suggestion-banner strong {{ color: #78350f; }}
.suggestion-banner .btn {{ font-size: 12px; padding: 4px 12px; }}
.sidebar-item.suggested {{ background: #fefce8; border-left: 3px solid #f59e0b; }}
{M_CSS[1]}
"""
    html = html.replace("</style>", css + "</style>")

    # ── 4. Inject banner ───────────────────────────────────────────────
    banner = f"""
{M_BANNER[0]}
  <div class="suggestion-banner" id="suggestionBanner">
    <span>&#x26A1;</span>
    <span><strong id="suggestionCount">0</strong> AI-suggested cuts preloaded from edit proposal (~23 min savings)</span>
    <button class="btn btn-secondary btn-sm" onclick="acceptAllSuggestions()">Accept All</button>
    <button class="btn btn-secondary btn-sm" onclick="revertAllSuggestions()">Revert All</button>
    <button class="btn btn-secondary btn-sm" id="btnToggleRationale" onclick="toggleSuggestionDetails()">Show Rationales</button>
  </div>
{M_BANNER[1]}
"""
    anchor = '<audio id="audioEl" preload="auto" style="display:none;"></audio>'
    html = html.replace(anchor, anchor + banner)

    # ── 5. Inject JS functions ─────────────────────────────────────────
    js_fns = f"""
{M_JS[0]}
var showRationales = false;

function updateSuggestionBanner() {{
    var count = 0;
    segments.forEach(function(seg) {{
        if (seg.suggested && seg.status === 'cut') count++;
    }});
    var el = document.getElementById('suggestionCount');
    if (el) el.textContent = count;
    var banner = document.getElementById('suggestionBanner');
    if (banner) {{
        var anyLeft = segments.some(function(s) {{ return s.suggested; }});
        banner.style.display = anyLeft ? 'flex' : 'none';
    }}
}}

function revertSuggestion(idx) {{
    saveUndo();
    segments[idx].status = 'keep';
    segments[idx].suggested = false;
    delete segments[idx].suggestion_info;
    renderAll();
}}

function acceptSuggestion(idx) {{
    saveUndo();
    segments[idx].suggested = false;
    delete segments[idx].suggestion_info;
    renderAll();
}}

function revertAllSuggestions() {{
    saveUndo();
    segments.forEach(function(seg) {{
        if (seg.suggested && seg.status === 'cut') {{
            seg.status = 'keep';
            seg.suggested = false;
            delete seg.suggestion_info;
        }}
    }});
    renderAll();
}}

function acceptAllSuggestions() {{
    saveUndo();
    segments.forEach(function(seg) {{
        if (seg.suggested) {{
            seg.suggested = false;
            delete seg.suggestion_info;
        }}
    }});
    renderAll();
}}

function toggleSuggestionDetails() {{
    showRationales = !showRationales;
    document.getElementById('btnToggleRationale').textContent = showRationales ? 'Hide Rationales' : 'Show Rationales';
    renderAll();
}}
{M_JS[1]}

"""
    html = html.replace("// ── Init ", js_fns + "// ── Init ")

    # ── 6. Replace entire renderSegments function ──────────────────────
    # After strip_markers, the old renderSegments may be gone (markers removed it).
    # Handle both cases: original present, or already stripped.
    fn_start = html.find("function renderSegments()")
    fn_end_marker = "\nfunction renderAll()"

    new_fn = RENDER_SEGMENTS_FN.format(
        M_RENDER_START=M_RENDER[0],
        M_RENDER_END=M_RENDER[1],
    )

    if fn_start != -1:
        # Original or previous injection still present — replace it
        fn_end = html.find(fn_end_marker, fn_start)
        if fn_end == -1:
            print("ERROR: Could not find renderAll boundary"); sys.exit(1)
        html = html[:fn_start] + new_fn + "\n" + html[fn_end:]
    else:
        # strip_markers already removed it — insert before renderAll
        ra_pos = html.find("function renderAll()")
        if ra_pos == -1:
            print("ERROR: Could not find renderAll()"); sys.exit(1)
        html = html[:ra_pos] + new_fn + "\n\n" + html[ra_pos:]

    # ── 7. Patch renderAll ─────────────────────────────────────────────
    # Match renderAll body flexibly (trailing whitespace varies)
    html = re.sub(
        r"(function renderAll\(\) \{[^}]*schedulePreview\(\);)\s*\n\}",
        r"\1\n    updateSuggestionBanner();\n}",
        html,
        count=1,
    )

    # ── 8. Patch sidebar ───────────────────────────────────────────────
    html = html.replace(
        "item.className = 'sidebar-item' + (seg.status === 'cut' ? ' cut' : '');",
        "item.className = 'sidebar-item' + (seg.status === 'cut' ? ' cut' : '') + (seg.suggested ? ' suggested' : '');",
        1,
    )

    # ── 9. Write ───────────────────────────────────────────────────────
    with open(output_path, "w") as f:
        f.write(html)

    print(f"\nDone: {output_path}")
    print(f"  {len(suggestions)} segments marked as suggested cuts")
    for cut in cuts:
        matched = [i for i, info in suggestions.items() if info["cut_num"] == cut["cut_num"]]
        print(f"  CUT {cut['cut_num']:2d} ({cut['label'][:40]:40s}): {len(matched)} segs")


if __name__ == "__main__":
    base = Path(__file__).parent
    inject_suggestions(
        str(base / "edit_review.html"),
        str(base / "edit_proposal.md"),
        str(base / "edit_review.html"),
    )
