| X" on the arcade set: the X" marker in matches (the title line is moved by
| code_stage.s, which also hooks the title).
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
