| X" on the arcade set: Zangief in the match (he plays in Dan's slot, char 10,
| with a bit per player).
|
| - Animations: his state table is the blob tools/arcade_zangief.py writes at
|   ZBLOB (word offsets from ZBLOB; 0 = keep Dan's state). The two animation
|   setters (0x14390, 0x143B2) take it for a fighter object with the bit.
| - Frames: type 12, a new sprite frame type: as type 2, but the position list
|   is a long pointer instead of an offset into the table at 0x2DB1C (the hook
|   is the frame type dispatcher, 0x14BD6). Tiles: codes 0x8000- (graphics
|   0xC00000-, the new ROMs of the set).
| - Palette: one 15-colour palette at ZBLOB + 0x80, written every frame while
|   his animation runs over the sprite palette his frames use (12, or 12 plus
|   the object's +0x0D when +0x0C is negative: match P2, select screen).

.set ZBLOB,      0x90000
.set ZPAL,       ZBLOB + 0x80
.set ZEND,       ZBLOB + 0x10000
.set XP_ZBITS,   0xFF3010           | bit 0: P1 is Zangief, bit 1: P2
.set FIGHTER1,   0xFF8B00
.set FIGHTER2,   0xFF8C00
.set PAL_P1,     0x90C000 + 12 * 32
.set PAL_P2,     0x90C000 + 16 * 32
.set ZNAME,      0x9F000            | HUD name lists (side 0, side 0x80 later), tools/cps2label.py
.set PLAYER1,    0xFF8300
.set PLAYER2,    0xFF8700

| !!! INSERT AT: 14396
| !!! LENGTH: 0x8
jsr    xp_zanim

| !!! INSERT AT: 143B8
| !!! LENGTH: 0x8
jsr    xp_zanim

| !!! INSERT AT: 14BD6
| !!! LENGTH: 0xA
jmp    xp_ftype

| match HUD name (0x16C78: a0 = list of the character's name, fp = player)
| !!! INSERT AT: 16C78
| !!! LENGTH: 0x8
jsr    xp_zname

| !!! INSERT AT: 0F0800
| !!! LENGTH: 0x400
| d1 = character, d0 = state, fp = object -> a0 = state table (d1 = char * 4)
xp_zanim:
add.w  %d1, %d1
add.w  %d1, %d1
lea    xp_animbase, %a0             | the game's table at 0x143F6 is read
movea.l (%a0, %d1.w), %a0           | pc-relative (decrypted): a copy here
cmpi.w #40, %d1                     | Dan's slot
bne.b  za_out
bsr.b  xp_zmine
beq.b  za_out
move.l %a1, -(%sp)
lea    ZBLOB, %a1
move.w %d0, %d1
add.w  %d1, %d1
tst.w  (%a1, %d1.w)                 | his own animation for this state?
beq.b  za_dan
movea.l %a1, %a0
za_dan:
move.l (%sp)+, %a1
za_out:
rts

| Z set if fp is not a fighter object of a player who is Zangief
xp_zmine:
movem.l %d0, -(%sp)
moveq  #1, %d0
cmpa.l #FIGHTER1, %fp
beq.b  zm_bit
moveq  #2, %d0
cmpa.l #FIGHTER2, %fp
beq.b  zm_bit
moveq  #0, %d0
zm_bit:
and.b  XP_ZBITS, %d0
movem.l (%sp)+, %d0                 | (movem does not touch the flags)
rts

xp_zname:
lea    0(%a2, %d0.w), %a0
movea.l 4(%a0), %a0
cmpi.b #10, 0x82(%fp)
bne.b  zn_out
move.l %d0, -(%sp)
moveq  #1, %d0
cmpa.l #PLAYER1, %fp
beq.b  zn_bit
moveq  #2, %d0
cmpa.l #PLAYER2, %fp
bne.b  zn_no
zn_bit:
and.b  XP_ZBITS, %d0
beq.b  zn_no
lea    ZNAME, %a0
tst.b  0x81(%fp)                    | side
beq.b  zn_no
lea    ZNAME + 0x80, %a0
zn_no:
move.l (%sp)+, %d0
zn_out:
rts

| frame type dispatcher: d0 = type (word at a0, a0 moves past it)
xp_ftype:
move.w (%a0)+, %d0
cmpi.w #12, %d0
beq.b  xp_type12
add.w  %d0, %d0                     | type 0..10 even: long index
lea    xp_ftypes, %a1
movea.l (%a1, %d0.w), %a1
jmp    (%a1)

| type 12: word sprites, word count-1, long position list, count longs
| (code << 16 | attr); the body is the game's type 2 (0x14C64)
xp_type12:
move.w (%a0)+, %d5
cmp.w  %d5, %d7
bcs.w  t12_out
sub.w  %d5, %d7
move.w (%a0)+, %d5
movea.l (%a0)+, %a1
t12_loop:
move.w (%a1)+, %d0
move.w (%a1)+, %d1
move.b 11(%fp), %d3
lsl.b  #5, %d3
andi.b #0x60, %d3
swap   %d4
add.w  %d4, %d1
btst   #5, %d3
beq.b  t12_nf
move.b 2(%a0), %d2
andi.w #0xF, %d2
addq.w #1, %d2
lsl.w  #4, %d2
neg.w  %d0
sub.w  %d2, %d0
t12_nf:
swap   %d4
add.w  %d4, %d0
andi.w #0x3FF, %d0
andi.w #0x3FF, %d1
or.w   48(%fp), %d0
ori.w  #0x2000, %d1
move.l (%a0)+, %d2
eor.b  %d3, %d2
move.b 13(%fp), %d3
tst.b  12(%fp)
beq.b  t12_np
bpl.b  t12_pp
add.b  %d2, %d3
t12_pp:
andi.w #0xFF60, %d2
andi.w #0x1F, %d3
or.w   %d3, %d2
t12_np:
move.w %d2, %d3
swap   %d2
movem.w %d0-%d3, (%a2)
lea    8(%a2), %a2
dbf    %d5, t12_loop
t12_out:
rts

| every frame (from the sprite list hook): his palette over Dan's while his
| animation runs
xp_zpal:
movem.l %d0-%d1/%a0-%a1, -(%sp)
lea    FIGHTER1, %a0
bsr.b  zp_one
lea    FIGHTER2, %a0
bsr.b  zp_one
movem.l (%sp)+, %d0-%d1/%a0-%a1
rts
zp_one:
move.l 0x1C(%a0), %d0               | current animation entry
cmpi.l #ZBLOB, %d0
bcs.b  zp_out
cmpi.l #ZEND, %d0
bcc.b  zp_out
moveq  #0x0C, %d1                   | his frames' palette, as the emitter
tst.b  0x0C(%a0)                    | offsets it (match P2, select screen)
bpl.b  zp_slot
add.b  0x0D(%a0), %d1
andi.w #0x1F, %d1
zp_slot:
lsl.w  #5, %d1
lea    0x90C000, %a1
adda.w %d1, %a1
lea    ZPAL, %a0
moveq  #7, %d0
zp_copy:
move.l (%a0)+, (%a1)+
dbf    %d0, zp_copy
zp_out:
rts

| copies of two tables the game reads pc-relative (so through the decryption):
| the characters' state tables (0x143F6) and the frame type handlers (0x14BE2)
xp_animbase:
.long 0x54CA4, 0x57DDE, 0x5B4AE, 0x5ECB2, 0x617DC, 0x6747A
.long 0x6C290, 0x6E9BC, 0x725B8, 0x77922, 0x7AB6C
xp_ftypes:
.long 0x14BEE, 0x14C64, 0x14CE6, 0x14D60, 0x14DFA, 0x14E92
