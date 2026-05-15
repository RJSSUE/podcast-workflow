---
name: podcast-shownotes
description: >
  Generate bilingual show notes for podcast platforms. Use when the user wants show notes — "write show notes", "create the episode description", "generate show notes for Apple Podcasts". Produces English (Dance Chat) and Chinese (舞所不谈) versions. Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Show Notes

Generates practical, scannable show notes for both podcast platforms.

**Input:** Edited transcript + guest info
**Output:** `podcast_output/shownotes_en.md` (Dance Chat) + `podcast_output/shownotes_zh.md` (舞所不谈)

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

---

## Structure

```
[Episode Title]
[One-line description]

In this episode: [2-3 sentence summary]

About [Guest Name]: [3-4 sentence bio]

Key Topics Discussed:
- [Topic 1]
- [Topic 2]
- [Topic 3]
(5-8 bullet points)

Timestamps:
[00:00] Introduction
[XX:XX] [Topic]
... (estimated from transcript structure — mark as approximate)

Connect with [Guest]:
[Placeholder — ask user to fill in]

Connect with the Podcast:
Dance Chat — Apple Podcasts [link placeholder]
舞所不谈 — [Chinese platform link placeholder]
Instagram: @thetrygirl (confirm handle with user)
```

---

## Process

1. Write **English show notes** (for Dance Chat) -> `./podcast_output/shownotes_en.md`
2. Write **Chinese show notes** (for 舞所不谈) -> `./podcast_output/shownotes_zh.md`

Chinese show notes should not be a direct translation — adapt phrasing and framing for the Chinese-platform audience.
