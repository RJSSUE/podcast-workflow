#!/usr/bin/env python3
"""Validate story analyst edit proposal output.

Usage: python validate_edit_proposal.py <proposal_path> [--episode NAME] [--target-minutes N]

Outputs JSON scorecard to stdout.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import make_scorecard, output_scorecard, read_file


def check_rationale_presence(content):
    """Check that each proposed edit has a non-empty rationale."""
    # Look for numbered items in cut/merge/reorder sections
    # Pattern: "N. ... — **Rationale:** ..." or "N. ... Rationale: ..."
    sections = re.split(r"^#{1,3}\s+", content, flags=re.MULTILINE)

    edit_sections = []
    for section in sections:
        header = section.split("\n")[0].lower()
        if any(kw in header for kw in ["cut", "merge", "reorder", "trim"]):
            edit_sections.append(section)

    if not edit_sections:
        return {
            "metric": "rationale_presence",
            "passed": False,
            "details": "No edit sections (Cuts/Merges/Reorders) found in proposal",
        }

    # Count items with and without rationales
    total_items = 0
    items_with_rationale = 0

    for section in edit_sections:
        # Find numbered items
        items = re.findall(r"^\d+\.\s+.+", section, re.MULTILINE)
        for item in items:
            total_items += 1
            # Check for rationale markers
            if re.search(r"(rationale|reason|because|why|this\s+improves|this\s+creates|for\s+better)", item, re.IGNORECASE):
                items_with_rationale += 1
            elif len(item) > 80:
                # Long items likely contain inline reasoning
                items_with_rationale += 1

    if total_items == 0:
        return {
            "metric": "rationale_presence",
            "passed": False,
            "details": "No numbered edit items found in edit sections",
        }

    ratio = items_with_rationale / total_items
    passed = ratio >= 0.8

    return {
        "metric": "rationale_presence",
        "passed": passed,
        "details": f"{items_with_rationale}/{total_items} items have rationale ({ratio*100:.0f}%)",
    }


def check_qa_pairing(content):
    """Check that the proposal doesn't cut host questions while keeping guest answers."""
    # This is a heuristic check — look for explicit mentions of keeping Q&A pairs
    mentions_pairing = bool(re.search(r"(host.*question|Q&A|question.*answer|pair)", content, re.IGNORECASE))

    # Check if any cut suggestions mention cutting ONLY a host question
    # Pattern: cut recommendation that mentions host/question but not the guest response
    cuts_section = ""
    in_cuts = False
    for line in content.split("\n"):
        if re.match(r"^#{1,3}\s+.*[Cc]ut", line):
            in_cuts = True
            continue
        elif re.match(r"^#{1,3}\s+", line):
            in_cuts = False
        if in_cuts:
            cuts_section += line + "\n"

    # Look for items that cut only host turns
    host_only_cuts = re.findall(r"\d+\.\s+.*[Hh]ost.*(?:cut|remove|delete)", cuts_section)
    suspicious = [c for c in host_only_cuts if "guest" not in c.lower() and "answer" not in c.lower()]

    passed = len(suspicious) == 0

    return {
        "metric": "qa_pairing_integrity",
        "passed": passed,
        "details": f"{len(suspicious)} potential orphaned Q&A cuts found" + (f": {suspicious[0][:80]}..." if suspicious else ""),
    }


def check_story_arc_present(content):
    """Check that the proposal includes a story arc section."""
    has_arc = bool(re.search(r"(story\s+arc|narrative\s+arc|narrative\s+journey|episode\s+flow)", content, re.IGNORECASE))
    has_structure = bool(re.search(r"(beginning|hook|opening|intro).*(middle|development|body).*(end|closing|resolution)", content, re.IGNORECASE | re.DOTALL))

    # Also check for episode split discussion if the content is long
    has_split_discussion = bool(re.search(r"(episode\s+1|episode\s+2|split|two\s+episodes)", content, re.IGNORECASE))

    passed = has_arc or has_structure

    return {
        "metric": "story_arc_present",
        "passed": passed,
        "details": f"Story arc section: {'found' if has_arc else 'missing'}. Narrative structure: {'found' if has_structure else 'missing'}. Episode split: {'discussed' if has_split_discussion else 'not discussed'}",
    }


def check_estimated_length(content, target_minutes=75):
    """Check that the proposal includes an estimated final length."""
    # Look for time estimates
    time_patterns = re.findall(r"(\d{2,3})\s*(?:min|minute)", content, re.IGNORECASE)
    has_estimate = len(time_patterns) > 0

    if has_estimate:
        estimates = [int(t) for t in time_patterns]
        within_range = any(60 <= e <= 85 for e in estimates)
        details = f"Estimated lengths found: {', '.join(str(e) + ' min' for e in estimates)}. Within 70-80 min target: {'yes' if within_range else 'no'}"
        passed = within_range
    else:
        details = "No time estimate found in proposal"
        passed = False

    return {
        "metric": "target_length_adherence",
        "passed": passed,
        "details": details,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_edit_proposal.py <proposal_path> [--episode NAME] [--target-minutes N]"}))
        sys.exit(1)

    proposal_path = sys.argv[1]
    episode_name = "unknown"
    target_minutes = 75

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--episode" and i + 1 < len(args):
            episode_name = args[i + 1]
            i += 2
        elif args[i] == "--target-minutes" and i + 1 < len(args):
            target_minutes = int(args[i + 1])
            i += 2
        else:
            i += 1

    content = read_file(proposal_path)

    checks = [
        check_rationale_presence(content),
        check_qa_pairing(content),
        check_story_arc_present(content),
        check_estimated_length(content, target_minutes),
    ]

    scorecard = make_scorecard("story_analyst", episode_name, checks)
    output_scorecard(scorecard)


if __name__ == "__main__":
    main()
