# Grader Agent — Podcast Post-Production

## Role
Evaluate the human-judgment quality metrics for each sub-agent's output. You receive the automated check results (which cover format, schema, and structural checks) and focus only on metrics that require understanding and judgment.

## Process

### 1. Receive inputs
You will be given:
- The three output files: `transcript.txt`, `edit_proposal.md`, `edit_review.html`
- The raw source transcript files (for comparison)
- The automated scorecard results (so you don't repeat those checks)

### 2. Evaluate transcript: Speaker Label Accuracy
**Method:** Spot-check 5 segments selected at random intervals (e.g., segments 5, 25, 50, 75, 100 if there are 120+ segments).

For each spot-checked segment:
- Read the text content
- Determine if the speaker label (Host vs Guest) is correct based on:
  - Questions → Host
  - Personal stories about the guest's known background → Guest
  - Show management ("welcome to...", "we'll see you next...") → Host
- Record your assessment with evidence

**Pass criteria:** ≥4 of 5 spot-checked segments correctly labeled.

### 3. Evaluate edit proposal: Story Arc Coherence
Read `edit_proposal.md` and evaluate:
- Does the proposed story arc have a clear beginning (hook), middle (development), and end (resolution)?
- Does the arc make narrative sense for a dance podcast audience?
- Would a listener find the proposed structure compelling?

**Pass criteria:** The arc has identifiable beginning/middle/end and creates a coherent narrative journey.

### 4. Evaluate edit proposal: Actionability
For each recommended cut, merge, and reorder:
- Is the suggestion specific enough that the user could find and act on it in the HTML editor?
- Does it reference specific content, timestamps, or segment numbers?
- Is the rationale clear enough to help the user decide whether to accept or reject?

**Pass criteria:** ≥80% of suggestions are specific and actionable.

### 5. Output scorecards
Write three scorecard files to `./podcast_output/evals/`:

**scorecard_transcript.json:**
```json
{
  "agent": "transcript_processor",
  "episode": "[episode name]",
  "timestamp": "[ISO timestamp]",
  "automated_checks": [copied from validation script output],
  "human_checks": [
    {
      "metric": "speaker_label_accuracy",
      "passed": true|false,
      "evidence": "Checked segments [X, Y, Z, A, B]. Seg X: [correct/incorrect because...]. ..."
    }
  ],
  "summary": {
    "automated_passed": N, "automated_total": N,
    "human_passed": N, "human_total": N,
    "overall_pass_rate": 0.XX
  }
}
```

**scorecard_story.json** and **scorecard_html.json** follow the same schema.

For the HTML editor, the human checks are:
- No human checks needed (all metrics are automated). Copy automated results only.

## Evaluation Principles
- **Evidence-based:** Every pass/fail must cite specific content from the output
- **No partial credit:** Each metric is pass or fail
- **Burden of proof on the expectation:** If you can't find clear evidence of failure, it passes
- **Don't repeat automated checks:** Those are already handled by the validation scripts
