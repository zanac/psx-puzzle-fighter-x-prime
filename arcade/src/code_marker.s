| X" on the arcade set: the X" marker in matches and the title line.
| Code blocks: opcodes of the encrypted pzfe.03 (patched decrypted, then
| encrypted again by tools/arcade.py). They replace parts of KScl's X' code.

| =============================================================================
| X" BETWEEN THE WIN COUNTERS (KScl's hook at 0x3F000, '"' instead of "'")
| =============================================================================
| !!! INSERT AT: 3F000
| !!! LENGTH: 0x3E
move.l %sp, %d0             | stack position tells a player match from attract
cmpi.l #0xFF0700, %d0
bpl.b  xm_player
lea    0x900EF0.l, %a0      | attract: out of the way of the logo
bra.b  xm_draw
xm_player:
lea    0x900BF0.l, %a0      | player match: centre
xm_draw:
move.l #0x00E80019, (%a0)   | X (top, bottom)
move.l #0x00F80019, 4(%a0)
lea    0x80(%a0), %a0       | next column
move.l #0x00820019, (%a0)   | " (top, bottom)
move.l #0x00920019, 4(%a0)
jmp    0x2DAC6.l

| =============================================================================
| TITLE LINE: 'X" BALANCE PATCH BY ZANAC' (25 characters, centred)
| =============================================================================
| KScl's routine at 0x3F100 draws the string at 0x3F900 from column 16;
| the longer line starts at column 12.
| !!! INSERT AT: 3F104
| !!! LENGTH: 0x6
lea    0x900670.l, %a1
