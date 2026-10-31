| X" on the arcade set: Zangief in Arcade (VS COM).
|
| The opponents: when Arcade starts, 0xBAB2 copies a 16-byte order (0xBC78 +
| 16 * random row) to 0xFF0CA6: characters 0-7 in some order, then Dan
| (0x0A); Devilot may take place 6 and Akuma place 8. Each STAGE screen
| (0x7F50) takes the opponent of the stage (0xFF8112) from it and writes it
| as the CPU's character (0x7FB6); 0xBA80 does the same for the first one not
| beaten yet (bits in 0xFF8110) when a match is set up from elsewhere.
|
| - His order (as on the PSX): when the human player is Zangief, Felicia (6),
|   his Pocket Fighter rival, is moved to place 7: the 8th opponent, before
|   Dan and the bosses.
| - CPU challenger: in another character's run, Zangief takes Dan's place one
|   time in two (the CPU's Zangief bit); otherwise the CPU's bit is cleared.

.set A5,         0xFF8000
.set XP_ZBITS,   0xFF3010
.set ORDER,      0xFF0CA6           | a5 - 0x735A
.set FELICIA,    6
.set PLAYER1,    0xFF8300
.set PLAYER2,    0xFF8700
.set ZBLOB,      0x90000

| STAGE screen: stage (0xFF8112) < 8 ?
| !!! INSERT AT: 07F50
| !!! LENGTH: 0x8
jsr    xp_zstage

| STAGE screen: the opponent (d0) to the CPU's select object (fp) and struct
| (a4); a0 = the human's struct
| !!! INSERT AT: 07FB6
| !!! LENGTH: 0x8
jsr    xp_zcpu2

| after the order is copied (a0 = the human player's struct): the rest of
| 0xBAB2 up to the Akuma test is redone in xp_zorder
| !!! INSERT AT: 0BADA
| !!! LENGTH: 0x16
jmp    xp_zorder

| the CPU's character (d0 = place, d1 = character, a0 / a1 = human / CPU)
| !!! INSERT AT: 0BA9A
| !!! LENGTH: 0x8
jsr    xp_zcpu

| CONTINUE screen (and others): a fighter-sized figure whose animation is
| taken from the character's state table directly (0x243D8: d0 = state, fp+3
| = character, a4 = player struct; 0x243DC-0x243E7 look the base up)
| !!! INSERT AT: 243DC
| !!! LENGTH: 0xC
jsr    xp_zcont

| Akuma's ambush (when the CPU is Dan): an intruder object (0x27C54) runs in,
| taunts and is beaten; its animations come from Dan's table 0x7AB6C at four
| places. When the CPU fighter it stands for (+0x32) is Zangief: his.
| !!! INSERT AT: 27CBE
| !!! LENGTH: 0x6
jsr    xp_zintr

| !!! INSERT AT: 27D16
| !!! LENGTH: 0x6
jsr    xp_zintr

| !!! INSERT AT: 27D40
| !!! LENGTH: 0x6
jsr    xp_zintr

| !!! INSERT AT: 27D5A
| !!! LENGTH: 0x6
jsr    xp_zintr

| !!! INSERT AT: 0F1200
| !!! LENGTH: 0x200
xp_zorder:
jsr    xp_zis_ok                    | code_zangief.s (Z: a0 is not Zangief)
beq.b  zr_devil
btst   #FELICIA, A5 + 0x111         | already beaten (0xFF8110 bit 6)
bne.b  zr_devil
lea    ORDER, %a2
moveq  #7, %d0
zr_find:
cmpi.b #FELICIA, 0(%a2, %d0.w)
beq.b  zr_swap
dbf    %d0, zr_find
bra.b  zr_devil
zr_swap:
move.b 7(%a2), 0(%a2, %d0.w)
move.b #FELICIA, 7(%a2)
zr_devil:                           | the game's (0xBADA-0xBAEF): Devilot in place 6
tst.b  A5 + 0x139
beq.b  zr_out
move.w A5 + 0x110, %d0
btst   #8, %d0
bne.b  zr_out
move.b #8, ORDER + 6
zr_out:
jmp    0xBAF0

| Felicia to place 7 when the human player is Zangief and she has not come yet
xp_zstage:
movem.l %d0-%d1/%a0/%a2, -(%sp)
lea    PLAYER1, %a0
tst.b  0x9E(%a0)                    | +0x9E set: played by the CPU
beq.b  zs_hum
lea    PLAYER2, %a0
zs_hum:
jsr    xp_zis_ok
beq.b  zs_out
lea    ORDER, %a2
move.w A5 + 0x112, %d1
moveq  #7, %d0
zs_find:
cmp.w  %d1, %d0                     | only the places still to come
bcs.b  zs_out
cmpi.b #FELICIA, 0(%a2, %d0.w)
beq.b  zs_swap
dbf    %d0, zs_find
bra.b  zs_out
zs_swap:
move.b 7(%a2), 0(%a2, %d0.w)
move.b #FELICIA, 7(%a2)
zs_out:
movem.l (%sp)+, %d0-%d1/%a0/%a2
move.w A5 + 0x112, %d1              | the two instructions replaced
cmpi.w #8, %d1                      | (the flags go back with the rts)
rts

xp_zcont:
moveq  #0, %d1
move.b 3(%fp), %d1
lsl.w  #2, %d1
lea    xp_animbase, %a0             | code_zangief.s (the copy of 0x243FC's table)
movea.l 0(%a0, %d1.w), %a0
cmpi.b #10, 3(%fp)
bne.b  zt_out
movem.l %d0-%d1/%a0-%a1, -(%sp)
move.l %a4, %d1
andi.l #0xFFFFFF, %d1
movea.l %d1, %a0
jsr    xp_zis_ok                    | Z: not Zangief
beq.b  zt_dan
lea    ZBLOB, %a1
andi.w #0xFF, %d0
add.w  %d0, %d0
tst.w  0(%a1, %d0.w)
beq.b  zt_dan
move.l %a1, 8(%sp)                  | the a0 to give back
moveq  #0x0C, %d1                   | his palette over the slot his frames use
tst.b  0x0C(%fp)
bpl.b  zt_slot
add.b  0x0D(%fp), %d1
andi.w #0x1F, %d1
zt_slot:
lsl.w  #5, %d1
lea    0x90C000, %a0
adda.w %d1, %a0
lea    ZBLOB + 0x80, %a1
moveq  #7, %d1
zt_copy:
move.l (%a1)+, (%a0)+
dbf    %d1, zt_copy
zt_dan:
movem.l (%sp)+, %d0-%d1/%a0-%a1
zt_out:
rts

| d0 = state, fp = the intruder -> a0 = the state table
xp_zintr:
lea    0x7AB6C, %a0
movem.l %d0-%d1/%a1, -(%sp)
moveq  #0, %d1
move.w 0x32(%fp), %d1
ori.l  #0xFF0000, %d1
cmpi.l #0xFF8B00, %d1
beq.b  zi_p1
cmpi.l #0xFF8C00, %d1
bne.b  zi_out
moveq  #1, %d1
bra.b  zi_bit
zi_p1:
moveq  #0, %d1
zi_bit:
btst   %d1, XP_ZBITS
beq.b  zi_out
lea    ZBLOB + 0xA0, %a1            | his intruder table (tools/arcade_zangief.py)
andi.w #0xFF, %d0
add.w  %d0, %d0
tst.w  0(%a1, %d0.w)
beq.b  zi_out
movea.l %a1, %a0
moveq  #0x0C, %d1                   | his palette over the slot his frames use
tst.b  0x0C(%fp)
bpl.b  zi_slot
add.b  0x0D(%fp), %d1
andi.w #0x1F, %d1
zi_slot:
lsl.w  #5, %d1
lea    0x90C000, %a1
adda.w %d1, %a1
move.l %a0, -(%sp)
lea    ZBLOB + 0x80, %a0
moveq  #7, %d1
zi_copy:
move.l (%a0)+, (%a1)+
dbf    %d1, zi_copy
movea.l (%sp)+, %a0
zi_out:
movem.l (%sp)+, %d0-%d1/%a1
rts

xp_zcpu2:
move.b %d0, 0x82(%fp)               | the two instructions replaced
move.b %d0, 0x82(%a4)
movem.l %d0-%d2/%a0-%a1, -(%sp)
move.b %d0, %d1
movea.l %a4, %a1
bra.b  zc_go

xp_zcpu:
move.w %d0, A5 + 0x112              | the two instructions replaced
move.b %d1, 0x82(%a1)
movem.l %d0-%d2/%a0-%a1, -(%sp)
zc_go:
move.l %a1, %d2                     | the CPU's bit (a1 may be sign-extended)
andi.l #0xFFFFFF, %d2
cmpi.l #PLAYER1, %d2
seq    %d2                          | P1: 0xFF + 1 = 0, P2: 1
addq.b #1, %d2
bclr   %d2, XP_ZBITS
cmpi.b #10, %d1                     | Dan's place
bne.b  zc_out
jsr    xp_zis_ok                    | the human (a0) is Zangief: Dan stays
bne.b  zc_out
jsr    0x2DB02                      | random
btst   #0, %d0
beq.b  zc_out
bset   %d2, XP_ZBITS
zc_out:
movem.l (%sp)+, %d0-%d2/%a0-%a1
rts
