| X" on the arcade set: Zangief and Dan on their own icons, in a new row above
| Chun-Li and Sakura (as on the PSX). The PLAYER SELECT logo moves up two rows
| (scroll2 row 1 instead of 3) to make room; the icons are scroll2 tiles from
| tools/cps2icons.py (codes in the new graphics), palettes in scroll2 8 and 9.
| Navigation (KScl's tables): row 0 holds Zangief (column 1) and Dan (column 2),
| Dan leaves the secret row. Both are character 10; the cursor position tells
| Zangief (0xFF3010 bits, set while the player chooses).

.set ZICONS,     0x9F100            | 2 palettes (16 words each), then 9 + 9 tile codes
.set XP_ZBITS,   0xFF3010
.set S2,         0x904000
.set S2PAL,      0x90C800           | scroll2 palettes
.set ICON_PAL0,  8
.set CUR1,       0xFF0C82           | +1 position (P1); P2 at +4
.set POS_ZG,     0x01               | KScl navigation positions (row 0)

| the three select screen set-ups (Arcade, Versus, challenge): logo + icons
| !!! INSERT AT: 0705A
| !!! LENGTH: 0xE
jsr    xp_logo

| !!! INSERT AT: 07220
| !!! LENGTH: 0xE
jsr    xp_logo

| !!! INSERT AT: 073A2
| !!! LENGTH: 0xE
jsr    xp_logo

| !!! INSERT AT: 0F0C00
| !!! LENGTH: 0x200
xp_logo:
lea    S2 + 1 * 4 + 8 * 0x40, %a1   | column 8, row 1 (was row 3)
moveq  #0, %d0
jsr    0xBB8C
clr.b  XP_ZBITS                     | the choosing players set theirs
| fall through: icons and their palettes

| scroll2 cell (column c, row r) = S2 + 4 * ((r & 15) + 16 * c + 64 * (r & 0x30))
xp_icons:
movem.l %d0-%d3/%a0-%a2, -(%sp)
lea    ZICONS + 64, %a0             | tile codes
lea    S2 + 4 * (5 + 16 * 9), %a1   | Zangief: columns 9-11, rows 5-7
moveq  #ICON_PAL0, %d2
bsr.b  ic_one
lea    S2 + 4 * (5 + 16 * 12), %a1  | Dan: columns 12-14
moveq  #ICON_PAL0 + 1, %d2
bsr.b  ic_one
lea    ZICONS, %a0                  | their palettes
lea    S2PAL + ICON_PAL0 * 32, %a1
moveq  #15, %d0
ic_pal:
move.l (%a0)+, (%a1)+
dbf    %d0, ic_pal
movem.l (%sp)+, %d0-%d3/%a0-%a2
rts
ic_one:                             | 3 rows of 3 tiles, row-major in the list
moveq  #2, %d0
ic_row:
movea.l %a1, %a2
moveq  #2, %d1
ic_col:
move.w (%a0)+, (%a2)
move.w %d2, 2(%a2)
lea    0x40(%a2), %a2               | next column
dbf    %d1, ic_col
addq.l #4, %a1                      | next row
dbf    %d0, ic_row
rts

| select hook (every frame, each player choosing): Zangief bit from the
| cursor position; the palettes again (the screen's palette upload comes later)
xp_selz:
movem.l %d0-%d1/%a0, -(%sp)
moveq  #0, %d1                      | player index
cmpa.l #0xFF8B00, %fp
beq.b  sz_p
moveq  #1, %d1
cmpa.l #0xFF8C00, %fp
bne.b  sz_out
sz_p:
lea    CUR1, %a0
move.w %d1, %d0
add.w  %d0, %d0
add.w  %d0, %d0
cmpi.b #POS_ZG, 1(%a0, %d0.w)
bne.b  sz_clr
bset   %d1, XP_ZBITS
bra.b  sz_pal
sz_clr:
bclr   %d1, XP_ZBITS
sz_pal:
bsr.w  xp_icons
sz_out:
movem.l (%sp)+, %d0-%d1/%a0
rts
