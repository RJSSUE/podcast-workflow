#!/usr/bin/env python3
"""Validate transcript processor output.

Usage: python validate_transcript.py <transcript_path> [source_path1 source_path2 ...] [--episode NAME]

Outputs JSON scorecard to stdout.
"""

import json
import os
import re
import sys

# Add parent directory so we can import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import make_scorecard, output_scorecard, parse_timestamp, read_file


def check_format_compliance(lines):
    """Check that speaker turns match the expected format."""
    # Pattern: Host (Name): or Guest (Name): at start of a content line
    speaker_pattern = re.compile(r"^(Host|Guest)\s*\([^)]+\)\s*:")
    timestamp_pattern = re.compile(r"^\[[\d:]+\]")

    content_lines = []
    for line in lines:
        line = line.strip()
        if not line or timestamp_pattern.match(line) or line.startswith("==="):
            continue
        content_lines.append(line)

    if not content_lines:
        return {"metric": "format_compliance", "passed": False, "details": "No content lines found"}

    matching = sum(1 for l in content_lines if speaker_pattern.match(l))
    total = len(content_lines)
    passed = matching / total >= 0.9 if total > 0 else False

    return {
        "metric": "format_compliance",
        "passed": passed,
        "details": f"{matching}/{total} content lines match speaker format ({matching/total*100:.1f}%)",
    }


def check_segment_boundaries(content):
    """Check that no single segment contains both Host: and Guest: labels."""
    # Split into segments by timestamp markers or blank lines
    segments = re.split(r"\n\s*\n|\n(?=\[[\d:]+\])", content)

    mixed_count = 0
    total_segments = 0

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        has_host = bool(re.search(r"^Host\s*\(", seg, re.MULTILINE))
        has_guest = bool(re.search(r"^Guest\s*\(", seg, re.MULTILINE))
        if has_host or has_guest:
            total_segments += 1
            if has_host and has_guest:
                mixed_count += 1

    passed = mixed_count == 0

    return {
        "metric": "segment_boundaries",
        "passed": passed,
        "details": f"{mixed_count} mixed-speaker segments found out of {total_segments} total",
    }


def check_coverage(transcript_content, source_paths):
    """Check that output covers >=90% of source material by character count."""
    if not source_paths:
        return {
            "metric": "coverage",
            "passed": True,
            "details": "No source files provided for comparison — skipped",
        }

    source_total = 0
    for path in source_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                source_total += len(f.read())
        except FileNotFoundError:
            continue

    if source_total == 0:
        return {"metric": "coverage", "passed": True, "details": "Source files empty or not found — skipped"}

    # Strip timestamps, speaker labels, and whitespace for a fairer comparison
    clean_transcript = re.sub(r"\[[\d:]+\]", "", transcript_content)
    clean_transcript = re.sub(r"(Host|Guest)\s*\([^)]+\)\s*:\s*", "", clean_transcript)
    clean_transcript = re.sub(r"\s+", " ", clean_transcript).strip()

    ratio = len(clean_transcript) / source_total
    passed = ratio >= 0.9

    return {
        "metric": "coverage",
        "passed": passed,
        "details": f"Output {len(clean_transcript)} chars vs source {source_total} chars ({ratio*100:.1f}%)",
    }


def check_timestamp_continuity(content):
    """Check that timestamps are monotonically increasing with no large gaps."""
    timestamps = re.findall(r"\[([\d:]+)\]", content)
    if len(timestamps) < 2:
        return {"metric": "timestamp_continuity", "passed": True, "details": "Fewer than 2 timestamps — skipped"}

    seconds_list = [parse_timestamp(ts) for ts in timestamps]
    seconds_list = [s for s in seconds_list if s is not None]

    if len(seconds_list) < 2:
        return {"metric": "timestamp_continuity", "passed": True, "details": "Could not parse timestamps — skipped"}

    gaps = []
    for i in range(1, len(seconds_list)):
        gap = seconds_list[i] - seconds_list[i - 1]
        if gap < -5:  # Allow small backward jumps (rounding)
            gaps.append(f"Backward jump at index {i}: {seconds_list[i-1]}s → {seconds_list[i]}s")
        elif gap > 120:  # Flag gaps > 2 minutes as suspicious (not 2 seconds — podcast segments can be long)
            gaps.append(f"Large gap at index {i}: {gap}s between timestamps")

    passed = len(gaps) == 0

    return {
        "metric": "timestamp_continuity",
        "passed": passed,
        "details": f"{len(gaps)} issues found" + (f": {'; '.join(gaps[:3])}" if gaps else ""),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_transcript.py <transcript_path> [source1 source2 ...] [--episode NAME]"}))
        sys.exit(1)

    transcript_path = sys.argv[1]
    episode_name = "unknown"
    source_paths = []

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--episode" and i + 1 < len(args):
            episode_name = args[i + 1]
            i += 2
        else:
            source_paths.append(args[i])
            i += 1

    content = read_file(transcript_path)
    lines = content.split("\n")

    checks = [
        check_format_compliance(lines),
        check_segment_boundaries(content),
        check_coverage(content, source_paths),
        check_timestamp_continuity(content),
    ]

    scorecard = make_scorecard("transcript_processor", episode_name, checks)
    output_scorecard(scorecard)


if __name__ == "__main__":
    main()
