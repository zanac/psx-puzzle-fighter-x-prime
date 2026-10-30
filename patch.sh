#!/bin/sh
# Build Super Puzzle Fighter II Turbo X" (PSX) without an assembler: the
# same as ./build.sh without its armips argument (the executable comes from
# xprime-patch.json). Only python3 is needed.
#
# usage: ./patch.sh <SPF2T image> <Pocket Fighter image> <output>
# SPF2T: NTSC-U SLUS-00418; Pocket Fighter: NTSC-U SLUS-00653 (BIN, CUE or PBP)
# Writes <output>.bin, <output>.cue and <output>.pbp, whatever the input.
set -e
if [ $# -ne 3 ]; then
	sed -n '2,8p' "$0"
	exit 1
fi
HERE=$(cd "$(dirname "$0")" && pwd)
exec "$HERE/build.sh" "$1" "$2" "$3"
