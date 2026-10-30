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

## Step 1: room on the disc (done)

**Tools.**
- `tools/discexpand.py` adds files to `/DATA`:
  - each file gets its own Mode 2 Form 1 sectors right after the last file of the data track;
  - a 150-sector postgap follows, as on the original disc;
  - the CD-DA tracks move after them, by the same amount;
  - the PVD volume size grows by that amount, and the directory entries are added in sorted order (the `/DATA` directory had 1568 free bytes).
- `tools/makedisc.py` replaces files, adds the new ones and writes BIN + CUE + PBP.
- A PBP input keeps its own header and PSP loader: `discout.to_raw` and the template path of `write_pbp`. The TOC follows the moved tracks.

**EXE (`src/files.asm`).**
- The file LBA table (`0x80165CC0`, 0x54 files plus the CD-DA tracks at ids 0x54/0x55) cannot grow in place, so it moves to `0x801548C8`. That is a 512-byte function with no references and no execution in coverage (boot, menus, Versus, Arcade, Street Puzzle).
- Its only two readers are repointed: the file loader `0x801044A8` and the XA player `0x801063A4`.
- New files get ids 0x56, 0x57, … in the order given to `XP_NEWFILES` (see `build.sh`).

**Checks.**
- With no new files, the disc differs from the previous build only in 3 EXE sectors, and the regression passes.
- With two dummy files (300 KB and a copy of `STAGE03.EMI`):
  - the CD-DA moved by 183 sectors, byte for byte;
  - the files read back from the ISO are identical to the originals;
  - pointing stage 1's table entry at the copy in RAM loads it from the new location: Ken's background appears in a Chun-Li stage match;
  - the regression passes on both the PBP and the BIN/CUE outputs;
  - a BIN input gives the same output as a PBP input.
- The game never reads the CD-DA tracks in attract mode, and no file load uses ids 0x54/0x55. They may be unused (bonus audio), but their LBAs are moved anyway.

## Step 2: the slot (done)

Zangief is Dan (10) plus a per-player bit in `XP_ZBITS` (bit 0 P1, bit 1 P2), set and read only in Versus. All code is in `src/zangief.asm`, in two unreferenced functions that never run (`0x80163CDC`, 684 bytes, and `0x801639F8`–`0x80163C24`).

| Piece | How |
|---|---|
| Select cycle | Down: … Mei-Ling → Anita → **Zangief** → cell character; Up walks back (Zangief → Anita). In Arcade, Anita goes straight to the cell character. The bit is cleared with the alternate bits on a new game (`0x80123D80`). |
| Name label | Label 13 (an unused small Japanese label) redrawn as ZANGIEF by `tools/labels.py`; it spans labels 13+14, and record 13 takes MORRIGAN's 5-column geometry so the whole 78-px label shows. Key `0x1A` (Dan \| 0x10) selects frame `0x40`. |
| Counter Gem preview | The preview panel is a **tile script** (`0x80108924`: tile ids, row moves, attribute), one per character, from the table at `0x8016FA84`. The panel function `0x8013B0E8` picks it at `0x8013B15C`; `xp_zpv` returns Zangief's own script for character 10 + bit. His tiles are the free 40×24 block at (152,152) of the preview page (`FIRST.EMI`/`FIRSTE.EMI` 0x9D800), drawn by `tools/previews.py --chars …,11` from Dan's block plus the Siberian Bear pattern. |
| Drop pattern | Pattern lookup `0x801350E4`: `xp_patchar` points it at `XP_ZPATTERN` for Zangief. |
| Damage | `xp_zchar` gives index 11 in `DMGTAB` (send 90 %, receive 90 %); `tools/model.py` knows it. |

**Checks.**
- Select: the cycle and the Up walk-back, both players; the label and the preview (red/blue over green/yellow).
- Arcade: Down from Anita goes to the cell character; the bit stays 0.
- A Versus match Zangief vs Mei-Ling: the pattern comes from his table, and the damage fuzz matches the model 120/120 with Zangief on both sides.
- Full regression: passes (damage 150/150).

**Still Dan's until later steps:** the select portrait (step 5), in-match sprites (3), voices (4), stage and music (6). The RESULT screen counts him as Dan.

## Step 3 research: how a character is animated in a match

- The character object (P1 `0x801D4E9C` in a Versus match) holds an **animation script pointer at +0x28** and a frame timer at +0x12. The draw code (`0x8010C800`) reads the frame index at script +4 and draws record `index` of the player's frame bank (P1 `0x800E7600`), through `0x8010CC48`.
- **Script entry**, 16 bytes: `u16 duration, u16 flags, s16 frame, s16 jump, ...`. Flag `0x8000` jumps by `jump` entries (loops); duration 4095 means "hold". Ticker: `0x80136680`; set script: `0x80136554`.
- **States.** `0x8016EEC4` holds one list of script pointers per character (0–10), indexed by a state id. `0x801364AC (obj, state)` / `0x80136400` start a state. Dan's list has 51 entries, many of them the same idle script; states 23/24 are the select-screen poses.
- **Attacks** are per-character code: two tables of 11 routines at `0x8016F178` and `0x8016F1A4` (Dan: `0x80149188`, `0x8014971C`). They start states and play voices (`0x80105C4C`); projectiles and effects use a third, shared frame bank (`0x800F19C8`).
- The scripts live in the EXE; the frame indices point into the character file's records (Dan uses records 199–251 of `PL9A`, after Akuma's).

So Zangief can keep Dan's state machine and attack code, with his own list of scripts and his own frame bank. Effects that Dan's attacks spawn (Gadoken) must be suppressed or replaced for him.

## Pocket Fighter animation data

- The character object (Zangief as P1 in a training match: `0x801E1DA8`) holds the current frame at +0x46, the current animation entry at +0x1C and the base of the character's animation array at +0x48. The array comes from the character's `MDL` overlay (Zangief: `0x8016265C`, 1023 entries).
- **Entry**, 24 bytes: `u16 duration, s16 flags, s16 jump, u16 frame, ...`. A negative flag ends the animation and jumps to entry `jump` (a loop or the next state). Step: `0x801A6EB0`; set entry: `0x801A6D88`.
- Splitting at the jumps gives **144 animations** for Zangief (stance, walk, normals, Double Lariat, Spinning Piledriver, costume moves, bear, hits, knock-downs, wins…).
- **Costume overlays.** A frame record with flag bit 0 is drawn with the **next** record on top, each at its own anchor. The bear, worker, cook and other costume frames come in pairs (odd = body, even = costume). Drawing a body frame alone shows Zangief without his costume, and the costume frame alone shows the skin without Zangief.
- **Anchors.** Record `x, y` is the origin inside the frame, at the feet. Jumps (the Piledriver) are object movement, not anchors, so airborne frames need a vertical offset baked in when converted.

## Step 3: in-match sprites and animations (done)

**Build.** `XP_PF=<Pocket Fighter image> ./build.sh …` runs `tools/zangief.py`, which writes `PL0B_OBJ.EMI` (new file id 0x56) from `/PLAYER/ZANGIEF.PAC` and `/MDL/PL09A.MDL` on the user's disc.
- Frames: Pocket Fighter records composited with their costume overlay, kept facing left (the game mirrors P1), scaled to 0.65 around the feet, quantised to one 15-colour palette. 42 frames, 0xEAA0 bytes of graphics. The Piledriver frames get a vertical lift.
- Record entry, loaded at the player's bank (P1 `0x800E7600`, P2 `0x800EBB00`): 44-byte records, then at +0x2C00 the palette block (4 colour sets × 4 palettes: Zangief + Dan's 3 effect palettes), then at +0x2E00 the 51 state offsets and the 16-byte scripts.
- Colour sets follow the confirm button like the others: set 1 (X) is the original red, then blue, green and dark. A Zangief facing Dan or another Zangief in P2 gets the alternate set, as for any same-slot match-up.

**Hooks** (`src/zangief.asm`, code at `0x80151AC0`, an unreferenced 440-byte function that never runs; installed only when the build has the file):

| Where | What |
|---|---|
| `0x8010BB1C` (character file load) | Zangief loads file 0x56 with its own "loaded file" cache value (11), so switching Dan ↔ Zangief reloads. |
| `0x80136430`, `0x801364DC` (start a state) | Zangief's scripts from his bank (states 23/24, the select-screen poses, stay Dan's). |
| `0x80136860` (palette upload, `0x80136824`) | Zangief's palette block from his bank. |

**States** (Dan's 51, the logic stays Dan's): idle 0–2 and 37/43–50; win entry 3 and random win poses 4/31–34 (table `0x80171C20`); lose 5/30/38; reaction to an incoming attack 6/7/8 = 6 + strength (`0x801355EC`); attacks 10–13 = 10 + level; super 14. The scripts carry no effect events, so Dan's Gadoken is not thrown.

**Correction.** Dan's states 7/8 (frames 201/202, arms up) are his reaction to being hit, not a taunt. SPF2T has no taunt; Zangief's provocation pose is among his random win poses (31, 34) instead.

**Checks** (`XP_PF` build):
- Versus Zangief vs Mei-Ling: idle, attacks (punch, Piledriver seen in play), super (bear, burst, pose), hit reactions, K.O. and win, all in game.
- Zangief vs Zangief, Dan vs Zangief, Zangief vs Akuma: both sprites and palettes correct.
- After a match, the loser switching from Zangief to Dan gets Dan's graphics again.
- Damage fuzz 120/120 with Zangief; full regression passes on the `XP_PF` build and on the plain build (which also reproduces `xprime-patch.json`).

## Step 4: voices (done)

**SPF2T voice bank** (`SE_PLxx.EMI`, file ids `0x3E + n`): 3 entries.
- Entry 0: the sound id table, 8 bytes per id. Byte 3 is the program; the high nibble of byte 5 is the tone. Ids 0–23 are the 24 samples; 25–33 replay some of them with other parameters.
- Entry 1: the VAB header (Dan: 2 programs, 24 tones, 11.025 kHz samples: note = 48 + n, center = note + 24).
- Entry 2: the VAG body.

The loader is `0x801058D0 (player)`. It keeps a per-player cache byte (`0x801BF118/9`), and its value 11 means "none loaded". Voices are played through `0x80105C4C`, with flag 1 for P1's bank and 0x42 for P2's.

**Dan's voice ids in play** (traced): 30–33 come with the attack states (30 also starts the super), 19/20 with the hit reaction (state 6), 27 when the opponent is knocked out, 28 after the win, 23 for the lose, and 4–7, 10 and 13 during play.

**Pocket Fighter.** Character n's voices are in `/SE/SE(n+1)A.PAC` (Zangief: `SE0AA.PAC`; B is the same for P2, C adds the costume voices). PAC entries:
- a 256 × 4-byte sound table (byte 1 = program, high nibble of byte 2 = tone);
- the VAB header: 3 programs, 31 VAGs, 8 kHz (note + 30 = center, shift 57);
- the VAG body.

Sound codes `0xAxx` in his animations name voices: 0x16 is the Double Lariat shout (VAG 23), 0x14 his taunt (VAG 21), 0x1C the special (VAG 29), and 0x33/0x1D the bear (VAGs 17/30). VAGs never used by an animation (4, 7–13, 31) are played by code: hits, K.O., win.

**Build.** `zangief.py voices` writes `SE_PL0B.EMI` (new file id 0x57). It is Dan's layout with Zangief's VAGs copied raw into Dan's 24 slots (`VOICE_MAP`); each tone gets center = note + 30 and shift 57, so the 8 kHz samples play at their own pitch. The hook at `0x8010594C` (`xp_zse`, code at `0x8015C550`, an unreferenced 380-byte function that never runs) loads it for Zangief, with cache value 0x20.

**Checks.**
- In a Zangief match his bank is resident in SPU RAM (all 56 sampled chunks of `SE_PL0B`, none of Dan's).
- The captured match audio matches his samples at the moments the game plays ids 31 and 32 (correlation 0.48 and 0.74).
- After switching Zangief → Dan, Dan's bank is back.
- Damage fuzz 120/120; full regression passes; the plain build still reproduces `xprime-patch.json`.

**Open.** Some slot roles are guesses (the samples cannot be listened to here); `VOICE_MAP` is one table to adjust by ear.
