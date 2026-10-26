#!/bin/sh
# Build Super Puzzle Fighter II Turbo X' (PSX) from an original NTSC-U image.
#
# usage: ./build.sh <input.bin|input.pbp> <output.bin|output.pbp> [armips]
#
# Input:  SLUS-00418, either a raw 2352-byte BIN (single data track, as in the
#         usual BIN/CUE dumps) or a single-disc PBP.
# Output: same format as the input. For BIN output, reuse the original .cue
#         (renaming the FILE line if the file name changes).
# Needs:  python3, armips (pass its path as 3rd argument or have it in PATH).
set -e

if [ $# -lt 2 ]; then
	sed -n '2,11p' "$0"
	exit 1
fi

IN=$1
OUT=$2
ARMIPS=${3:-armips}
HERE=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 "$HERE/tools/extract.py" "$IN" /SLUS_004.18 "$TMP/SLUS_004.18"
python3 "$HERE/tools/checkexe.py" "$TMP/SLUS_004.18"
"$ARMIPS" "$HERE/src/xprime.asm" -root "$HERE" \
	-strequ IN "$TMP/SLUS_004.18" -strequ OUT "$TMP/SLUS_004.18.xp"
# Counter Gem previews on the character select are pre-drawn art: redraw the
# characters whose drop pattern changes, from the patched EXE's table
for EMI in FIRST FIRSTE; do
	python3 "$HERE/tools/extract.py" "$IN" "/DATA/$EMI.EMI" "$TMP/$EMI.EMI"
	python3 "$HERE/tools/previews.py" "$TMP/SLUS_004.18.xp" "$TMP/$EMI.EMI" "$TMP/$EMI.EMI.pv" --chars 0,2,4,6,7,10
	# select-screen name labels for Mei-Ling and Anita
	python3 "$HERE/tools/labels.py" "$TMP/$EMI.EMI.pv" "$TMP/$EMI.EMI.xp"
done
python3 "$HERE/tools/discpatch.py" "$IN" "$OUT" \
	"/SLUS_004.18=$TMP/SLUS_004.18.xp" \
	"/DATA/FIRST.EMI=$TMP/FIRST.EMI.xp" \
	"/DATA/FIRSTE.EMI=$TMP/FIRSTE.EMI.xp"
echo "done: $OUT"
