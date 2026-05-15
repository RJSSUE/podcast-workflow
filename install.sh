#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

mkdir -p "$SKILLS_DIR"

SKILLS=(
  podcast-shared
  podcast-asr
  podcast-transcribe
  podcast-normalize
  podcast-clean
  podcast-storyline
  podcast-audio
  podcast-editor
  podcast-articles
  podcast-shownotes
  podcast-instagram
  podcast-summary
  podcast-highlights
  podcast-videoclip
  podcast-post-production
)

echo "Installing podcast-workflow skills..."
echo ""

for skill in "${SKILLS[@]}"; do
  target="$SKILLS_DIR/$skill"
  source="$SCRIPT_DIR/$skill"

  if [ -L "$target" ]; then
    rm "$target"
  elif [ -d "$target" ]; then
    echo "  SKIP $skill (directory exists, not a symlink — back up and remove manually)"
    continue
  fi

  ln -s "$source" "$target"
  echo "  OK   $skill"
done

echo ""
echo "Done! ${#SKILLS[@]} skills installed."
echo "Run any skill with: /podcast-asr, /podcast-transcribe, etc."
echo ""
echo "Next steps:"
echo "  1. Edit podcast-shared/config.md with your show name and host name"
echo "  2. Install dependencies: ffmpeg, python3, pip install openai-whisper edge-tts"
