#!/bin/sh
# Build Super Puzzle Fighter II Turbo X" (PSX) from your own discs.
#
# usage: ./build.sh [--arcade <spf2t.zip> <sgemf.zip>] <SPF2T image>
#                   <Pocket Fighter image> <output> [armips]
#
# SPF2T:  Super Puzzle Fighter II Turbo NTSC-U (SLUS-00418)
# PF:     Pocket Fighter NTSC-U (SLUS-00653): Zangief's graphics, voices,
#         stage, music and ending picture are built from it
# Images: a raw 2352-byte BIN, a CUE (one or more BIN files) or a
#         single-disc PBP, for either disc.
# Output: <output>.bin + <output>.cue + <output>.pbp, whatever the input.
# Needs:  python3. Without armips, the executable comes from
#         xprime-patch.json; with armips (4th argument), it is assembled
#         from src/ (XP_MKPATCH=<file.json> then also writes the patch).
# Extra:  XP_NEWFILES="NAME=FILE ..." adds files to /DATA (new file ids after
#         Zangief's, in that order; needs armips).
# Arcade: --arcade also builds the CPS2 set spf2enh.zip, next to <output>,
#         from your MAME sets spf2t and sgemf (see build_arcade.sh).
#         With --arcade, his stage also gets a remix of its music for the
#         arranged music setting, rendered from sgemf.
set -e

ARC_SPF=""
ARC_PF=""
if [ "${1:-}" = "--arcade" ]; then
	ARC_SPF=$2
	ARC_PF=$3
	shift 3
fi
if [ $# -lt 3 ]; then
	sed -n '2,21p' "$0"
	exit 1
fi

IN=$1
PF=$2
OUT=$3
ARMIPS=${4:-}
HERE=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 "$HERE/tools/extract.py" "$IN" /SLUS_004.18 "$TMP/SLUS_004.18"
python3 "$HERE/tools/checkexe.py" "$TMP/SLUS_004.18"
python3 "$HERE/tools/checkpf.py" "$PF"
NEWFILES=${XP_NEWFILES:-}
# Zangief's in-match file, from Pocket Fighter (new file ids 0x56, 0x57)
python3 "$HERE/tools/extract.py" "$PF" /PLAYER/ZANGIEF.PAC "$TMP/ZANGIEF.PAC"
python3 "$HERE/tools/extract.py" "$PF" /MDL/PL09A.MDL "$TMP/PL09A.MDL"
python3 "$HERE/tools/extract.py" "$IN" /DATA/FIRST.EMI "$TMP/FIRST.EMI"
python3 "$HERE/tools/extract.py" "$IN" /DATA/PL9A_OBJ.EMI "$TMP/PL9A_OBJ.EMI"
python3 "$HERE/tools/extract.py" "$PF" /STAGE/SELECT.PAC "$TMP/PF_SELECT.PAC"
# WINNER screen: his own Pocket Fighter win quotes, set in the font of
# every character's SPF2T quotes
python3 "$HERE/tools/extract.py" "$PF" /MDL/SELMES.MDL "$TMP/SELMES.MDL"
QF=""
for n in 00 01 02 03 04 05 06 07 08; do
	python3 "$HERE/tools/extract.py" "$IN" /DATA/PL${n}_OBJ.EMI "$TMP/PL${n}_OBJ.EMI"
	QF="$QF${QF:+,}$TMP/PL${n}_OBJ.EMI"
done
python3 "$HERE/tools/zangief.py" "$TMP/ZANGIEF.PAC" "$TMP/PL09A.MDL" \
	"$TMP/FIRST.EMI" "$TMP/PL9A_OBJ.EMI" "$TMP/SLUS_004.18" "$TMP/PL0B_OBJ.EMI" \
	--select "$TMP/PF_SELECT.PAC" --quotefont "$QF" --selmes "$TMP/SELMES.MDL"
# his voices (second new file: id 0x57)
python3 "$HERE/tools/extract.py" "$PF" /SE/SE0AA.PAC "$TMP/SE0AA.PAC"
python3 "$HERE/tools/extract.py" "$IN" /DATA/SE_PL0A.EMI "$TMP/SE_PL0A.EMI"
python3 "$HERE/tools/zangief.py" voices "$TMP/SE0AA.PAC" "$TMP/SE_PL0A.EMI" "$TMP/SE_PL0B.EMI"
# his stage (Pocket Fighter's castle, on Ken's stage file) and music
# (new file ids 0x58, 0x59)
python3 "$HERE/tools/extract.py" "$PF" /STAGE/ST06.PAC "$TMP/ST06.PAC"
python3 "$HERE/tools/extract.py" "$IN" /DATA/STAGE03.EMI "$TMP/STAGE03.EMI"
python3 "$HERE/tools/pf_stage.py" "$TMP/ST06.PAC" "$TMP/STAGE03.EMI" "$TMP/ZG_STAGE.EMI"
# with the arranged music on, his stage plays a remix of the castle theme,
# rendered from Pocket Fighter's arcade set (--arcade's sgemf: the PSX disc
# has no notes); without it the original plays both ways
REMIX=""
if [ -n "$ARC_PF" ]; then
	if python3 "$HERE/tools/remix.py" "$ARC_PF" "$TMP/REMIX.wav"; then
		REMIX="$TMP/REMIX.wav"
	else
		echo "remix not rendered: the original music for both settings"
	fi
fi
python3 "$HERE/tools/pf_stage.py" music "$PF" "$TMP/ZG_MUSIC.XA" $REMIX
# his Arcade staff roll figure: the picture of his Pocket Fighter opening
# (new file id 0x5A)
python3 "$HERE/tools/extract.py" "$PF" /STAGE/OPEN09.PAC "$TMP/OPEN09.PAC"
python3 "$HERE/tools/extract.py" "$IN" /DATA/HARD_END.EMI "$TMP/HARD_END.EMI"
python3 "$HERE/tools/zangief.py" ending "$TMP/OPEN09.PAC" "$TMP/HARD_END.EMI" "$TMP/ZG_END.EMI"
NEWFILES="PL0B_OBJ.EMI=$TMP/PL0B_OBJ.EMI SE_PL0B.EMI=$TMP/SE_PL0B.EMI ZG_STAGE.EMI=$TMP/ZG_STAGE.EMI ZG_MUSIC.XA=$TMP/ZG_MUSIC.XA ZG_END.EMI=$TMP/ZG_END.EMI $NEWFILES"
# his name call on the select screen (SELECT.EMI's sound bank)
python3 "$HERE/tools/extract.py" "$PF" /SE/SE0D.PAC "$TMP/SE0D.PAC"
python3 "$HERE/tools/extract.py" "$IN" /DATA/SELECT.EMI "$TMP/SELECT.EMI"
python3 "$HERE/tools/zangief.py" name "$TMP/SELECT.EMI" "$TMP/SE0D.PAC" "$TMP/SELECT.EMI.xp"
# file table: original files, moved CD-DA tracks, new files (src/files.asm)
python3 "$HERE/tools/discexpand.py" table "$IN" "$TMP/SLUS_004.18" "$TMP/files.bin" $NEWFILES
if [ -n "$ARMIPS" ]; then
	"$ARMIPS" "$HERE/src/xprime.asm" -root "$HERE" \
		-strequ IN "$TMP/SLUS_004.18" -strequ OUT "$TMP/SLUS_004.18.xp" \
		-strequ XP_TABLE "$TMP/files.bin"
	if [ -n "${XP_MKPATCH:-}" ]; then
		python3 "$HERE/tools/mkpatch.py" "$TMP/SLUS_004.18" "$TMP/SLUS_004.18.xp" \
			"$TMP/files.bin" "$XP_MKPATCH"
	fi
else
	python3 "$HERE/tools/applypatch.py" "$HERE/xprime-patch.json" \
		"$TMP/SLUS_004.18" "$TMP/files.bin" "$TMP/SLUS_004.18.xp"
fi
# Counter Gem previews on the character select are pre-drawn art: redraw the
# characters whose drop pattern changes, from the patched EXE's table
for EMI in FIRST FIRSTE; do
	python3 "$HERE/tools/extract.py" "$IN" "/DATA/$EMI.EMI" "$TMP/$EMI.EMI"
	python3 "$HERE/tools/previews.py" "$TMP/SLUS_004.18.xp" "$TMP/$EMI.EMI" "$TMP/$EMI.EMI.pv" --chars 0,2,4,6,7,10,11
	# select-screen name labels for Mei-Ling and Anita
	python3 "$HERE/tools/labels.py" "$TMP/$EMI.EMI.pv" "$TMP/$EMI.EMI.lb"
	# Zangief's icon on the select grid (Pocket Fighter's)
	python3 "$HERE/tools/zangief.py" icon "$TMP/PF_SELECT.PAC" "$TMP/$EMI.EMI.lb" "$TMP/$EMI.EMI.xp"
done
ADDS=""
for f in $NEWFILES; do ADDS="$ADDS +$f"; done
python3 "$HERE/tools/makedisc.py" "$IN" "$OUT" \
	"/SLUS_004.18=$TMP/SLUS_004.18.xp" \
	"/DATA/FIRST.EMI=$TMP/FIRST.EMI.xp" \
	"/DATA/FIRSTE.EMI=$TMP/FIRSTE.EMI.xp" \
	"/DATA/SELECT.EMI=$TMP/SELECT.EMI.xp" $ADDS
echo "done: $OUT"
if [ -n "$ARC_SPF" ]; then
	"$HERE/build_arcade.sh" "$ARC_SPF" "$ARC_PF" "$(dirname "$OUT")/spf2enh.zip"
fi
