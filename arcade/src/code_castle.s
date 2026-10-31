| X" on the arcade set: Zangief's stage, Pocket Fighter's castle.
|
| The castle is Dan's stage (0xFF8100 = 20) with other scroll2 blocks, other
| scroll2 palettes, no stage objects and Pocket Fighter's castle music (song
| 24, tools/qsconv.py). The data (blocks 0x89-, palette block CPAL, block list
| CLIST) come from the user's Pocket Fighter set (tools/cps2castle.py).
|
| When: stage 20 and XP_CASTLE (set by xp_stage, code_stage.s: the stage
| selector's ZANGIEF, RANDOM, or NORMAL with the stage's player Zangief), or,
| in a one-player game, the CPU is Zangief (his challenge in Dan's place).

.set A5,         0xFF8000
.set XP_CASTLE,  0xFF3005           | byte: this match's stage 20 is the castle
.set PLAYER1,    0xFF8300
.set PLAYER2,    0xFF8700
.set DAN_STAGE,  20
.set CPAL,       0xB2E00            | palette block (cps2castle.py)
.set CLIST,      0xB3202            | block list; word 0x16 at CLIST - 2
.set CTAB,       CLIST - 22         | word[CTAB + 20] = 22: CTAB + 22 = CLIST

| =============================================================================
| HOOKS
| =============================================================================
| scroll2 of the stage (0x17AAE): the block list table
| !!! INSERT AT: 17ADC
| !!! LENGTH: 0x6
jsr    xp_cs2

| scroll2 palettes of the stage: three loaders (0xA22C0 + stage * 0x200)
| !!! INSERT AT: 20D0C
| !!! LENGTH: 0x6
jsr    xp_cpal

| !!! INSERT AT: 20ED2
| !!! LENGTH: 0x6
jsr    xp_cpal

| !!! INSERT AT: 20FD2
| !!! LENGTH: 0x6
jsr    xp_cpal

| stage objects (0x1674E: a loop over the stage's list in 0x16792, an object
| allocated (0x2DA46) for each entry)
| !!! INSERT AT: 1675E
| !!! LENGTH: 0x6
jsr    xp_cobj

| stage music (0x2BBF0: d0 = stage; song = word 0x2BC12[d0], then 0x2B294)
| !!! INSERT AT: 2BC00
| !!! LENGTH: 0x10
jsr    xp_cmus
jmp    0x2B294
nop
nop

| =============================================================================
| CODE (pzf.04 free space)
| =============================================================================
| !!! INSERT AT: 0F1500
| !!! LENGTH: 0x200
| NE if the stage is the castle; every register kept
xp_iscastle:
movem.l %d0/%a0, -(%sp)
moveq  #0, %d0
cmpi.w #DAN_STAGE, A5 + 0x100
bne.b  ic_out
cmpi.b #3, A5 + 0xAC                | two players: XP_CASTLE decides
bne.b  ic_1p
tst.b  XP_CASTLE                    | (in a one-player game it may be stale:
sne    %d0                          | the attract demo goes through xp_stage)
bra.b  ic_out
ic_1p:
lea    PLAYER1, %a0                 | the CPU (+0x9E set)
tst.b  0x9E(%a0)
bne.b  ic_cpu
lea    PLAYER2, %a0
tst.b  0x9E(%a0)
beq.b  ic_out
ic_cpu:
jsr    xp_zis_ok                    | code_zangief.s (Z: not Zangief)
beq.b  ic_out
moveq  #1, %d0
ic_out:
tst.b  %d0
movem.l (%sp)+, %d0/%a0
rts

xp_cs2:
movea.l #0x17D08, %a3               | what the hook replaced
jsr    xp_iscastle
beq.b  c2_out
movea.l #CTAB, %a3
c2_out:
rts

xp_cpal:
lea    0xA22C0, %a0                 | what the hook replaced
jsr    xp_iscastle
beq.b  cp_out
lea    CPAL - DAN_STAGE * 0x200, %a0
cp_out:
rts

xp_cobj:
jsr    xp_iscastle
bne.b  co_none
jmp    0x2DA46                      | what the hook replaced (its flags go back)
co_none:
addq.l #4, %sp                      | out of 0x1674E: no objects
rts

xp_cmus:
moveq  #0, %d1                      | 0x2BC00-0x2BC0A: d1 = word 0x2BC12[d0]
moveq  #0, %d2                      | (1 + d0 / 2 for the stages 0-20)
moveq  #0, %d3
move.w %d0, %d1
lsr.w  #1, %d1
addq.w #1, %d1
cmpi.w #22, %d0                     | (stage 22 reads the word after the table)
bne.b  cm_tab
move.w #0x4A2D, %d1
cm_tab:
jsr    xp_iscastle
beq.b  cm_out
moveq  #24, %d1                     | Pocket Fighter's castle (qsconv.py)
cm_out:
rts

