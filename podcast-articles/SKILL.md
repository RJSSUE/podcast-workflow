---
name: podcast-articles
description: >
  Write bilingual feature articles from a podcast interview transcript. Use when the user wants feature articles written — "write the articles", "create the feature article", "write about this episode". Produces culturally adapted English and Chinese versions. Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Articles

Writes bilingual feature articles (English + Chinese) from a podcast interview, following The Try Girl's distinctive editorial voice.

**Input:** Edited transcript + guest info
**Output:** `podcast_output/article_en.md` + `podcast_output/article_zh.md`

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

**Read `~/.claude/skills/podcast-shared/references/article_style_guide.md` before writing.** The style guide defines the voice, structure, and emotional techniques that make Dance Chat articles distinctive.

---

## Writing Guidelines

Key principles from the style guide:
- **Organize by theme and feeling**, not chronology. Each section has its own emotional arc.
- **Open with contrast or tension** — drop the reader into a moment, not a bio.
- **Vulnerability is the spine.** Weave in doubt, sacrifice, fear as ongoing human texture — not just setbacks to overcome.
- **The subject speaks for themselves.** Direct quotes carry the emotional weight. Author prose sets scenes and bridges themes.
- **Specificity creates emotion.** Concrete details hit harder than abstractions.
- **Evocative section headers** that read like chapter titles, not labels.
- **Close with forward motion**, not a neat bow.

**Length:** 800-1200 words per version.

**Byline format:**
- English: `By The Try Girl | Dance Chat`
- Chinese: `作者：The Try Girl | 舞所不谈`

---

## Process

1. Write **English version** first -> `./podcast_output/article_en.md`
2. Write **Chinese version** (not a direct translation — adapt tone and cultural references for a Chinese readership) -> `./podcast_output/article_zh.md`
