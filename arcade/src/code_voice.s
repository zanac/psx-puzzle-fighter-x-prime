| X" on the arcade set: Zangief's voices.
|
| Voice id = base[character] (table 0x2BE7E: 0x120, 0x140, ... Dan 0x250) +
| d0 (0x2BE50; d0 from the attack voice table 0x14496: character * 64 +
| category * 8 + variant), + 0x200 for P2 (the same voice on channel 11).
| Dan's offsets in use: 2-7, 15, 20. For Zangief the id comes from
| ZVOICES (his Pocket Fighter voices converted by tools/qsconv.py into free
| song slots s / s + 0x200; tools/arcade.py ZVOICES gives the choice).

.set XP_ZBITS,   0xFF3010
.set ZVOICES,    0x9E300            | 32 words: Zangief's P1 id by Dan's offset (tools/arcade.py)

| fp = player struct, d0 = offset; d1 = id (the instructions replaced)
| !!! INSERT AT: 2BE5E
| !!! LENGTH: 0x6
jsr    xp_zvoice

| !!! INSERT AT: 0F1400
| !!! LENGTH: 0x100
xp_zvoice:
move.l %a0, -(%sp)
lea    xp_vbase, %a0                | the game's table, read pc-relative
move.w 0(%a0, %d1.w), %d1
add.b  %d0, %d1
move.l %fp, %a0                     | fp = the player struct
jsr    xp_zis_ok                    | code_zangief.s (Z: not Zangief)
beq.b  vo_out
moveq  #0, %d1
move.b %d0, %d1
andi.w #0x1F, %d1
add.w  %d1, %d1
lea    ZVOICES, %a0
move.w 0(%a0, %d1.w), %d1
vo_out:
movea.l (%sp)+, %a0
rts
xp_vbase:
.short 0x120, 0x140, 0x160, 0x180, 0x1A0, 0x1C0, 0x1E0, 0x200, 0x220, 0x240, 0x250
