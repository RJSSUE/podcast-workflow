#!/usr/bin/env python3
"""Aggregate per-agent scorecards into episode summary and update cross-episode history.

Usage: python aggregate_scores.py <evals_dir> [--episode NAME] [--history-path PATH]

Reads scorecard_transcript.json, scorecard_story.json, scorecard_html.json from <evals_dir>.
Writes episode_summary.json to <evals_dir>.
Appends to feedback_history.json (default: ../../evals/feedback_history.json relative to this script).
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_scorecard(evals_dir, filename):
    """Load a scorecard JSON file, returning None if it doesn't exist."""
    path = os.path.join(evals_dir, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_episode_summary(scorecards, episode_name):
    """Build an episode summary from individual scorecards."""
    agents = {}
    for sc in scorecards:
        if sc is None:
            continue
        agent = sc["agent"]
        summary = sc.get("summary", {})
        flags = []

        # Collect failed checks as flags
        for check in sc.get("automated_checks", []) + sc.get("human_checks", []):
            if check.get("passed") is False:
                flags.append(f"{check['metric']}: {check.get('details', 'failed')[:100]}")

        agents[agent] = {
            "pass_rate": summary.get("overall_pass_rate", 0.0),
            "flags": flags,
        }

    overall_rates = [a["pass_rate"] for a in agents.values()]
    overall = round(sum(overall_rates) / len(overall_rates), 2) if overall_rates else 0.0

    return {
        "episode": episode_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agents": agents,
        "overall_pass_rate": overall,
    }


def update_feedback_history(history_path, episode_summary, scorecards):
    """Append episode data to feedback_history.json and recompute trends."""
    # Load or create history
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {"episodes": [], "trends": {}, "recurring_failures": []}

    # Build per-metric episode entry
    episode_scores = {}
    for sc in scorecards:
        if sc is None:
            continue
        agent = sc["agent"]
        by_metric = {}
        for check in sc.get("automated_checks", []) + sc.get("human_checks", []):
            by_metric[check["metric"]] = check.get("passed", None)
        episode_scores[agent] = {
            "overall": sc.get("summary", {}).get("overall_pass_rate", 0.0),
            "by_metric": by_metric,
        }

    history["episodes"].append({
        "episode": episode_summary["episode"],
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "scores": episode_scores,
    })

    # Recompute trends (last 10 episodes)
    recent = history["episodes"][-10:]
    trends = {}
    for ep in recent:
        for agent, data in ep.get("scores", {}).items():
            if agent not in trends:
                trends[agent] = {}
            for metric, passed in data.get("by_metric", {}).items():
                if metric not in trends[agent]:
                    trends[agent][metric] = []
                trends[agent][metric].append(passed)

    history["trends"] = trends

    # Identify recurring failures (failed in >=2 of last 5 episodes)
    recent_5 = history["episodes"][-5:]
    recurring = []
    for agent, metrics in trends.items():
        for metric, results in metrics.items():
            recent_results = results[-5:]
            failures = sum(1 for r in recent_results if r is False)
            if failures >= 2:
                affected = []
                for ep in recent_5:
                    if ep.get("scores", {}).get(agent, {}).get("by_metric", {}).get(metric) is False:
                        affected.append(ep["episode"])
                recurring.append({
                    "agent": agent,
                    "metric": metric,
                    "failure_rate": round(failures / len(recent_results), 2),
                    "episodes_affected": affected,
                    "suggested_fix": f"Review {agent} agent definition for {metric} — failed in {failures}/{len(recent_results)} recent episodes",
                })

    history["recurring_failures"] = recurring

    # Write updated history
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return history


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: aggregate_scores.py <evals_dir> [--episode NAME] [--history-path PATH]"}))
        sys.exit(1)

    evals_dir = sys.argv[1]
    episode_name = "unknown"
    # Default: skill's evals directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_path = os.path.join(script_dir, "..", "evals", "feedback_history.json")

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--episode" and i + 1 < len(args):
            episode_name = args[i + 1]
            i += 2
        elif args[i] == "--history-path" and i + 1 < len(args):
            history_path = args[i + 1]
            i += 2
        else:
            i += 1

    # Load scorecards
    sc_transcript = load_scorecard(evals_dir, "scorecard_transcript.json")
    sc_story = load_scorecard(evals_dir, "scorecard_story.json")
    sc_html = load_scorecard(evals_dir, "scorecard_html.json")

    scorecards = [sc_transcript, sc_story, sc_html]
    loaded = [sc for sc in scorecards if sc is not None]

    if not loaded:
        print(json.dumps({"error": f"No scorecards found in {evals_dir}"}))
        sys.exit(1)

    # Build episode summary
    summary = build_episode_summary(loaded, episode_name)

    # Write episode summary
    summary_path = os.path.join(evals_dir, "episode_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Update cross-episode history
    history = update_feedback_history(history_path, summary, loaded)

    # Output summary to stdout
    output = {
        "episode_summary": summary,
        "recurring_failures": history.get("recurring_failures", []),
        "episodes_tracked": len(history.get("episodes", [])),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
