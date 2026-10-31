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
.set ZPORT,      0x9F800            | his portrait: pseudo entry, palette (+8), ...
.set XP_PORTOBJ, 0xFF3020           | the portrait objects (P1, P2) last set to his
.set ZSELNAME,   0x9F700            | his name: pseudo entry (dur/flags, frame)
.set ZPREV,      0x9F500            | Zangief's Counter Gem block (header + 70 longs)

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

| cursor marker position (0x261F0: d0 = character from the cursor struct at
| a0; the game's table at 0x26208 has x, y per character 0-7, y counted up)
| !!! INSERT AT: 261F0
| !!! LENGTH: 0x6
jsr    xp_curxy

| the marker is drawn only for characters 0-7 (0x26170): also on the icons
| !!! INSERT AT: 26170
| !!! LENGTH: 0xA
jsr    xp_curdraw

| KScl's cursor movement (0x789E, d3 = directions pressed, a4 = cursor,
| fp = select object), with the Zangief bit set as soon as the cursor moves,
| before the poses and portraits are started
| !!! INSERT AT: 0789E
| !!! LENGTH: 0x56
lea    0x03F800.l, %a0      | offsets by direction
moveq  #0, %d4
move.b (%a0,%d3.w), %d4
beq.b  mv_none
add.b  0x1(%a4), %d4
lea    0x40(%a0), %a0       | navigation table
move.b (%a0,%d4.w), %d0
cmpi.b #0xFF, %d0
beq.b  mv_none
move.b %d4, 0x1(%a4)
move.b %d0, (%a4)
move.b %d0, 0x82(%fp)
jsr    xp_selz              | Zangief bit from the new position
jsr    0x2B572.l
moveq  #0x17, %d0
jsr    0x14390.l
jsr    0x8532.l
mv_none:
rts

| Counter Gem box of the character under the cursor (0x79BE: a0 = the
| character's entry in the 0x84560 table, fp = select object)
| !!! INSERT AT: 079BE
| !!! LENGTH: 0x10
jsr    xp_zprev

| name under the select pose (0x262A0: a0 = 0x7DB20 table, d0 = character
| or 11 + character, a4 = select object): his own name
| !!! INSERT AT: 262A0
| !!! LENGTH: 0xE
jsr    xp_zselname

| select portrait (0x2512C: a0 = cursor struct, d0 = 2 * (char + 35))
| !!! INSERT AT: 2512C
| !!! LENGTH: 0x12
jsr    xp_zport

| same character -> the alternate colours (0x7968 on confirming, 0x7FC6 when a
| challenge sets both): Zangief and Dan are not the same character any more
| !!! INSERT AT: 07968
| !!! LENGTH: 0x8
jsr    xp_samech

| !!! INSERT AT: 07FC6
| !!! LENGTH: 0x8
jsr    xp_samech

| !!! INSERT AT: 0F0C00
| !!! LENGTH: 0x400
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

xp_curxy:
moveq  #0, %d0
move.b (%a0), %d0
cmpi.b #0x01, 1(%a0)                | Zangief's icon: above Chun-Li
bne.b  cx_dan
move.w #0x90, 16(%fp)
bra.b  cx_row0
cx_dan:
cmpi.b #0x02, 1(%a0)                | Dan's: above Sakura
bne.b  cx_out
move.w #0xC0, 16(%fp)
cx_row0:
move.w #0xB0, 20(%fp)
moveq  #8, %d0                      | the game then skips its table
cx_out:
cmpi.b #8, %d0
rts

xp_curdraw:
movea.l 50(%fp), %a0
moveq  #0, %d0
move.b (%a0), %d0
cmpi.b #0x01, 1(%a0)
beq.b  cd_icon
cmpi.b #0x02, 1(%a0)
bne.b  cd_out
cd_icon:
moveq  #0, %d0
cd_out:
cmpi.b #8, %d0
rts

xp_zprev:
moveq  #0, %d0
move.b 0x82(%fp), %d0
lsl.w  #4, %d0
lea    0(%a0, %d0.w), %a0
movea.l 4(%a0), %a0
cmpi.b #10, 0x82(%fp)
bne.b  zv_out
moveq  #0, %d0
cmpa.l #0xFF8B00, %fp
beq.b  zv_bit
moveq  #1, %d0
cmpa.l #0xFF8C00, %fp
bne.b  zv_out
zv_bit:
btst   %d0, XP_ZBITS
beq.b  zv_out
lea    ZPREV, %a0
zv_out:
rts

xp_zselname:
lsl.w  #2, %d0
lea    0(%a0, %d0.w), %a0
cmpi.b #10, 0x82(%a4)
bne.b  sn_set
move.l %a4, %d0                     | a4 comes sign-extended (moveaw): 24 bits
andi.l #0xFFFFFF, %d0
cmpi.l #0xFF8B00, %d0
seq    %d0
andi.b #1, %d0
beq.b  sn_p2
moveq  #0, %d0
bra.b  sn_bit
sn_p2:
move.l %a4, %d0
andi.l #0xFFFFFF, %d0
cmpi.l #0xFF8C00, %d0
bne.b  sn_set
moveq  #1, %d0
sn_bit:
btst   %d0, XP_ZBITS
beq.b  sn_set
lea    ZSELNAME, %a0
sn_set:
move.l %a0, 28(%fp)
move.l (%a0), 24(%fp)
rts

xp_zport:
cmpi.b #POS_ZG, 1(%a0)              | cursor on Zangief's icon
beq.b  zt_his
lea    0x7DAC6, %a0
move.w 0(%a0, %d0.w), %d0
lea    -4(%a0, %d0.w), %a0
move.l %a0, 28(%fp)
rts
zt_his:
lea    ZPORT, %a0
move.l %a0, 28(%fp)
moveq  #0, %d0
move.b 3(%fp), %d0                  | side
add.w  %d0, %d0
add.w  %d0, %d0
lea    XP_PORTOBJ, %a0
move.l %fp, 0(%a0, %d0.w)
rts

| every frame: his portrait's palette over the slot it uses
xp_zportpal:
movem.l %d0-%d1/%a0-%a2, -(%sp)
lea    XP_PORTOBJ, %a2
moveq  #1, %d1
zq_loop:
movea.l (%a2)+, %a0
move.l %a0, %d0
beq.b  zq_next
cmpi.l #ZPORT, 28(%a0)
bne.b  zq_next
moveq  #0, %d0
move.b 13(%a0), %d0
andi.w #31, %d0
lsl.w  #5, %d0
lea    0x90C000, %a1
adda.w %d0, %a1
lea    ZPORT + 8, %a0
moveq  #7, %d0
zq_copy:
move.l (%a0)+, (%a1)+
dbf    %d0, zq_copy
zq_next:
dbf    %d1, zq_loop
movem.l (%sp)+, %d0-%d1/%a0-%a2
rts

| Z set if the objects/structs at fp and a0 have the same character, Zangief
| counting as his own (bit of each one's side: 0xFF83/0xFF8B P1, 0xFF87/0xFF8C P2)
xp_samech:
movem.l %d0-%d2, -(%sp)
move.b 0x82(%fp), %d0
cmp.b  0x82(%a0), %d0
bne.b  sc_out                       | Z clear: different
cmpi.b #10, %d0
bne.b  sc_out                       | Z set: same, not Dan's slot
move.l %fp, %d0
bsr.b  sc_side
move.b %d2, %d1
move.l %a0, %d0
bsr.b  sc_side
cmp.b  %d1, %d2                     | Z set when both or neither are Zangief
sc_out:
movem.l (%sp)+, %d0-%d2             | (movem keeps the flags)
rts
sc_side:                            | d0 = address -> d2 = its Zangief bit (0/1)
andi.l #0xFFFF00, %d0
moveq  #0, %d2
cmpi.l #0xFF8300, %d0
beq.b  sd_p1
cmpi.l #0xFF8B00, %d0
beq.b  sd_p1
moveq  #1, %d2
sd_p1:
btst   %d2, XP_ZBITS
sne    %d2
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
