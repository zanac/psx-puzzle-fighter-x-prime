#!/bin/sh
# Build Super Puzzle Fighter II Turbo X' (PSX) from an original NTSC-U image.
#
# usage: ./build.sh <input.bin|.cue|.pbp> <output> [armips]
#
# Input:  SLUS-00418 as a raw 2352-byte BIN, a CUE (one or more BIN files)
#         or a single-disc PBP.
# Output: <output>.bin + <output>.cue + <output>.pbp, whatever the input.
# Needs:  python3, armips (pass its path as 3rd argument or have it in PATH).
# Zangief: XP_PF=<Pocket Fighter NTSC-U image (SLUS-00653), .cue/.bin/.pbp>
#         builds his graphics and animations from your own Pocket Fighter disc
#         (tools/zangief.py). Without it he keeps Dan's look in the match.
# Extra:  XP_NEWFILES="NAME=FILE ..." adds files to /DATA (new file ids after
#         Zangief's, in that order); the CD-DA tracks move after them.
set -e

if [ $# -lt 2 ]; then
	sed -n '2,13p' "$0"
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
NEWFILES=${XP_NEWFILES:-}
ZG_HAVE=0
SELREPL=""
if [ -n "${XP_PF:-}" ]; then
	# Zangief's in-match file, from Pocket Fighter (new file ids 0x56, 0x57)
	python3 "$HERE/tools/extract.py" "$XP_PF" /PLAYER/ZANGIEF.PAC "$TMP/ZANGIEF.PAC"
	python3 "$HERE/tools/extract.py" "$XP_PF" /MDL/PL09A.MDL "$TMP/PL09A.MDL"
	python3 "$HERE/tools/extract.py" "$IN" /DATA/FIRST.EMI "$TMP/FIRST.EMI"
	python3 "$HERE/tools/extract.py" "$IN" /DATA/PL9A_OBJ.EMI "$TMP/PL9A_OBJ.EMI"
	python3 "$HERE/tools/extract.py" "$XP_PF" /STAGE/SELECT.PAC "$TMP/PF_SELECT.PAC"
	python3 "$HERE/tools/zangief.py" "$TMP/ZANGIEF.PAC" "$TMP/PL09A.MDL" \
		"$TMP/FIRST.EMI" "$TMP/PL9A_OBJ.EMI" "$TMP/SLUS_004.18" "$TMP/PL0B_OBJ.EMI" \
		--select "$TMP/PF_SELECT.PAC"
	# his voices (second new file: id 0x57)
	python3 "$HERE/tools/extract.py" "$XP_PF" /SE/SE0AA.PAC "$TMP/SE0AA.PAC"
	python3 "$HERE/tools/extract.py" "$IN" /DATA/SE_PL0A.EMI "$TMP/SE_PL0A.EMI"
	python3 "$HERE/tools/zangief.py" voices "$TMP/SE0AA.PAC" "$TMP/SE_PL0A.EMI" "$TMP/SE_PL0B.EMI"
	# his stage (Pocket Fighter's castle, on Ken's stage file) and music
	# (new file ids 0x58, 0x59)
	python3 "$HERE/tools/extract.py" "$XP_PF" /STAGE/ST06.PAC "$TMP/ST06.PAC"
	python3 "$HERE/tools/extract.py" "$IN" /DATA/STAGE03.EMI "$TMP/STAGE03.EMI"
	python3 "$HERE/tools/pf_stage.py" "$TMP/ST06.PAC" "$TMP/STAGE03.EMI" "$TMP/ZG_STAGE.EMI"
	python3 "$HERE/tools/pf_stage.py" music "$XP_PF" "$TMP/ZG_MUSIC.XA"
	NEWFILES="PL0B_OBJ.EMI=$TMP/PL0B_OBJ.EMI SE_PL0B.EMI=$TMP/SE_PL0B.EMI ZG_STAGE.EMI=$TMP/ZG_STAGE.EMI ZG_MUSIC.XA=$TMP/ZG_MUSIC.XA $NEWFILES"
	# his name call on the select screen (SELECT.EMI's sound bank)
	python3 "$HERE/tools/extract.py" "$XP_PF" /SE/SE0D.PAC "$TMP/SE0D.PAC"
	python3 "$HERE/tools/extract.py" "$IN" /DATA/SELECT.EMI "$TMP/SELECT.EMI"
	python3 "$HERE/tools/zangief.py" name "$TMP/SELECT.EMI" "$TMP/SE0D.PAC" "$TMP/SELECT.EMI.xp"
	SELREPL="/DATA/SELECT.EMI=$TMP/SELECT.EMI.xp"
	ZG_HAVE=1
fi
# file table: original files, moved CD-DA tracks, new files (src/files.asm)
python3 "$HERE/tools/discexpand.py" table "$IN" "$TMP/SLUS_004.18" "$TMP/files.bin" $NEWFILES
"$ARMIPS" "$HERE/src/xprime.asm" -root "$HERE" \
	-strequ IN "$TMP/SLUS_004.18" -strequ OUT "$TMP/SLUS_004.18.xp" \
	-strequ XP_TABLE "$TMP/files.bin" -equ ZG_HAVE $ZG_HAVE
# Counter Gem previews on the character select are pre-drawn art: redraw the
# characters whose drop pattern changes, from the patched EXE's table
for EMI in FIRST FIRSTE; do
	python3 "$HERE/tools/extract.py" "$IN" "/DATA/$EMI.EMI" "$TMP/$EMI.EMI"
	python3 "$HERE/tools/previews.py" "$TMP/SLUS_004.18.xp" "$TMP/$EMI.EMI" "$TMP/$EMI.EMI.pv" --chars 0,2,4,6,7,10,11
	# select-screen name labels for Mei-Ling and Anita
	python3 "$HERE/tools/labels.py" "$TMP/$EMI.EMI.pv" "$TMP/$EMI.EMI.xp"
done
ADDS=""
for f in $NEWFILES; do ADDS="$ADDS +$f"; done
python3 "$HERE/tools/makedisc.py" "$IN" "$OUT" \
	"/SLUS_004.18=$TMP/SLUS_004.18.xp" \
	"/DATA/FIRST.EMI=$TMP/FIRST.EMI.xp" \
	"/DATA/FIRSTE.EMI=$TMP/FIRSTE.EMI.xp" $SELREPL $ADDS
echo "done: $OUT"
