#!/bin/bash
set -e

SKILLS_DIR="$HOME/.claude/skills"

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

echo "Uninstalling podcast-workflow skills..."
echo ""

for skill in "${SKILLS[@]}"; do
  target="$SKILLS_DIR/$skill"
  if [ -L "$target" ]; then
    rm "$target"
    echo "  REMOVED $skill"
  else
    echo "  SKIP    $skill (not a symlink or doesn't exist)"
  fi
done

echo ""
echo "Done. Skills removed from Claude Code."
