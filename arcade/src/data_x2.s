| X" on the arcade set: data blocks (read as data, never as opcodes): they go
| into the ROM as they are.

| =============================================================================
| DAN: "Gadoken" drop pattern, sends and receives 110 %
| =============================================================================
| Same pattern as the PSX X" (src/xprime.asm). Blue:1 Yellow:2 Green:3 Red:4,
| bottom row first. The select screen preview is drawn from it at build time
| (tools/cps2preview.py).

| !!! INSERT AT: 010908
| !!! LENGTH: 0xC0
dc.w 4, 2, 4, 3, 4, 1, 0, 0
dc.w 4, 2, 4, 3, 4, 1, 0, 0
dc.w 4, 1, 4, 2, 4, 3, 0, 0
dc.w 4, 1, 4, 2, 4, 3, 0, 0
dc.w 4, 2, 4, 3, 4, 1, 0, 0
dc.w 4, 2, 4, 3, 4, 1, 0, 0
dc.w 4, 1, 4, 2, 4, 3, 0, 0
dc.w 4, 1, 4, 2, 4, 3, 0, 0
dc.w 4, 2, 4, 3, 4, 1, 0, 0
dc.w 4, 2, 4, 3, 4, 1, 0, 0
dc.w 4, 1, 4, 2, 4, 3, 0, 0
dc.w 4, 1, 4, 2, 4, 3, 0, 0

| Receive rate /20 (KScl's table at 0x10120, by character): Dan 22, then
| slot 11 = Zangief 18 (code_zangief.s gives him index 11)
| !!! INSERT AT: 01012A
| !!! LENGTH: 0x2
dc.b 0x16, 0x12

| Send rate /20 (KScl's table at 0x10140): Dan 22, Zangief 18
| !!! INSERT AT: 01014A
| !!! LENGTH: 0x2
dc.b 0x16, 0x12

| =============================================================================
| ZANGIEF: "Siberian Bear" drop pattern (3x2 blocks), as on the PSX
| =============================================================================
| !!! INSERT AT: 09F400
| !!! LENGTH: 0xC0
zg_pattern:
.rept 3
dc.w 3, 3, 3, 2, 2, 2, 0, 0
dc.w 3, 3, 3, 2, 2, 2, 0, 0
dc.w 4, 4, 4, 1, 1, 1, 0, 0
dc.w 4, 4, 4, 1, 1, 1, 0, 0
.endr

| =============================================================================
| TITLE TEXT (KScl's string slot at 0x3F900, followed by free space)
| =============================================================================
| !!! INSERT AT: 3F900
| !!! LENGTH: 0x1A
.ascii "X\" BALANCE PATCH BY ZANAC\x00"

| =============================================================================
| SELECT NAVIGATION (KScl's tables): Zangief and Dan in row 0, above Chun-Li
| and Sakura; Dan leaves the secret row (Devilot, Akuma)
| =============================================================================
| !!! INSERT AT: 3F840
| !!! LENGTH: 0x28
dc.b 0xFF, 0x0A, 0x0A, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
dc.b 0x02, 0x01, 0x07, 0x03, 0xFF, 0xFF, 0xFF, 0xFF
dc.b 0x00, 0x04, 0x05, 0x06, 0xFF, 0xFF, 0xFF, 0xFF
dc.b 0x08, 0x09, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
dc.b 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF

| start positions per character (Dan: row 0, column 2)
| !!! INSERT AT: 3F888
| !!! LENGTH: 0x4
dc.b 0x18, 0x19, 0x02, 0x08
