#!/bin/sh
# Apply the X' patch to an original Super Puzzle Fighter II Turbo (NTSC-U,
# SLUS-00418) image. No assembler needed, only python3.
#
# usage: ./patch.sh <original.bin|original.pbp> <output.bin|output.pbp>
set -e
if [ $# -ne 2 ]; then
	sed -n '2,6p' "$0"
	exit 1
fi
HERE=$(cd "$(dirname "$0")" && pwd)
python3 "$HERE/tools/applypatch.py" "$HERE/xprime-patch.json" "$1" "$2"
