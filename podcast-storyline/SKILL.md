---
name: podcast-storyline
description: >
  Analyze a podcast interview transcript and propose a cohesive story arc with edit recommendations. Use when the user wants narrative analysis, story structure, or edit proposals for an interview — "analyze the storyline", "propose edits", "create a story arc", "what should we cut". Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Storyline

Analyzes a podcast interview transcript as a narrative editor. Proposes a story arc, identifies cuts, merges, and reorders that transform raw conversation into a compelling, cohesive episode.

**Input:** Transcript (formatted or raw `.txt`) + guest info + target length
**Output:** `podcast_output/edit_proposal.md`

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

### Get episode metadata (if not already known)
- **Guest name**
- **Interview language**
- **Target episode length** (default: 70–80 minutes per episode)

---

## Processing

Read `~/.claude/skills/podcast-shared/agents/story_analyst.md` and follow its instructions.

Before spawning the story analyst agent:
1. Read `~/.claude/skills/podcast-shared/evals/feedback_history.json` — extract `recurring_failures` array
2. Inject any recurring failures as "KNOWN ISSUES FROM PRIOR EPISODES" context

The agent produces:
- A narrative story arc analysis
- Numbered edit plan with cuts, merges, reorders (all with rationale)
- Written to `./podcast_output/edit_proposal.md` and summarized inline

---

## Validation

After processing, validate the output:

```bash
python ~/.claude/skills/podcast-shared/scripts/validate_edit_proposal.py \
  ./podcast_output/edit_proposal.md \
  --episode "<GUEST_NAME>"
```

Save the scorecard to `podcast_output/evals/scorecard_story.json`.
