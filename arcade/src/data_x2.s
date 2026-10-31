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

| Receive rate /20 (KScl's table at 0x10120, by character): Dan 22, then slot 11
| !!! INSERT AT: 01012A
| !!! LENGTH: 0x2
dc.b 0x16, 0x14

| Send rate /20 (KScl's table at 0x10140): Dan 22
| !!! INSERT AT: 01014A
| !!! LENGTH: 0x2
dc.b 0x16, 0x14

| =============================================================================
| TITLE TEXT (KScl's string slot at 0x3F900, followed by free space)
| =============================================================================
| !!! INSERT AT: 3F900
| !!! LENGTH: 0x1A
.ascii "X\" BALANCE PATCH BY ZANAC\x00"
