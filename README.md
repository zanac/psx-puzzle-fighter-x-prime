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
- Mei-Ling and Anita count as Hsien-Ko and Donovan (no +25 %); the Versus Difficulty 1-5 handicap stays as in vanilla
- Devilot, Akuma and Dan selectable without codes
- **PSX X' addition — Dan:** new "Gadoken" drop pattern (red spine: columns 1/3/5 red, mixed pairs between) instead of all red; sends 110 % and receives 110 %
- `X'` marker in game

## Screenshots

**Title screen.** "X' BALANCE PATCH" is shown under the copyright.

![Title screen](docs/screenshots/title.png)

**Secret characters without codes.** On the bottom row, Down cycles the cell through Devilot → Akuma → Dan → Mei-Ling → Anita and back.
Mei-Ling and Anita get their own name labels, which the original select screen never had.

![Secret character cycle](docs/screenshots/select_cycle.png)

![Mei-Ling vs Anita on the select screen](docs/screenshots/select_meiling_anita.png)

**New drop patterns.** Counter Gem previews, vanilla (top) vs X' (bottom), generated from the game's own pattern tables.

![Counter Gem patterns, vanilla vs X'](docs/screenshots/counter_gems.png)

**In game.** `X'` sits between the win counters, as in the arcade patch.

![Match with the X' marker](docs/screenshots/match.png)

## Status

Done:

- **Drop patterns.** New patterns for the five characters, including the Counter Gem previews on the select screen.
- **Damage formula.** It reproduces the arcade X' patch exactly. It was fuzz-tested in an emulator against a Python model of the arcade code.
- **Diamond.** It always applies its penalty, so the diamond trick is gone.
- **Character select.** Pressing Down on the bottom row cycles through Devilot, Akuma, Dan, Mei-Ling and Anita, and the select screen now has name labels for Mei-Ling and Anita.
- **Markers.** `X'` appears between the win counters during matches, and "X' BALANCE PATCH" appears on the title screen.
- **Codes.** The old secret-character codes are disabled; cycling replaces them.

See [docs/RESEARCH.md](docs/RESEARCH.md) for the map of the PSX executable.

## Download and patching

Get the zip from [Releases](https://github.com/zanac/psx-puzzle-fighter-x-prime/releases). It contains no game data. You need your own **Super Puzzle Fighter II Turbo, NTSC-U, SLUS-00418** image (single-track BIN or PBP) and Python 3; nothing else.

```sh
./patch.sh original.bin  xprime.bin      # or
./patch.sh original.pbp  xprime.pbp
python3 tools/applypatch.py xprime-patch.json original.bin xprime.bin   # same, any OS
```

The output keeps the input's format. For BIN output, copy the original `.cue` and point its FILE line at the new `.bin`.

The patcher checks the SHA-1 of every file it changes, before and after, so a different version or a modified image is rejected.
Tested on PCSX ReARMed; reports from other emulators or real hardware are welcome.

## Building from source

```sh
./build.sh original.pbp  xprime.pbp  [path/to/armips]
./build.sh original.bin  xprime.bin  [path/to/armips]
```

The input must be the original NTSC-U SLUS-00418; the script checks the
executable's hash. The output has the same format as the input. For BIN
output, reuse the original `.cue` and rename the file inside it if needed.

Needs `python3` and [armips](https://github.com/Kingcom/armips).

## How to play the secret characters

On the character select screen, move to the bottom row and keep pressing
**Down**: the character on that cell cycles through Devilot, Akuma, Dan,
Mei-Ling and Anita, then back. Up, Left or Right return to the normal grid.
As in vanilla, the button used to confirm picks the colours: Circle or
Triangle give the standard colours, Cross or Square the alternate ones.

Mei-Ling and Anita keep Hsien-Ko's and Donovan's portrait on the select
screen, with their own name label; they appear as themselves in the match.

## Tools

| Path | Purpose |
|---|---|
| `tools/pbp2bin.py` | PSX PBP (PSISOIMG) → BIN/CUE |
| `tools/psxiso.py` | list / extract the ISO9660 file system of a raw BIN |
| `tools/findpat.py` | scan a file for drop-pattern-shaped tables |
| `patch.sh`, `tools/applypatch.py` | apply `xprime-patch.json` (no assembler needed) |
| `tools/mkpatch.py` | create `xprime-patch.json` from an original and a built image |
| `tools/nav.py` | menu navigation helpers for the emulator tests |
| `tools/discpatch.py` | replace files in a BIN or PBP (EDC/ECC, PBP rebuild) |
| `tools/previews.py` | redraw the Counter Gem previews from the EXE table |
| `tools/lzh.py` | codec for the sprite-graphics LZ (decoder `0x8010D5C0`) |
| `tools/labels.py` | builds the MEI-LING / ANITA select-screen labels in FIRST.EMI |
| `tools/regress.py` | end-to-end regression in the emulator (screens, damage, secrets) |
| `tools/model.py` | Python model of the arcade X' damage formula (for tests) |
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
