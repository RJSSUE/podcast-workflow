---
name: podcast-instagram
description: >
  Write Instagram post captions and hashtags for a podcast episode. Use when the user wants social media copy — "write Instagram post", "create captions", "social media copy for this episode". Works standalone or as part of the full podcast-post-production pipeline.
---

# Podcast Instagram

Writes Instagram post captions with bilingual hashtags for episode promotion.

**Input:** Guest info + episode highlights (from transcript or articles)
**Output:** `podcast_output/instagram_post.txt`

---

## Setup

Read `~/.claude/skills/podcast-shared/config.md` for show defaults and shared configuration.

---

## Caption Options

Write **3 caption options** at different lengths/styles:

1. **Short & punchy** (<=150 chars) — Hook + episode link CTA
2. **Medium storytelling** (<=300 chars) — One powerful quote or insight + CTA
3. **Full caption** (<=500 chars) — Story setup + key takeaway + CTA + hashtag line

---

## Hashtag Block

Generate 15-20 hashtags based on the guest's dance style and background. Always include:
`#舞所不谈 #DanceChat #TheTryGirl #dancepodcast #舞蹈播客`

Then add guest-specific style tags (e.g. `#contemporarydance`, `#hiphop`, `#ballet`, `#ballroom`, `#breaking`) and community reach tags in both English and Chinese.

Append the hashtag block to all three caption options.

---

## Process

Save all options as `./podcast_output/instagram_post.txt`.
