# Zangief voice map

How Zangief's voices are wired, so a sample can be swapped quickly. Change `VOICE_MAP` in `tools/zangief.py` and rebuild (`./build.sh <SPF2T> <Pocket Fighter> <output>`).

- The game plays voice **ids** from Dan's sound table (`SE_PL0A.EMI` entry 0). Ids 0–23 are the 24 slots; 25–33 replay some slots with other parameters.
- Script cues use Dan's voice table `0x8016EFF4` (index 1–6 → ids 25–30; 7/8 → ids 14/15, added for Zangief).
- Zangief's samples are the VAGs of Pocket Fighter `/SE/SE0AA.PAC` (01–31). `/SE/SE0AC.PAC` adds 32–56 (costume moves); those are not built in yet: using one needs `zangief.py voices` to read SE0AC instead.

## Slots

| Dan slot | When the game plays it | Zangief voice |
|---|---|---|
| 1 | ids 0, 25: attack cue (state 11, Double Lariat) | 30 |
| 2 | ids 1, 26: attack cue (state 13, Piledriver) | 31 |
| 3 | ids 2, 31: attack (code, small attacks) | 05 |
| 4 | ids 3, 30: attack (code) and super start (state 14 cue) | 28 |
| 5 | ids 4, 32: attack (code) | 26 |
| 6 | id 5: during play (code), role unclear | 13 |
| 7 | id 6: during play (code), role unclear | 10 |
| 8 | ids 7, 27: opponent K.O.; attack cue (state 12) and super cue | 21 |
| 9 | ids 8, 28: win; super cue | 04 |
| 10 | id 9: not seen | 15 |
| 11 | id 10: not seen for Dan | 11 |
| 12 | id 11: win pose 34 (provocation pose) | 16 |
| 13 | id 12: not seen | 18 |
| 14 | id 13: not seen for Dan | 14 |
| 15 | id 14: "in trouble" 1 (Zangief only, state 1 cue) | 07 |
| 16 | id 15: "in trouble" 2 (Zangief only, state 2 cue) | 06 |
| 17 | ids 16, 29: after the win; super cue | 17 |
| 18 | id 17: not seen | 24 |
| 19 | ids 18, 33: attack (code) | 23 |
| 20 | id 19: hit reaction (state 6) | 08 |
| 21 | id 20: hit reaction (state 6) | 09 |
| 22 | id 21: during play (code), role unclear | 27 |
| 23 | id 22: not seen | 29 |
| 24 | id 23: lose | 12 |

## All Zangief voices

| Voice | In use (slot) | Pocket Fighter use |
|---|---|---|
| 01 | — | effect |
| 02 | — | effect |
| 03 | — | effect |
| 04 | slot 9 | played by code (hits, K.O., win…) |
| 05 | slot 3 | punch |
| 06 | slot 16 | a move |
| 07 | slot 15 | played by code (hits, K.O., win…) |
| 08 | slot 20 | played by code (hits, K.O., win…) |
| 09 | slot 21 | played by code (hits, K.O., win…) |
| 10 | slot 7 | played by code (hits, K.O., win…) |
| 11 | slot 11 | played by code (hits, K.O., win…) |
| 12 | slot 24 | played by code (hits, K.O., win…) |
| 13 | slot 6 | played by code (hits, K.O., win…) |
| 14 | slot 14 | a move |
| 15 | slot 10 | a move |
| 16 | slot 12 | a move |
| 17 | slot 17 | bear (start) |
| 18 | slot 13 | a move |
| 19 | — | a move |
| 20 | — | a move |
| 21 | slot 8 | taunt |
| 22 | — | a move |
| 23 | slot 19 | Double Lariat |
| 24 | slot 18 | a move |
| 25 | — | a move |
| 26 | slot 5 | special moves |
| 27 | slot 22 | a move |
| 28 | slot 4 | arms-up move |
| 29 | slot 23 | long special move |
| 30 | slot 1 | bear (end) |
| 31 | slot 2 | played by code (hits, K.O., win…) |
| 32 | — | costume moves |
| 33 | — | costume moves |
| 34 | — | costume moves |
| 35 | — | costume moves |
| 36 | — | costume moves |
| 37 | — | costume moves |
| 38 | — | costume moves |
| 39 | — | costume moves |
| 40 | — | costume moves |
| 41 | — | costume moves |
| 42 | — | costume moves |
| 43 | — | costume moves |
| 44 | — | costume moves |
| 45 | — | costume moves |
| 46 | — | costume moves |
| 47 | — | costume moves |
| 48 | — | costume moves |
| 49 | — | costume moves |
| 50 | — | costume moves |
| 51 | — | costume moves |
| 52 | — | costume moves |
| 53 | — | costume moves |
| 54 | — | costume moves |
| 55 | — | costume moves |
| 56 | — | costume moves |

Free today: 19, 20, 22, 25, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56 (01–03 are effects).

To listen: `python3 tools/zangief.py voices SE0AA.PAC SE_PL0A.EMI out.EMI --wav DIR` writes every Zangief and Dan sample as WAV (from your own discs).

## Arcade (spf2enh)

The arcade plays only 8 of Dan's voices (offsets 2-7, 15, 20 of his id 0x250 +
offset; offset n = PSX slot n + 1). `ZVOICES` in `tools/arcade.py` maps them to
Pocket Fighter's arcade voices (song ids of instrument bank 7), the same choices
as the PSX where an arcade take of the VAG exists:

| Dan offset | PSX slot | Zangief voice | PF arcade id (bank 7 #) |
|---|---|---|---|
| 2 | 3 | 05 punch | 0x1C7 (#37) |
| 3 | 4 | 28 arms-up move | 0x1F2 (#7) |
| 4 | 5 | 26 special moves | 0x1ED (#23) |
| 5 | 6 | 13 | 0x1DB (#33) |
| 6 | 7 | 10 has no arcade take: 11 | 0x1D8 (#0) |
| 7 | 8 | 21 taunt | 0x1E6 (#20) |
| 15 | 16 | 06 has no arcade take: 07 | 0x1CC (#45) |
| 20 | 19 | 23 Double Lariat | 0x1E8 (#49) |

PSX VAG -> PF arcade bank 7 instrument, matched on the waveforms: 04 #43, 05 #37,
07 #45, 08 #5, 09 #30, 11 #0, 13 #33, 14 #32, 15 #25, 16 #6, 17 #27, 18 #35,
21 #20, 23 #49, 24 #47, 26 #23, 27 #10, 28 #7, 30 #13. See docs/QSOUND.md.
