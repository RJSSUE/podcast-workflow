# Evaluation JSON Schemas

Reference for all evaluation-related JSON formats used by the podcast post-production pipeline.

---

## 1. Scorecard (per-agent, per-episode)

Written by `validate_*.py` scripts. One file per agent per episode.

**Files:** `podcast_output/evals/scorecard_transcript.json`, `scorecard_story.json`, `scorecard_html.json`

```json
{
  "agent": "transcript_processor | story_analyst | html_editor_builder",
  "episode": "Melanie",
  "timestamp": "2026-04-07T15:30:00Z",
  "automated_checks": [
    {
      "metric": "format_compliance",
      "passed": true,
      "details": "142/142 lines match speaker format (100.0%)"
    }
  ],
  "human_checks": [
    {
      "metric": "speaker_label_accuracy",
      "passed": true,
      "evidence": "Spot-checked 5 segments, all correct"
    }
  ],
  "summary": {
    "automated_passed": 4,
    "automated_total": 4,
    "human_passed": 1,
    "human_total": 1,
    "overall_pass_rate": 1.0
  }
}
```

### Field reference

| Field | Type | Description |
|-------|------|-------------|
| `agent` | string | Agent identifier: `transcript_processor`, `story_analyst`, or `html_editor_builder` |
| `episode` | string | Episode name (e.g. guest name or episode number) |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `automated_checks[]` | array | Results from deterministic validation scripts |
| `automated_checks[].metric` | string | Metric identifier (e.g. `format_compliance`, `segment_count_match`) |
| `automated_checks[].passed` | boolean | Whether the check passed |
| `automated_checks[].details` | string | Human-readable explanation |
| `human_checks[]` | array | Results from grader agent evaluation |
| `human_checks[].metric` | string | Metric identifier (e.g. `speaker_label_accuracy`) |
| `human_checks[].passed` | boolean | Whether the check passed |
| `human_checks[].evidence` | string | Specific evidence supporting the judgment |
| `summary.overall_pass_rate` | float | 0.0–1.0, (auto_passed + human_passed) / total |

---

## 2. Episode Summary

Written by `aggregate_scores.py`. Combines all 3 agent scorecards into one overview.

**File:** `podcast_output/evals/episode_summary.json`

```json
{
  "episode": "Melanie",
  "timestamp": "2026-04-07T15:35:00Z",
  "agents": {
    "transcript_processor": {
      "pass_rate": 1.0,
      "flags": []
    },
    "story_analyst": {
      "pass_rate": 0.75,
      "flags": ["target_length_adherence: No time estimate found in proposal"]
    },
    "html_editor_builder": {
      "pass_rate": 0.8,
      "flags": ["feature_completeness: Missing: split"]
    }
  },
  "overall_pass_rate": 0.85
}
```

### Field reference

| Field | Type | Description |
|-------|------|-------------|
| `agents.<name>.pass_rate` | float | That agent's overall_pass_rate from its scorecard |
| `agents.<name>.flags` | array | Failed check descriptions (first 100 chars each) |
| `overall_pass_rate` | float | Mean of all agent pass_rates |

---

## 3. Feedback History (cross-episode)

Maintained by `aggregate_scores.py`. Appended after each episode. Used for trend tracking and recurring failure detection.

**File:** `evals/feedback_history.json` (in skill directory)

```json
{
  "episodes": [
    {
      "episode": "Melanie",
      "date": "2026-04-07",
      "scores": {
        "transcript_processor": {
          "overall": 1.0,
          "by_metric": {
            "format_compliance": true,
            "segment_boundaries": true,
            "coverage": true,
            "timestamp_continuity": true
          }
        },
        "story_analyst": {
          "overall": 0.75,
          "by_metric": {
            "rationale_presence": true,
            "qa_pairing_integrity": true,
            "story_arc_present": true,
            "target_length_adherence": false
          }
        }
      }
    }
  ],
  "trends": {
    "transcript_processor": {
      "format_compliance": [true, true, true],
      "segment_boundaries": [true, true, false]
    }
  },
  "recurring_failures": [
    {
      "agent": "story_analyst",
      "metric": "target_length_adherence",
      "failure_rate": 0.4,
      "episodes_affected": ["Melanie", "Episode3"],
      "suggested_fix": "Review story_analyst agent definition for target_length_adherence — failed in 2/5 recent episodes"
    }
  ]
}
```

### Field reference

| Field | Type | Description |
|-------|------|-------------|
| `episodes[]` | array | One entry per processed episode, in chronological order |
| `episodes[].scores.<agent>.by_metric` | object | Metric name → boolean pass/fail |
| `trends` | object | Last 10 episodes' per-metric results, keyed by agent then metric |
| `recurring_failures[]` | array | Metrics that failed in ≥2 of the last 5 episodes |
| `recurring_failures[].failure_rate` | float | Failures / recent episodes examined |
| `recurring_failures[].suggested_fix` | string | Auto-generated remediation hint |

---

## 4. Metric Reference by Agent

### Transcript Processor
| Metric | Type | Script |
|--------|------|--------|
| `format_compliance` | Auto | `validate_transcript.py` |
| `segment_boundaries` | Auto | `validate_transcript.py` |
| `coverage` | Auto | `validate_transcript.py` |
| `timestamp_continuity` | Auto | `validate_transcript.py` |
| `speaker_label_accuracy` | Human | `grader.md` |

### Story Analyst
| Metric | Type | Script |
|--------|------|--------|
| `rationale_presence` | Auto | `validate_edit_proposal.py` |
| `qa_pairing_integrity` | Auto | `validate_edit_proposal.py` |
| `story_arc_present` | Auto | `validate_edit_proposal.py` |
| `target_length_adherence` | Auto | `validate_edit_proposal.py` |
| `story_arc_coherence` | Human | `grader.md` |
| `actionability` | Human | `grader.md` |

### HTML Editor Builder
| Metric | Type | Script |
|--------|------|--------|
| `segment_count_match` | Auto | `validate_html.py` |
| `export_json_schema` | Auto | `validate_html.py` |
| `feature_completeness` | Auto | `validate_html.py` |
| `speaker_labels_present` | Auto | `validate_html.py` |
| `no_js_errors` | Auto | `validate_html.py` |
