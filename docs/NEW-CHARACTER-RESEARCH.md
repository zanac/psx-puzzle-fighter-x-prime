# Zangief port: step 0 research

Findings so far for [PLAN-new-character.md](PLAN-new-character.md). All addresses are RAM unless noted.

## Pocket Fighter (SLUS-00653): Zangief's sprites, decoded

`tools/pf_sprites.py PLAYER/ZANGIEF.PAC OUTDIR --sheet` dumps all **492 frames** of `ZANGIEF.PAC` to PNG. They cover:
- stance and walking;
- normal moves and specials (Double Lariat, Spinning Piledriver…);
- the costume-change moves (worker, cook, bear…);
- hit, knock-down and dizzy;
- win poses;
- small items and effects.

`ZANGIEFF.PAC` (the larger "F" set) has not been decoded yet; it uses the same format.

**PAC container.** It starts with `u32 count`, then `u32 total size`, then `count` pairs of `(u32 type, u32 size)`. Entries are 0x800-aligned from 0x800.

| Type | Content |
|---|---|
| 0 | Compressed 16×16 4bpp cells. Kept compressed in RAM (`0x80037000` in a training match) and decoded on the fly by `0x80192C34` into the scratchpad. |
| 1 | `u32` table. It starts with 12-byte frame records (493 for Zangief), followed by the cell lists. |
| 2 | 16-colour BGR555 palettes (115). |

**Frame record.** The fields are `u16 index, u8 rows, u8 columns, u16 x, u16 y, u16 cells, u16 flags`. At `table[index]`:
1. A presence mask of `ceil(rows×columns/32)` words. It is read byte by byte, MSB first, with cells in column-major order. Drawing code: `0x80191D50`.
2. One word per present cell:
   - bits 0-23: offset in type 0;
   - bits 24-28: palette offset;
   - bits 30-31: flip (1 = vertical, 2 = horizontal; copy routines in the table at `0x801D1178`).

**Cell compression.** Each cell starts with a flag byte, read LSB first:
- flag 0: a literal byte;
- flag 1: a control byte `c`, with `d = c >> 4` and `n = c & 15`:
  - `d ≠ 0`: copy `n` bytes from `d` bytes back (`n = 0` copies nothing);
  - `d = 0`: repeat the next byte `n + 1` times.

A cell is complete at 128 bytes.

**Size.** Zangief's stance is about **105×81 px**; his frame boxes are up to 128×96.

## Super Puzzle Fighter II Turbo: in-match character sprites

`tools/spf_sprites.py PLxx_OBJ.EMI OUTDIR` dumps a character's frames as a grayscale sheet; the CLUTs are not mapped yet.

**`PLxx_OBJ.EMI`** has two entries:

| Entry | Content | RAM | Room |
|---|---|---|---|
| 0 | LZ graphics: the halfword LZ of `tools/lzh.py`, decoder `0x8010D5C0`, called by `0x8010D558` | P1 `0x80024000`, P2 `0x8006C000` | **0x48000** bytes per player |
| 1 | 44-byte frame records | P1 `0x800E7600`, P2 `0x800EBB00` | **0x4500** bytes per player (about 400 records) |

**Frame record.** The fields are `u32 offset`, `s16 x, s16 y` (anchor, e.g. −32, −63), `u8 rows, u8 columns` (16 px cells), `u8 units` (decoded size / 128) and `u8 flags`. Then comes a cell mask: words from +12, bit 31 first, row-major. The drawing loop is `0x8010CCDC`, with rows outer and columns inner. The decoded data is a 256 px-wide strip of the present cells.

Many records are small overlay parts (eyes, mouth, headband) drawn over a body frame.

**Sizes and budgets of existing characters:**

| File | Records | Entry 0 | Entry 1 | Stance bbox |
|---|---|---|---|---|
| PL00 Morrigan | 229 | 0x33776 | 0x275C | 58×73 |
| PL02 Ryu | 236 | 0x27120 | 0x2890 | 61×63 |
| PL03 Ken | 237 | 0x2032A | 0x28BC | 61×61 |
| PL04 Hsien-Ko + Mei-Ling | 382 | 0x30C76 | 0x41A8 | 57×68 |
| PL05 Donovan + Anita | 331 | 0x3B50A | 0x38E4 | 52×65 |
| PL9A Akuma + Dan | 247 | 0x3B8CC | 0x2A74 | 61×70 |

**Consequences for Zangief:**
- **Scale.** At 105×81, Pocket Fighter's Zangief is about 1.3–1.7× an SPF2T character. To fit, he has to be scaled to roughly **0.75–0.8**, giving about 80×63, a little bigger than the others, which suits Zangief. Shrinking pixel art has to be done with care (palette-aware, with hand checks of key frames).
- **His own file.** The alternates (Mei-Ling, Anita) live inside their base character's file. `PL9A` (Akuma + Dan) has only about 0xC700 bytes left in the 0x48000 buffer, so Zangief needs **his own `PL0B_OBJ.EMI`**. The loader must pick it when his alternate bit is set.

## The alternate mechanism (option B)

Mei-Ling and Anita are not a generic feature. They are **hand-coded checks** in about **40 functions**: everywhere the game tests `0x801AE4D8` (Mei-Ling bits) or `0x801AE4D9` (Anita bits), it branches to Mei-Ling's or Anita's own data tables. Coverage in a Versus match (Mei-Ling against Anita) shows where they run:

| Where | Functions |
|---|---|
| Select screen, boot | `0x801245DC`, `0x80136554`, `0x80138DB0`, `0x80139FFC`, `0x8013A9CC`, `0x8013AD30` |
| Match start | `0x80121B4C`, `0x80121CA4`, `0x801221C8`, `0x80122344`, `0x80122410`, `0x80128D88`, `0x80136A18`, `0x801461AC`, `0x80146930`, `0x801469FC` |
| During the match | `0x80129EDC`, `0x80134D80` (damage, ours), `0x80135A94`, `0x80136740`, `0x80136B20`, `0x80146380`, `0x80146BDC`, `0x80146D48` |
| Not reached in this test (win screen, endings, Arcade…) | `0x80111770`, `0x80111974`, `0x8011267C`, `0x80113204`, `0x801138E8`, `0x80115820`, `0x8011658C`, `0x80116D70`, `0x80117600`, `0x801226F0`, `0x80135800`, `0x801360DC`, `0x80137B78`, `0x80146584`, `0x80146E3C`, `0x80146F9C`, `0x80147248` |

**Consequence.** Option B means adding a third branch, "Zangief bit → Zangief's tables", in each relevant function (about 25-30 for Versus only), plus his file. That is a lot of work, but **the list of places is known exactly** from the references to the two alternate bytes. With option A, we would have to discover every per-character table blind. **B remains the recommendation.**

## Music

Both games use the same XA format: 8 interleaved channels, stereo, 37.8 kHz, 4-bit.
- Pocket Fighter: `KYOKU/XA00-04.XA`.
- SPF2T: `STR/ORG00-02.XA` and `STR/QSD00-02.XA`.

So Zangief's theme can be copied **sector for sector** into a new XA file for SPF2T.

**Tracing the music.** The instrumented core now logs every `CdlSetfilter`. `xdbg_cd_log()` returns `file << 24 | channel << 16 | low bits of the LBA`, and `xdbg_cd_lba()` returns the current read position.
- A Pocket Fighter channel holds several songs back to back. The song is chosen by the start position, not only by the channel.
- Free Battle always plays on the same stage, whatever the characters. Its music is file 1 (`XA00`), channel 0, from about LBA 344.
- To get **Zangief's own** stage and theme, an Arcade match against him is needed (his home stage). That is planned for step 6, with the same tracing.

Also still to do: how SPF2T maps a stage to its XA file, channel and start.

## Voices

Both games store voices and effects as standard VAB banks:
- SPF2T: `SE_PLxx.EMI`.
- Pocket Fighter: `SE/SExxA/B/C.PAC`, with the VAB at +0x1000.

Still to do:
- find which Pocket Fighter bank is Zangief's;
- map each SPF2T voice id to its use (attacks, damage, win, lose).

## Stage

- Pocket Fighter loads files by index through a table of 12-byte entries `(LBA, size, type)`. In RAM it sits at `0x801D0268 − 12 × 0xEE` (the EXE loads at `0x80188A00`).
- `STAGE/ST00.PAC` is file id `0xEE`; `ST01`–`ST08` follow.
- Free Battle always loads `ST00` (the "MAX MUM" bar), whatever the characters.
- There are only 9 stages for 12 characters, so some characters share one. Zangief's home stage is the one Arcade uses against him; finding it is part of step 6.

Not mapped yet:
- SPF2T stages are 36 sectors each (`STAGEnn.EMI`).
- Pocket Fighter stages are `STAGE/STnn.PAC`, multi-layer.

A crop of Zangief's Pocket Fighter stage will have to be redrawn into the SPF2T stage format (step 6).

## Corrections

The note in `src/stage.asm` said that the reused function at `0x801544E4` never runs, "per emulator coverage". That first coverage run was **not actually active**: the debugger flag was off, so it recorded nothing. It has now been redone properly on the original disc, through boot, attract, menus, Versus select and a match: 37,793 code words were covered and **0** of them fall in `0x801544E4–0x801548C8`. The claim holds.
