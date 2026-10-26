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
- `X'` marker in game

## Status

Done:

- **Drop patterns.** New patterns for the five characters, including the Counter Gem previews on the select screen.
- **Damage formula.** It reproduces the arcade X' patch exactly. It was fuzz-tested in an emulator against a Python model of the arcade code.
- **Diamond.** It always applies its penalty, so the diamond trick is gone.
- **Character select.** Pressing Down on the bottom row cycles through Devilot, Akuma, Dan, Mei-Ling and Anita, and the select screen now has name labels for Mei-Ling and Anita.
- **Markers.** `X'` appears between the win counters during matches, and "X' BALANCE PATCH" appears on the title screen.
- **Codes.** The old secret-character codes are disabled; cycling replaces them.

See [docs/RESEARCH.md](docs/RESEARCH.md) for the map of the PSX executable.

## Building

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
Mei-Ling and Anita keep Hsien-Ko's and Donovan's portrait on the select
screen, with their own name label; they appear as themselves in the match.

## Tools

| Path | Purpose |
|---|---|
| `tools/pbp2bin.py` | PSX PBP (PSISOIMG) → BIN/CUE |
| `tools/psxiso.py` | list / extract the ISO9660 file system of a raw BIN |
| `tools/findpat.py` | scan a file for drop-pattern-shaped tables |
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
