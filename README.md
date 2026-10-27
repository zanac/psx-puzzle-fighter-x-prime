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
- **Versus stage selector (experimental branch):** NORMAL, RANDOM or a fixed stage, chosen by P1 on the select screen

## Screenshots

**Title screen.** "X' BALANCE PATCH BY ZANAC" is shown under the copyright.

![Title screen](docs/screenshots/title.png)

**Secret characters without codes.** On the bottom row, Down cycles the cell through Devilot → Akuma → Dan → Mei-Ling → Anita and back.
Mei-Ling and Anita get their own name labels, which the original select screen never had.

![Secret character cycle](docs/screenshots/select_cycle.png)

![Mei-Ling vs Anita on the select screen](docs/screenshots/select_meiling_anita.png)

**New drop patterns.** Counter Gem previews, vanilla (top) vs X' (bottom), generated from the game's own pattern tables.

![Counter Gem patterns, vanilla vs X'](docs/screenshots/counter_gems.png)

**In game.** `X'` sits between the win counters, as in the arcade patch.

![Match with the X' marker](docs/screenshots/match.png)

**Versus stage selector.** P1 picks the stage under the character grid with SELECT. From left to right: RANDOM, then AKUMA, and the match that follows on Akuma's stage.

![Stage selector: RANDOM, AKUMA, match on Akuma's stage](docs/screenshots/stage_selector.png)

RANDOM changes the stage at every match:

![Four RANDOM matches in a row](docs/screenshots/stage_random.png)

## Status

Done:

- **Drop patterns.** New patterns for the five characters, including the Counter Gem previews on the select screen.
- **Damage formula.** It reproduces the arcade X' patch exactly. It was fuzz-tested in an emulator against a Python model of the arcade code.
- **Diamond.** It always applies its penalty, so the diamond trick is gone.
- **Character select.** Pressing Down on the bottom row cycles through Devilot, Akuma, Dan, Mei-Ling and Anita, and the select screen now has name labels for Mei-Ling and Anita.
- **Markers.** `X'` appears between the win counters during matches, and "X' BALANCE PATCH BY ZANAC" appears on the title screen.
- **Codes.** The old secret-character codes are disabled; cycling replaces them.
- **Versus stage selector** (branch `experimental/random-stage`). It is described below.
- **Output formats.** The patch and build scripts always write BIN + CUE and PBP, whatever the input.

See [docs/RESEARCH.md](docs/RESEARCH.md) for the map of the PSX executable.

## Versus stage selector (experimental)

This feature is on the branch `experimental/random-stage`.

In Versus, the character select shows a stage line under the grid. **P1** presses **SELECT**, before confirming, to cycle through:

`NORMAL → RANDOM → MORRIGAN → CHUN-LI → RYU → KEN → HSIEN-KO → DONOVAN → FELICIA → SAKURA → DEVILOT → AKUMA`

- **NORMAL** is the vanilla behaviour: the stage of P1's character. It is the default.
- **RANDOM** draws a new stage at every match and never repeats the stage of the previous match.
- A **fixed stage** is used for every match.
- Each stage brings its own music, as in vanilla.
- The choice is kept from match to match (CONTINUE) and goes back to NORMAL when the title screen comes back.
- In a 3-round match, the stage stays the same for every round.
- Arcade, Street Puzzle and the demo are not changed.

![Stage line on the select screen](docs/screenshots/stage_select.png)

Details: [docs/PROPOSAL-random-stage.md](docs/PROPOSAL-random-stage.md), and section 7b of [docs/RESEARCH.md](docs/RESEARCH.md).

## Download and patching

Get the zip from [Releases](https://github.com/zanac/psx-puzzle-fighter-x-prime/releases). It contains no game data.

You need two things:
- Your own **Super Puzzle Fighter II Turbo, NTSC-U, SLUS-00418** image, as a BIN, a CUE (one or more BIN files, e.g. a Redump set) or a PBP.
- Python 3. Nothing else is needed.

```sh
./patch.sh original.pbp xprime        # or original.bin / original.cue
python3 tools/applypatch.py xprime-patch.json original.pbp xprime   # same, any OS
```

Whatever the input, you always get all three outputs:

| File | Use |
|---|---|
| `xprime.bin` + `xprime.cue` | one BIN with all 3 tracks (data + 2 CD audio) |
| `xprime.pbp` | single-disc PBP |

From a **PBP** input, the patched PBP keeps the original header and PSP loader, so it behaves like the original on a PSP.

From a **BIN/CUE** input, the PBP is built from scratch without a `DATA.PSP`. It works in emulators, but a real PSP needs a PBP made with a PSP tool from the patched BIN/CUE.

For a BIN input without a `.cue` beside it, the track layout comes from the known layout of this disc.

The patcher checks the SHA-1 of every file it changes, before and after, so a different version or a modified image is rejected.
Tested on PCSX ReARMed with all three outputs; reports from other emulators or real hardware are welcome.

## Building from source

```sh
./build.sh original.pbp  xprime  [path/to/armips]     # or original.bin / original.cue
```

The input must be the original NTSC-U SLUS-00418; the script checks the
executable's hash. As with `patch.sh`, it writes `xprime.bin`, `xprime.cue`
and `xprime.pbp`.

Needs `python3` and [armips](https://github.com/Kingcom/armips).

## How to play the secret characters

On the character select screen, move to the bottom row and keep pressing
**Down**: the character on that cell cycles through Devilot, Akuma, Dan,
Mei-Ling and Anita, then back. Up, Left or Right return to the normal grid.
As in vanilla, the button used to confirm picks the colours: Circle or
Triangle give the standard colours, Cross or Square the alternate ones.

Mei-Ling and Anita keep Hsien-Ko's and Donovan's portrait on the select
screen, with their own name label; they appear as themselves in the match.

## How to choose the Versus stage

On the Versus character select, P1 presses **SELECT** before confirming the
character. The line under the grid shows the setting (NORMAL, RANDOM or a
stage name). P2's SELECT does nothing.

## Tools

| Path | Purpose |
|---|---|
| `tools/discout.py` | disc input (BIN, CUE, PBP) and output (BIN + CUE + PBP); also converts between them |
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
| `src/stage.asm` | Versus stage selector (included by `src/xprime.asm`) |
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
