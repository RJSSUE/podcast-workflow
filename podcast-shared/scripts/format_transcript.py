#!/usr/bin/env python3
"""Format a raw timestamp+text transcript into speaker-labeled segments.

Parses the common raw podcast transcript format (alternating timestamp and text
lines) and assigns speakers using text-based pattern matching.

Usage:
  python format_transcript.py <raw_transcript.txt> \
    --guest "Guest Name" \
    [--host "Host Name"] \
    [--patterns patterns.json] \
    [--output podcast_output/formatted_transcript.txt] \
    [--segments-json podcast_output/segments.json] \
    [--language zh|en]

Pattern file format (JSON):
{
  "guest_patterns": ["regex1", "regex2", ...],
  "host_patterns": ["regex1", "regex2", ...],
  "guest_strong": ["high-confidence regex", ...],
  "host_strong": ["high-confidence regex", ...]
}

If no pattern file is provided, uses generic heuristics:
  - Questions (？or ?) → likely host
  - Short interjections (< 30 chars) → alternate from previous
  - First/last segment → host
"""

import json
import re
import sys
from pathlib import Path


def parse_raw_transcript(text):
    """Parse alternating timestamp/text lines into blocks."""
    lines = text.split("\n")
    blocks = []
    current_ts = None
    current_text_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        ts_match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)$', stripped)
        if ts_match:
            if current_text_lines:
                blocks.append({
                    "start_time": current_ts,
                    "text": " ".join(current_text_lines),
                })
                current_text_lines = []
            current_ts = ts_match.group(1)
        else:
            current_text_lines.append(stripped)

    if current_text_lines:
        blocks.append({"start_time": current_ts, "text": " ".join(current_text_lines)})

    return blocks


def normalize_ts(ts):
    if ts is None:
        return "00:00:00"
    parts = ts.split(":")
    if len(parts) == 2:
        return f"00:{int(parts[0]):02d}:{int(parts[1]):02d}"
    elif len(parts) == 3:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
    return "00:00:00"


def assign_end_times(blocks):
    for i in range(len(blocks) - 1):
        blocks[i]["end_time"] = blocks[i + 1]["start_time"]
    if blocks:
        # Estimate last block end time: start + text length heuristic
        last_start = ts_to_seconds(blocks[-1]["start_time"])
        duration = max(5, len(blocks[-1]["text"]) / 15)
        blocks[-1]["end_time"] = seconds_to_ts(last_start + duration)


def ts_to_seconds(ts):
    parts = [float(p) for p in ts.split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def seconds_to_ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_speaker_assigner(patterns, language="zh"):
    """Build a speaker assignment function from pattern config."""

    guest_pats = [re.compile(p, re.IGNORECASE) for p in patterns.get("guest_patterns", [])]
    host_pats = [re.compile(p, re.IGNORECASE) for p in patterns.get("host_patterns", [])]
    guest_strong = [re.compile(p, re.IGNORECASE) for p in patterns.get("guest_strong", [])]
    host_strong = [re.compile(p, re.IGNORECASE) for p in patterns.get("host_strong", [])]

    # Language-specific question markers
    q_mark = "？" if language == "zh" else "?"

    def assign(text, idx, all_blocks):
        if idx == 0:
            return "Host"
        if idx == len(all_blocks) - 1:
            return "Host"

        guest_score = 0
        host_score = 0

        for pat in guest_pats:
            if pat.search(text):
                guest_score += 1
        for pat in host_pats:
            if pat.search(text):
                host_score += 1
        for pat in guest_strong:
            if pat.search(text):
                guest_score += 5
        for pat in host_strong:
            if pat.search(text):
                host_score += 5

        # Question heuristic
        q_count = text.count(q_mark) + text.count("?")
        if q_count >= 2:
            host_score += 2
        elif q_count >= 1:
            host_score += 1

        # Long narrative with first-person
        if language == "zh" and len(text) > 200:
            if re.search(r"我(就|觉得|是|会|在|从|也)", text):
                # Long first-person narrative — could be either, slight guest lean
                guest_score += 1
        elif language == "en" and len(text) > 500:
            if re.search(r"\b(I joined|I was|I started|I left|I moved)\b", text):
                guest_score += 3

        # Short interjections in Chinese often come from the listener
        if language == "zh" and len(text) < 15:
            # Very short (嗯, 对, 是的, etc.) — lean toward listener interjection
            pass  # Let alternation handle it

        if guest_score > host_score:
            return "Guest"
        elif host_score > guest_score:
            return "Host"
        else:
            # Tie: alternate from previous speaker
            if idx > 0:
                prev = all_blocks[idx - 1].get("speaker", "Host")
                return "Guest" if prev == "Host" else "Host"
            return "Guest"

    return assign


def format_and_assign(raw_path, guest_name, host_name="Host",
                      patterns=None, language="zh"):
    """Parse raw transcript, assign speakers, return segments list."""

    with open(raw_path, "r", encoding="utf-8") as f:
        raw = f.read()

    blocks = parse_raw_transcript(raw)

    for b in blocks:
        b["start_time"] = normalize_ts(b["start_time"])
    assign_end_times(blocks)

    if patterns is None:
        patterns = {"guest_patterns": [], "host_patterns": [],
                    "guest_strong": [], "host_strong": []}

    assigner = build_speaker_assigner(patterns, language)

    for i, block in enumerate(blocks):
        block["speaker"] = assigner(block["text"], i, blocks)

    # Build segments
    segments = []
    for i, block in enumerate(blocks):
        segments.append({
            "id": f"seg_{i + 1:03d}",
            "speaker": block["speaker"],
            "text": block["text"],
            "original_text": block["text"],
            "edited_text": "",
            "start_time": block["start_time"],
            "end_time": block["end_time"],
            "original_position": i + 1,
            "status": "keep",
            "muted_ranges": [],
            "act": None,
            "is_key_moment": False,
            "source": None,
            "suggested": False,
            "suggestion_info": None,
        })

    # Stats
    host_count = sum(1 for s in segments if s["speaker"] == "Host")
    guest_count = sum(1 for s in segments if s["speaker"] == "Guest")
    print(f"Parsed {len(segments)} segments: {host_count} Host, {guest_count} Guest")

    return segments


def write_formatted_transcript(segments, output_path, guest_name, host_name="Host"):
    """Write formatted transcript as Speaker (Name): text per line."""
    lines = []
    for seg in segments:
        speaker_label = f"{host_name} (The Try Girl)" if seg["speaker"] == "Host" else f"Guest ({guest_name})"
        lines.append(f"[{seg['start_time']}]")
        lines.append(f"{speaker_label}: {seg['text']}")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote formatted transcript: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: format_transcript.py <raw.txt> --guest NAME [--host NAME] "
              "[--patterns FILE] [--output FILE] [--segments-json FILE] [--language zh|en]")
        sys.exit(1)

    raw_path = sys.argv[1]
    guest_name = "Guest"
    host_name = "Host"
    patterns_file = None
    output_path = None
    segments_json_path = None
    language = "zh"

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--guest" and i + 1 < len(args):
            guest_name = args[i + 1]; i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host_name = args[i + 1]; i += 2
        elif args[i] == "--patterns" and i + 1 < len(args):
            patterns_file = args[i + 1]; i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]; i += 2
        elif args[i] == "--segments-json" and i + 1 < len(args):
            segments_json_path = args[i + 1]; i += 2
        elif args[i] == "--language" and i + 1 < len(args):
            language = args[i + 1]; i += 2
        else:
            i += 1

    patterns = None
    if patterns_file:
        with open(patterns_file, "r", encoding="utf-8") as f:
            patterns = json.load(f)

    if output_path is None:
        output_path = str(Path(raw_path).parent / "podcast_output" / "formatted_transcript.txt")

    segments = format_and_assign(raw_path, guest_name, host_name, patterns, language)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    write_formatted_transcript(segments, output_path, guest_name, host_name)

    if segments_json_path:
        Path(segments_json_path).parent.mkdir(parents=True, exist_ok=True)
        with open(segments_json_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        print(f"Wrote segments JSON: {segments_json_path}")


if __name__ == "__main__":
    main()
