#!/usr/bin/env python3
"""Validate ASR processor output.

Usage: python validate_asr.py <asr_raw_path> --audio <audio_path> [--episode NAME]

Outputs JSON scorecard to stdout.
"""

import json
import os
import re
import subprocess
import sys

# Add parent directory so we can import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import make_scorecard, output_scorecard, parse_timestamp, read_file


def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        return None


def check_duration_match(content, audio_path):
    """Check that ASR transcript duration roughly matches audio duration (within 5%)."""
    audio_duration = get_audio_duration(audio_path)
    if audio_duration is None:
        return {"metric": "duration_match", "passed": True,
                "details": "Could not determine audio duration — skipped"}

    # Find the last timestamp in the transcript
    timestamps = re.findall(r"\[[\d:]+ - ([\d:]+)\]", content)
    if not timestamps:
        return {"metric": "duration_match", "passed": False,
                "details": "No timestamps found in ASR output"}

    last_ts = parse_timestamp(timestamps[-1])
    if last_ts is None:
        return {"metric": "duration_match", "passed": False,
                "details": f"Could not parse last timestamp: {timestamps[-1]}"}

    ratio = last_ts / audio_duration
    passed = 0.90 <= ratio <= 1.05

    return {
        "metric": "duration_match",
        "passed": passed,
        "details": f"ASR ends at {last_ts}s, audio is {audio_duration:.1f}s ({ratio*100:.1f}%)",
    }


def check_timestamp_coverage(content):
    """Check that segments cover >=95% of the total duration with no large gaps."""
    matches = re.findall(r"\[([\d:]+) - ([\d:]+)\]", content)
    if len(matches) < 2:
        return {"metric": "timestamp_coverage", "passed": True,
                "details": "Fewer than 2 segments — skipped"}

    parsed = []
    for start_str, end_str in matches:
        start = parse_timestamp(start_str)
        end = parse_timestamp(end_str)
        if start is not None and end is not None:
            parsed.append((start, end))

    if not parsed:
        return {"metric": "timestamp_coverage", "passed": False,
                "details": "Could not parse any timestamps"}

    total_duration = parsed[-1][1] - parsed[0][0]
    if total_duration <= 0:
        return {"metric": "timestamp_coverage", "passed": False,
                "details": "Total duration is zero or negative"}

    covered = sum(end - start for start, end in parsed)
    coverage = covered / total_duration

    # Check for large gaps (>30s of silence)
    large_gaps = []
    for i in range(1, len(parsed)):
        gap = parsed[i][0] - parsed[i - 1][1]
        if gap > 30:
            large_gaps.append(f"{gap:.0f}s gap at {parsed[i-1][1]:.0f}s")

    passed = coverage >= 0.95 and len(large_gaps) == 0

    details = f"Coverage: {coverage*100:.1f}%"
    if large_gaps:
        details += f"; {len(large_gaps)} large gaps: {'; '.join(large_gaps[:3])}"

    return {"metric": "timestamp_coverage", "passed": passed, "details": details}


def check_segment_count(content):
    """Check that there's a reasonable number of segments (>10 for a podcast)."""
    segments = re.findall(r"\[[\d:]+ - [\d:]+\]", content)
    count = len(segments)
    passed = count >= 10

    return {
        "metric": "segment_count",
        "passed": passed,
        "details": f"{count} segments found" + (" (too few for a podcast)" if not passed else ""),
    }


def check_content_not_empty(content):
    """Check that segments contain actual text, not just timestamps."""
    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("===")]
    text_lines = [l for l in lines if re.match(r"\[[\d:]+ - [\d:]+\]\s+\S", l)]
    empty_lines = [l for l in lines if re.match(r"\[[\d:]+ - [\d:]+\]\s*$", l)]

    total = len(text_lines) + len(empty_lines)
    if total == 0:
        return {"metric": "content_not_empty", "passed": False,
                "details": "No segment lines found"}

    ratio = len(text_lines) / total
    passed = ratio >= 0.95

    return {
        "metric": "content_not_empty",
        "passed": passed,
        "details": f"{len(text_lines)}/{total} segments have text content ({ratio*100:.1f}%)",
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_asr.py <asr_raw_path> --audio <audio_path> [--episode NAME]"}))
        sys.exit(1)

    asr_path = sys.argv[1]
    audio_path = None
    episode_name = "unknown"

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--audio" and i + 1 < len(args):
            audio_path = args[i + 1]
            i += 2
        elif args[i] == "--episode" and i + 1 < len(args):
            episode_name = args[i + 1]
            i += 2
        else:
            i += 1

    content = read_file(asr_path)

    checks = [
        check_segment_count(content),
        check_timestamp_coverage(content),
        check_content_not_empty(content),
    ]

    if audio_path:
        checks.insert(0, check_duration_match(content, audio_path))

    scorecard = make_scorecard("asr_processor", episode_name, checks)
    output_scorecard(scorecard)


if __name__ == "__main__":
    main()
