# podcast-workflow

A complete podcast post-production toolkit for [Claude Code](https://claude.ai/claude-code). Turn raw audio recordings into polished episodes with transcripts, show notes, articles, social media copy, and highlight clips — all driven by AI-powered Claude Code skills.

## Quick Install

```bash
git clone https://github.com/rjssue/podcast-workflow.git
cd podcast-workflow
./install.sh
```

Then customize `podcast-shared/config.md` with your show name and host name.

### Prerequisites

| Tool | Install |
|------|---------|
| [Claude Code](https://claude.ai/claude-code) | Required — these are Claude Code skills |
| [ffmpeg](https://ffmpeg.org/) | `brew install ffmpeg` |
| Python 3 | `brew install python3` |
| [OpenAI Whisper](https://github.com/openai/whisper) | `pip install openai-whisper` |
| [edge-tts](https://github.com/rany2/edge-tts) | `pip install edge-tts` |

## Skills

After installation, invoke any skill with `/<skill-name>` in Claude Code.

### Core Pipeline

| Skill | What it does |
|-------|-------------|
| `/podcast-post-production` | Full end-to-end pipeline — provide raw audio + guest name, get everything below |
| `/podcast-asr` | Transcribe raw audio to timestamped text using OpenAI Whisper |
| `/podcast-transcribe` | Format raw transcript with Host/Guest speaker labels |
| `/podcast-normalize` | Equalize volume levels between speakers (loudness normalization) |
| `/podcast-clean` | Remove filler words and trim long pauses |
| `/podcast-storyline` | Analyze transcript and propose a cohesive story arc with edit recommendations |
| `/podcast-audio` | Compile final edited audio from edit decisions + raw audio files |
| `/podcast-editor` | Build an interactive HTML drag-and-drop transcript editor for review |

### Content Generation

| Skill | What it does |
|-------|-------------|
| `/podcast-articles` | Write feature articles from the interview transcript |
| `/podcast-shownotes` | Generate show notes for podcast platforms |
| `/podcast-instagram` | Write Instagram captions and hashtags |
| `/podcast-summary` | Generate an AI-narrated summary audio |

### Video

| Skill | What it does |
|-------|-------------|
| `/podcast-highlights` | Cut highlight clips/reels from podcast video recordings |
| `/podcast-videoclip` | Produce Instagram-ready MP4 with aligned audio, subtitles, and outro |

## Workflow Tools

Browser-based tools for scheduling and clip planning. Also deployed at:
**https://rjssue.github.io/podcast-workflow/tools/**

| Tool | Description |
|------|-------------|
| [Guest Scheduler](tools/podcast-scheduler/) | Collect guest availability for recording sessions — no backend needed |
| [Clip Planner](tools/clip-planner.html) | Plan and organize podcast clip segments |
| [Clip Editor](tools/clip-editor.html) | Visual editor for reviewing clips |

## How It Works

```
Raw audio files
    |
    v
/podcast-asr ──> /podcast-transcribe ──> /podcast-normalize
    |                                           |
    v                                           v
/podcast-storyline ──> /podcast-editor ──> /podcast-audio
    |                                           |
    v                                           v
/podcast-articles                        Final edited WAV
/podcast-shownotes
/podcast-instagram
/podcast-summary
/podcast-highlights
/podcast-videoclip
```

Each skill works **standalone** (just run the one you need) or as part of the full `/podcast-post-production` pipeline.

## Configuration

After running `install.sh`, edit `podcast-shared/config.md` to set:
- Your show name and host name
- Audio format preferences (defaults to WAV 24-bit/48kHz, -16 LUFS)
- TTS voice options for AI-generated summaries
- Multi-track recording conventions

## Uninstall

```bash
./uninstall.sh
```

This removes the symlinks from `~/.claude/skills/` but keeps the repo intact.

## License

MIT
