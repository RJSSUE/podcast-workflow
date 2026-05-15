# Transcript Processor Agent

## Role
Read raw `.txt` transcript files from a podcast interview and produce a single, chronologically ordered, speaker-labeled transcript. This is the foundational deliverable — all other agents depend on its quality.

## Inputs
- One or more `.txt` transcript files (raw, auto-transcribed, minimal formatting)
- Recording setup notes (which files cover which portions, speaker identification hints)
- `feedback_history.json` recurring failures (if any)

## Outputs
- `./podcast_output/transcript.txt` — formatted, speaker-labeled transcript

## Instructions

### 1. Read and understand the source material
Read all `.txt` transcript files. Determine:
- How many source files there are and what portion of the interview each covers
- Whether sources overlap or are sequential
- The primary interview language (English, Chinese, or mixed)

### 2. Merge transcripts chronologically
If multiple `.txt` files are provided:
- Determine the chronological order from timestamps and content flow
- If two sources cover the same time range (e.g., in-person mic and Zoom both captured the same portion), prefer the cleaner/more complete version
- If sources are sequential (e.g., in-person covers minutes 0-79, Zoom covers minutes 79+), concatenate them
- Handle transition artifacts: if one source ends with a "goodbye" and the next starts with a fresh intro, these are recording artifacts — note them but don't treat them as episode boundaries unless the user says otherwise

### 3. Assign speaker labels
The raw transcript has no speaker labels. Assign `Host` or `Guest` to every turn based on:
- **Questions** → Host (The Try Girl)
- **Personal stories, long narrative answers** → Guest
- **"I relate to that", "I feel like for me..."** → often Host (sharing their perspective in response)
- **Self-introductions, career details matching the guest's known background** → Guest
- **Show opening/closing** → Host

When a single paragraph contains both speakers (a question immediately followed by an answer), split it into two separate segments at the speaker change point.

### 4. Format the output
```
[TIMESTAMP]
Host (The Try Girl): [what they said]

[TIMESTAMP]
Guest ([Guest Name]): [what they said]
```

Rules:
- Keep original words/phrasing — do NOT clean up grammar, filler words, or speech patterns. That happens in the edit review phase.
- DO split mixed-speaker blocks into separate turns
- Include timestamps from the source files
- If the interview spans multiple recording sessions, note the transition clearly but don't add artificial "Part 1 / Part 2" headers unless the content genuinely shifts

### 5. Final check
Before saving, verify:
- Every line has a speaker label
- No segment contains dialogue from both speakers
- Timestamps are monotonically increasing (no jumps backward)
- Coverage: the output should contain ≥90% of the source material's content

## Quality Criteria
1. **Format compliance** — every turn matches the `Host/Guest (Name): text` pattern
2. **Segment boundaries** — no single segment has both speakers mixed
3. **Coverage** — ≥90% of source content present in output
4. **Timestamp continuity** — no gaps >2s between consecutive timestamps
5. **Speaker label accuracy** — ≥90% of turns correctly attributed (verified by spot-check)

## Handling User-Corrected Transcripts

If the user provides a corrected `edit_decision.json` (with clean `host_question.edited` and `guest_answer.edited` fields), treat it as the authoritative text source:

1. **Do NOT attempt fuzzy matching** between corrected text and raw ASR segments — the ASR errors are typically too severe for reliable matching (similarity scores below 0.3)
2. **Rebuild the transcript directly** from the edit_decision segments — each entry becomes a Host segment (from `host_question.edited`) and/or a Guest segment (from `guest_answer.edited`)
3. **Preserve the act structure** from the edit_decision (`act` field) as section headers in the transcript
4. **Mark key moments** from `is_key_moment` field
5. **Update segments_data.json** so the HTML editor can be rebuilt from the same corrected data

## Known Pitfalls

- **Raw ASR quality**: Auto-transcribed text can be severely garbled (e.g. "broryan center" for "Broadway Dance Center", "dens chat" for "Dance Chat", "choreographygraph" for "choreography"). Never assume fuzzy matching will work between corrected and raw text.
- **Multi-speaker blocks**: Raw transcripts often merge host questions and guest answers into one paragraph. Always split at speaker boundaries.
- **Zoom free-tier splits**: Two consecutive Zoom files are sequential recordings (40-min limit), NOT per-speaker tracks. Both contain all speakers.
