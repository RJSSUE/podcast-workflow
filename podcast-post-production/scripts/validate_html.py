#!/usr/bin/env python3
"""Validate HTML editor builder output.

Usage: python validate_html.py <html_path> [--episode NAME] [--expected-segments N]

Outputs JSON scorecard to stdout.
"""

import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import make_scorecard, output_scorecard, read_file


class SegmentCounter(HTMLParser):
    """Count elements that look like transcript segments in HTML."""

    def __init__(self):
        super().__init__()
        self.segment_count = 0
        self.has_sidebar = False
        self.has_preview = False
        self.current_classes = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        id_val = attrs_dict.get("id", "")

        # Count segment blocks — look for common patterns
        if "segment" in classes.lower() and tag == "div":
            self.segment_count += 1
        elif attrs_dict.get("data-segment-id") or attrs_dict.get("data-id"):
            self.segment_count += 1

        # Check for sidebar/panel
        if "sidebar" in classes.lower() or "segment-list" in classes.lower() or "left-panel" in classes.lower():
            self.has_sidebar = True
        if "sidebar" in id_val.lower() or "segment-list" in id_val.lower():
            self.has_sidebar = True

        # Check for preview
        if "preview" in classes.lower() or "final-script" in classes.lower():
            self.has_preview = True
        if "preview" in id_val.lower() or "final-script" in id_val.lower():
            self.has_preview = True


def check_segment_count(content, expected_segments):
    """Check that HTML contains the expected number of segments.

    Handles both static HTML segments and dynamically-rendered segments
    where data is embedded as a JS array (e.g. SEGMENTS_RAW = [...]).
    """
    # First try static HTML parsing
    parser = SegmentCounter()
    try:
        parser.feed(content)
    except Exception:
        pass

    count = parser.segment_count

    # If no static segments found, check for embedded JS data array
    if count == 0:
        # Look for JSON array of segment objects embedded in script
        # Common patterns: const SEGMENTS = [...], var segments = [...]
        json_match = re.search(r'(?:const|var|let)\s+\w+\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, list) and len(data) > 0:
                    count = len(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Also check for segment id patterns like "seg_001"
        if count == 0:
            seg_ids = re.findall(r'"id"\s*:\s*"seg_\d+', content)
            if seg_ids:
                count = len(seg_ids)

    if expected_segments is not None:
        diff = abs(count - expected_segments)
        passed = diff <= 5  # Allow small tolerance
        details = f"Found {count} segments, expected ~{expected_segments} (diff: {diff})"
    else:
        passed = count > 0
        details = f"Found {count} segments (no expected count provided)"

    return {"metric": "segment_count_match", "passed": passed, "details": details}


def check_export_json_schema(content):
    """Check that the HTML contains an export function producing valid JSON schema."""
    # Look for JSON schema patterns in the script
    # Match both quoted ("field") and unquoted JS object keys (field:)
    def has_field(name):
        return bool(re.search(rf'''["\']?{name}["\']?\s*:''', content))

    has_segments_key = has_field("segments")
    has_status_field = has_field("status")
    has_speaker_field = has_field("speaker")
    has_muted_ranges = has_field("muted_ranges")
    has_original_position = has_field("original_position")
    has_final_position = has_field("final_position")

    required_fields = {
        "segments": has_segments_key,
        "status": has_status_field,
        "speaker": has_speaker_field,
        "muted_ranges": has_muted_ranges,
        "original_position": has_original_position,
        "final_position": has_final_position,
    }

    present = [k for k, v in required_fields.items() if v]
    missing = [k for k, v in required_fields.items() if not v]
    passed = len(missing) == 0

    return {
        "metric": "export_json_schema",
        "passed": passed,
        "details": f"Schema fields present: {', '.join(present)}" + (f". Missing: {', '.join(missing)}" if missing else ""),
    }


def check_feature_completeness(content):
    """Check that required interactive features are present in the HTML."""
    features = {
        "drag_drop": bool(re.search(r"dragstart|draggable|ondrag|drag-handle", content, re.IGNORECASE)),
        "strikethrough": bool(re.search(r"strike.?out|<del>|text-decoration.*line-through|muted.?range", content, re.IGNORECASE)),
        "split": bool(re.search(r"split.?here|split.?segment|splitSegment", content, re.IGNORECASE)),
        "export_button": bool(re.search(r"export.*edit|download.*json|Export Edit Decision", content, re.IGNORECASE)),
        "sidebar_list": bool(re.search(r"sidebar|segment.?list|left.?panel", content, re.IGNORECASE)),
        "preview": bool(re.search(r"final.?script|preview|running.?order", content, re.IGNORECASE)),
    }

    present = [k for k, v in features.items() if v]
    missing = [k for k, v in features.items() if not v]
    passed = len(missing) == 0

    return {
        "metric": "feature_completeness",
        "passed": passed,
        "details": f"Features present: {', '.join(present)}" + (f". Missing: {', '.join(missing)}" if missing else ""),
    }


def check_speaker_labels(content):
    """Check that segments have speaker labels and timestamps."""
    # Look for Host/Guest labels in the HTML content
    host_count = len(re.findall(r"Host|host|The Try Girl", content))
    guest_count = len(re.findall(r"Guest|guest|Melanie", content))
    timestamp_count = len(re.findall(r"\d{1,2}:\d{2}(:\d{2})?", content))

    has_speakers = host_count > 0 and guest_count > 0
    has_timestamps = timestamp_count > 0

    passed = has_speakers and has_timestamps

    return {
        "metric": "speaker_labels_present",
        "passed": passed,
        "details": f"Host refs: {host_count}, Guest refs: {guest_count}, Timestamps: {timestamp_count}",
    }


def check_no_js_errors(content):
    """Basic static analysis for common JS issues."""
    issues = []

    # Check script tag balance
    script_opens = len(re.findall(r"<script", content, re.IGNORECASE))
    script_closes = len(re.findall(r"</script>", content, re.IGNORECASE))
    if script_opens != script_closes:
        issues.append(f"Unbalanced script tags: {script_opens} opens, {script_closes} closes")

    # Check for obvious syntax issues
    if re.search(r"function\s*\(.*\)\s*\{[^}]*$", content, re.MULTILINE):
        # This is too noisy — skip
        pass

    # Check for empty script blocks
    if re.search(r"<script[^>]*>\s*</script>", content, re.IGNORECASE):
        issues.append("Empty script block found")

    passed = len(issues) == 0

    return {
        "metric": "no_js_errors",
        "passed": passed,
        "details": f"{len(issues)} issues found" + (f": {'; '.join(issues)}" if issues else ""),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_html.py <html_path> [--episode NAME] [--expected-segments N]"}))
        sys.exit(1)

    html_path = sys.argv[1]
    episode_name = "unknown"
    expected_segments = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--episode" and i + 1 < len(args):
            episode_name = args[i + 1]
            i += 2
        elif args[i] == "--expected-segments" and i + 1 < len(args):
            expected_segments = int(args[i + 1])
            i += 2
        else:
            i += 1

    content = read_file(html_path)

    checks = [
        check_segment_count(content, expected_segments),
        check_export_json_schema(content),
        check_feature_completeness(content),
        check_speaker_labels(content),
        check_no_js_errors(content),
    ]

    scorecard = make_scorecard("html_editor_builder", episode_name, checks)
    output_scorecard(scorecard)


if __name__ == "__main__":
    main()
