| X" on the arcade set: Zangief on the WINNER screen: his own win quotes and
| his picture.
|
| Picture: the winner's object takes entry 0x7DAC6[character] (0x23C94, from
| 0x23B5C / 0x23C34, a4 = the player struct; the character's 10 palettes are
| already loaded): a full-body picture (Dan: a tiny figure). Zangief gets
| ZWIN (tools/arcade.py: Pocket Fighter's portrait, full body), its palette
| in the object's slot.
|
| English (a5+0x92 set): the quote index (0xFF8136) is the winner's character
| * 4 + random 0-3 (0xBC5A); the text routine (0x2A744) takes line index *
| 136 from the language's text table and a line count byte from another.
| Zangief (Dan's slot, his bit) gets the indexes 44-47, whose text and line
| counts are at ZQUOTES (tools/cps2quotes.py: his Pocket Fighter quotes).
| The Japanese texts (a5+0x92 clear) keep Dan's.

.set A5,         0xFF8000
.set ZQUOTES,    0x9E000            | 4 x 136 bytes of text, then 4 line counts
.set ZQ_FIRST,   44
.set ZWIN,       0x9D000            | pseudo entry, palette (+8), positions, frame

| !!! INSERT AT: 23B5C
| !!! LENGTH: 0x8
jmp    xp_zwinpic

| !!! INSERT AT: 23C34
| !!! LENGTH: 0x8
jmp    xp_zwinpic

| quote index: d0 = random 0-3 (the hook replaces everything up to the rts)
| !!! INSERT AT: 0BC64
| !!! LENGTH: 0x14
jmp    xp_zqidx

| text of the quote: fp+0x1A = index, a0 / a1 = the language's text / line
| count tables, d6 = language * 2
| !!! INSERT AT: 2A76A
| !!! LENGTH: 0x8
jsr    xp_zqtext

| !!! INSERT AT: 0F1000
| !!! LENGTH: 0x200
xp_zqidx:
movea.w A5 + 0x13A, %a0             | the winner's player struct
moveq  #0, %d1
move.b 0x82(%a0), %d1
lsl.w  #2, %d1
add.w  %d1, %d0
move.l %a0, %d1                     | 24 bits for xp_zis_ok
andi.l #0xFFFFFF, %d1
movea.l %d1, %a0
jsr    xp_zis_ok                    | code_zangief.s (Z: not Zangief)
beq.b  qi_set
addq.w #4, %d0                      | Dan's 40-43 -> his 44-47
qi_set:
move.w %d0, A5 + 0x136
rts

| d0 = character, a4 = player struct (sign-extended), fp = picture object
xp_zwinpic:
move.l %a0, -(%sp)
move.l %a4, %d1
andi.l #0xFFFFFF, %d1
movea.l %d1, %a0
jsr    xp_zis_ok                    | code_zangief.s (Z: not Zangief)
movea.l (%sp)+, %a0
bne.b  zw_his
jmp    0x23C94                      | the game's: entry from 0x7DAC6[d0]
zw_his:
movem.l %d0/%a0-%a1, -(%sp)
moveq  #0, %d0
tst.b  12(%fp)
bpl.b  zw_slot
move.b 13(%fp), %d0
andi.w #31, %d0
zw_slot:
lsl.w  #5, %d0
lea    0x90C000, %a1
adda.w %d0, %a1
lea    ZWIN + 8, %a0
moveq  #7, %d0
zw_copy:
move.l (%a0)+, (%a1)+
dbf    %d0, zw_copy
move.l #ZWIN, 28(%fp)
movem.l (%sp)+, %d0/%a0-%a1
rts

xp_zqtext:
move.w 26(%fp), %d0
lea    0(%a1, %d0.w), %a1
tst.w  %d6                          | English only
beq.b  qt_out
cmpi.w #ZQ_FIRST, %d0
bcs.b  qt_out
lea    ZQUOTES + 4 * 136 - ZQ_FIRST, %a1
adda.w %d0, %a1
lea    ZQUOTES - ZQ_FIRST * 136, %a0
qt_out:
rts
