# Super Puzzle Fighter II Turbo X' — PlayStation

A port of the **X' rebalance** to the PlayStation version of Super Puzzle Fighter II Turbo
(NTSC-U, **SLUS-00418**).

X' is David Sirlin's rebalance from Puzzle Fighter HD Remix. It was brought back to
the original arcade game by [KScl/puzzle-fighter-x-prime](https://github.com/KScl/puzzle-fighter-x-prime).
This project reimplements the same logic in the PSX executable. The PSX port is
compiled C rather than 68k assembly, so every change is rewritten from scratch.

## Goals

- New drop patterns for Morrigan, Ryu, Hsien-Ko, Felicia and Sakura
- Garbage: Chun-Li sends 120 %, Devilot 85 %, Akuma 100 % but receives 120 %
- Diamond always sends 80 % ("diamond trick" removed)
- No handicap
- Devilot, Akuma and Dan selectable without codes
- `X'` marker in game

## Status

Research phase. See [docs/RESEARCH.md](docs/RESEARCH.md) for the full map of the
PSX executable (player struct, damage routine, diamond logic, character select,
tables) and the open design decisions.

## Tools

| Path | Purpose |
|---|---|
| `tools/pbp2bin.py` | PSX PBP (PSISOIMG) → BIN/CUE |
| `tools/psxiso.py` | list / extract the ISO9660 file system of a raw BIN |
| `tools/findpat.py` | scan a file for drop-pattern-shaped tables |
| `tools/lr.py` | headless libretro frontend (input scripting, RAM access, savestates, screenshots, watchpoints) |
| `emu/build.sh` | builds an instrumented pcsx_rearmed libretro core (`emu/pcsx_rearmed-xdbg.patch`) |

```sh
emu/build.sh
python3 tools/pbp2bin.py game.pbp work/spf2t
python3 tools/psxiso.py work/spf2t.bin extract work/fs
```

No game data is included in this repository.

## Credits

- Balance design: David Sirlin (Puzzle Fighter HD Remix)
- Arcade X' patch: KScl
- PSX port: Vanni Brutto
