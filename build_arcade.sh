#!/bin/sh
# Build Super Puzzle Fighter II Turbo X" for the arcade (CPS2) from your own
# MAME sets.
#
# usage: ./build_arcade.sh <spf2t.zip> <sgemf.zip> <output.zip>
#
# spf2t:  Super Puzzle Fighter II Turbo (Euro 960529), MAME set spf2t
# sgemf:  Super Gem Fighter Mini Mix / Pocket Fighter (USA 970904), MAME set
#         sgemf: Zangief's graphics, quotes and pictures are built from it
# Output: the MAME set spf2enh (name the file spf2enh.zip), for the
#         mame2003-plus core with the spf2enh driver.
# Needs:  python3 with numpy and Pillow, and binutils for m68k
#         (m68k-linux-gnu-as/ld/objcopy/nm; another prefix with M68K_PREFIX).
set -e

if [ $# -lt 3 ]; then
	sed -n '2,15p' "$0"
	exit 1
fi
HERE=$(cd "$(dirname "$0")" && pwd)
P=${M68K_PREFIX:-m68k-linux-gnu-}
for t in as ld objcopy nm; do
	command -v "$P$t" >/dev/null 2>&1 || { echo "missing $P$t (binutils for m68k)"; exit 1; }
done
mkdir -p "$(dirname "$3")"
python3 "$HERE/tools/arcade.py" "$1" "$2" "$3"
echo "done: $3"
