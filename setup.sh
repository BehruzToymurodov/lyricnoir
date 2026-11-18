#!/usr/bin/env bash
# One-command setup for the Lyric Noir studio (Linux / Claude workspace).
set -e
cd "$(dirname "$0")"
PIP="python3 -m pip install -q -r requirements.txt"
$PIP 2>/dev/null || $PIP --break-system-packages
if ! command -v ffmpeg >/dev/null; then
  (sudo apt-get install -y -qq ffmpeg || apt-get install -y -qq ffmpeg) >/dev/null 2>&1 || echo "Install ffmpeg manually"
fi
mkdir -p work dist
python3 -m lyricnoir check
