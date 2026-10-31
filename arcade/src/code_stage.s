| X" on the arcade set: Versus stage selector.
|
| Vanilla VS HUMAN: the stage is the character of one of the players (the
| routine at 0xBA44, 0xFF8100 = stage * 2). Now P1 chooses it on the select
| screen with START, until he confirms his character; the line between the
| PLAYER SELECT logo and the grid shows the setting:
|   RANDOM (default), NORMAL (vanilla), MORRIGAN .. AKUMA, then RANDOM again.
| RANDOM draws a stage at every match, never the one of the previous match.
| The setting lives until the title screen comes back. VS COM is not touched.
|
| Code in pzf.04 (0x80000-, outside the encrypted range): it goes in as it is.
| RAM: 0xFF3000- is never written by the game (emulator trace of boot,
| attract, menus, select and matches).

.set A5,         0xFF8000
.set XP_STAGE,   0xFF3000           | byte: setting (0 RANDOM, 1 NORMAL, 2.. stage 0..)
.set XP_LAST,    0xFF3001           | byte: last stage RANDOM gave (0xFF none)
.set XP_START,   0xFF3002           | byte: START held last frame
.set XP_TICK,    0xFF3003           | byte: runs every select frame (RANDOM's seed)
.set N_SET,      12                 | RANDOM, NORMAL, 10 stages
.set N_STAGES,   10
.set XP_SHOW,    0xFF3004           | byte: frames the line stays on (set by the select hook)
.set LINE_X,     152 + 64           | sprite coordinates of the first character
.set LINE_Y,     92 + 16
.set FONT,       0x5880             | sprite font (8 pixels a character): tile FONT + ascii
.set LINE_PAL,   9                  | as the game's sprite text ("1CREDIT")

| =============================================================================
| HOOKS
| =============================================================================
| select screen, each player still choosing, each frame (0x784A: d2 = ~prev
| buttons; the next instruction ands it with the buttons held)
| !!! INSERT AT: 0784A
| !!! LENGTH: 0x6
jsr    xp_selkey

| title screen (KScl's title line routine at 0x3F100, whose first two
| instructions load the string and the screen position): back to RANDOM
| !!! INSERT AT: 3F100
| !!! LENGTH: 0xA
jsr    xp_title

| sprite list builder (0x149BE: the two instructions before the end mark)
| !!! INSERT AT: 149BE
| !!! LENGTH: 0xA
jsr    xp_sprites

| stage of the match (0xBAA2: d1 = character of the player at a1)
| !!! INSERT AT: 0BAA2
| !!! LENGTH: 0x6
jsr    xp_stage

| =============================================================================
| CODE (pzf.04 free space)
| =============================================================================
| !!! INSERT AT: 0F0000
| !!! LENGTH: 0x400
| fp = select object of the player (P1 0xFF8B00); every register but d2 kept
xp_selkey:
movem.l %d0-%d7/%a0-%a5, -(%sp)
tst.b  A5 + 0xE0                    | VS HUMAN (0 in VS COM, also when a challenger comes)
beq.b  sk_out
move.b #2, XP_SHOW                  | the line stays while anybody chooses
cmpa.l #0xFF8B00, %fp               | P1 only changes it
bne.b  sk_out
addq.b #1, XP_TICK
cmpi.b #N_SET, XP_STAGE             | RAM never set (real hardware)
bcs.b  sk_ok
clr.b  XP_STAGE
sk_ok:
move.w 0x9A(%fp), %d0               | START (bit 15) pressed now, not last frame
lsr.w  #8, %d0
andi.b #0x80, %d0
move.b XP_START, %d1
move.b %d0, XP_START
not.b  %d1
and.b  %d1, %d0
beq.b  sk_out
move.b XP_STAGE, %d0
addq.b #1, %d0
cmpi.b #N_SET, %d0
bcs.b  sk_set
moveq  #0, %d0
sk_set:
move.b %d0, XP_STAGE
moveq  #0x17, %d0                   | cursor sound (as the grid's)
jsr    0x14390
sk_out:
movem.l (%sp)+, %d0-%d7/%a0-%a5
move.w 0x9C(%fp), %d2               | the two instructions the hook replaced
not.w  %d2
rts

| sprite list: a2 = next entry, d7 = entries left; then what the hook
| replaced: the count of used entries, the end mark
xp_sprites:
jsr    xp_zpal                      | code_zangief.s
tst.b  XP_SHOW
beq.b  sp_end
subq.b #1, XP_SHOW
cmpi.w #10, %d7
bcs.b  sp_end
moveq  #0, %d0
move.b XP_STAGE, %d0
cmpi.b #N_SET, %d0
bcs.b  sp_ok
moveq  #0, %d0
sp_ok:
mulu.w #10, %d0
lea    xp_names, %a0
adda.w %d0, %a0
move.w #0xC000 + LINE_X, %d1        | x (+ priority, as the game's text)
moveq  #9, %d2
sp_loop:
moveq  #0, %d0
move.b (%a0)+, %d0
cmpi.b #0x20, %d0
beq.b  sp_next                      | spaces cost nothing
move.w %d1, (%a2)+
move.w #0x2000 + LINE_Y, (%a2)+     | y (+ tile bank 1)
addi.w #FONT, %d0
move.w %d0, (%a2)+
move.w #LINE_PAL, (%a2)+
subq.w #1, %d7
sp_next:
addq.w #8, %d1
dbf    %d2, sp_loop
sp_end:
sub.w  %d7, 0xFF8000 + 0x11A
move.l #0x8000, (%a2)+
rts

xp_title:
clr.b  XP_STAGE
move.b #0xFF, XP_LAST
lea    0x3F900, %a0                 | 'X" BALANCE PATCH BY ZANAC'
lea    0x900670, %a1                | column 12 (25 characters, centred)
rts

| d1 = stage (a1 = the player whose character gives it in vanilla)
xp_stage:
moveq  #0, %d1
move.b 0x82(%a1), %d1
cmpi.b #3, A5 + 0xAC                | two players
bne.b  st_out
tst.b  A5 + 0xE0                    | VS HUMAN, not an arcade challenge
beq.b  st_out
move.l %d0, -(%sp)
moveq  #0, %d0
move.b XP_STAGE, %d0
cmpi.b #N_SET, %d0
bcc.b  st_random                    | never set: RANDOM
subq.b #1, %d0
beq.b  st_done                      | NORMAL
bcs.b  st_random
subq.b #1, %d0
move.b %d0, %d1                     | a fixed stage
bra.b  st_done
st_random:
moveq  #0, %d0
move.b XP_TICK, %d0
divu.w #N_STAGES, %d0
swap   %d0                          | remainder
cmp.b  XP_LAST, %d0
bne.b  st_new
addq.b #1, %d0
cmpi.b #N_STAGES, %d0
bcs.b  st_new
moveq  #0, %d0
st_new:
move.b %d0, XP_LAST
move.b %d0, %d1
st_done:
move.l (%sp)+, %d0
st_out:
rts

| setting names, 10 characters each
xp_names:
.ascii "< RANDOM >"
.ascii "< NORMAL >"
.ascii "<MORRIGAN>"
.ascii "<CHUN-LI >"
.ascii "<  RYU   >"
.ascii "<  KEN   >"
.ascii "<HSIEN-KO>"
.ascii "<DONOVAN >"
.ascii "<FELICIA >"
.ascii "< SAKURA >"
.ascii "<DEVILOT >"
.ascii "< AKUMA  >"
.even
