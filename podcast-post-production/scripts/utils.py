"""Shared utilities for podcast post-production validation scripts."""

import json
import sys
from datetime import datetime


def make_scorecard(agent_name, episode_name, automated_checks, human_checks=None):
    """Build a scorecard dict in the standard format."""
    if human_checks is None:
        human_checks = []

    auto_passed = sum(1 for c in automated_checks if c["passed"])
    auto_total = len(automated_checks)
    human_passed = sum(1 for c in human_checks if c.get("passed") is True)
    human_total = len(human_checks)

    total_passed = auto_passed + human_passed
    total = auto_total + human_total

    return {
        "agent": agent_name,
        "episode": episode_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "automated_checks": automated_checks,
        "human_checks": human_checks,
        "summary": {
            "automated_passed": auto_passed,
            "automated_total": auto_total,
            "human_passed": human_passed,
            "human_total": human_total,
            "overall_pass_rate": round(total_passed / total, 2) if total > 0 else 0.0,
        },
    }


def output_scorecard(scorecard):
    """Print scorecard as JSON to stdout."""
    print(json.dumps(scorecard, indent=2))


def parse_timestamp(ts_str):
    """Parse a timestamp string like '00:01', '1:19:32', or '00:00:00' into total seconds."""
    ts_str = ts_str.strip().lstrip("[").rstrip("]")
    parts = ts_str.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


def read_file(path):
    """Read a file and return its contents, or exit with error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {path}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Error reading {path}: {str(e)}"}))
        sys.exit(1)
