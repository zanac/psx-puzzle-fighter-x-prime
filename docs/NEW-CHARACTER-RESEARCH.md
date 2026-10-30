# Zangief port: step 0 research

> **Note (step 8).** Builds always need Pocket Fighter now (`./build.sh <SPF2T> <Pocket Fighter> <output> [armips]`). The `XP_PF` variable, the `ZG_HAVE` switch and the "plain build" below belong to the history of steps 0–7.


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
- There are only 9 stages for 12 characters, so some characters share one. Zangief's is the castle, `ST06` (Moonlight Dark Castle). Both formats are described under step 6.

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
- Colour sets follow the confirm button like the others: set 0 (Circle / Triangle, the standard colours for every character) is the original red, set 1 (Cross / Square) blue, then green and dark. (Before experimental-arcade set 1 was the red one, so he was the only character whose standard button gave the alternate colours.) A Zangief facing another Zangief gets the alternate set, as for any mirror match; facing Dan (the same slot) he no longer does (xp_samechar).

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

## Fixes after the first videos

- **Round 2 sprite.** Between rounds, `0x80107430` re-uploads both players' palettes straight from the player structs (character + 0x6D colour set). Zangief got Dan's palette there. `xp_zpal2` wraps its two `jal 0x80108C68` calls.
- **Missing voices (super, K.O., win, raised hands).** These are script cues, not code. Script byte 11 is a voice index: `0x80136554` plays entry byte11 − 1 of the character's voice table at `0x8016EFFC`. `tools/zangief.py` now reads Dan's scripts from the EXE and puts each cue (and flag bit 0) on the Zangief entry playing at the same moment. A looping body is unrolled up to the last cue, so a cue never repeats unless Dan's does. Win sequence now: 30 (super), 27 (K.O.), 28 (win), 29, and the win pose's own voice.

## Second round of fixes

- **Pinch states.** States 1 and 2 are the "in trouble" idles: Dan uses his normal idle there, the other characters do not. Zangief: state 1 struggles (Pocket Fighter animation at entry 195, frames 94–96), state 2 cries out (frames 485/486).
- **Hit pose too short.** The game puts the reaction state (6/7) back to idle after about 6 frames. When Zangief goes from a hit script back to state 0–2, `xp_zstate` now returns a short "hit tail" instead: the hit frame for 14 frames, then a jump into that idle. The record entry lists the tails (offsets 51–53) and the hit-script range (54–55); `LISTOFF` moved to 0x2F00.
- **One-frame glitch.** Three more palette uploads: `0x8013688C` (from the player struct; now through `xp_zpal2`) and the burnt / frozen special palettes `0x80136908` / `0x80136990` (per-character tables at `0x800F9A40` / `0x800F9AA0` + `0x8016EFA0[char]`). `xp_zpal3` (code at `0x80155008`) points those at Zangief's versions: Dan's special palettes remapped to Zangief's colours by brightness, stored at bank + PALOFF + 0x200.
- **Spinning Piledriver.** It is attack levels 2–3 (states 12/13 = 10 + strength), which only big attacks reach. Random test play rarely gets there, so the demo video forces each state.

## "In trouble" voices

No SPF2T character has a voice on states 1/2. Zangief now gets one, through the voice cue mechanism:
- Dan's voice table (`0x8016EFF4`, 8 bytes: ids 25–30 for indices 1–6, then two unused zeros) gets ids 14/15 at indices 7/8. Dan's scripts never use 7/8.
- Slots 15/16 (ids 14/15, never seen played) hold Zangief VAGs 07 (state 1) and 06 (state 2), as chosen by ear.
- The cue sits on a first entry before the loop.
- `xp_zstate` skips it (starts one entry later) unless the current script is his idle 0 or pinch 1 (range at list offsets 56–57). So he cries when he gets into trouble or worse, not after every hit or attack. The hit tails for states 1/2 also jump past the cue.

Correction to the voice roles: Dan's script cues use voice-table indices 1–6 = ids 25–30, so slots 1, 2 and 8 are also attack / super voices (states 11, 13, 12, 14), not only "unclear" or "opponent K.O.".

The current voice assignment, slot by slot, is in [ZANGIEF-VOICES.md](ZANGIEF-VOICES.md).

## Step 5: select, VS and win screens (done)

Everything below is only active in Versus with Zangief's bit set, and only in builds made with `XP_PF`.

### Big portrait (select and VS)

- **How the game draws it.** A portrait is a set of "child" sprites (0x1C-byte objects at `0x801B5C64`, drawn by `0x8010CA04`). They are created by `0x80123BAC` from a per-character list: table `0x8018B66C`, entries of u16 count, then (frame, palette, x, y). Dan's list is entry 20 at `0x80189F24` (frames 143–146 of FIRST.EMI, palettes 0–3). The children take the parent's graphics and record banks.
- **Palettes.** `0x8010773C(side, character, row)` copies 10 palettes from FIRST.EMI to the side's portrait slots (P1 slot 0x30 = palettes 0x23.., P2 slot 0xD0 = 0x2D..). Row 0 is the select screen, row 1 the VS screen. Palette 3 of a side is rewritten by the game, so Zangief's quadrants use palettes 0, 1, 2 and 4.
- **Both screens use the same list.**
- **Zangief's art.** Pocket Fighter `/STAGE/SELECT.PAC` frame 554 (palettes from 586, one per cell palette offset), mirrored to face right.
  - Select: a close-up (scale 0.55, face and fists), placed in the part of the 128×112 box the screen shows.
  - VS: the whole art (scale 0.5).
  - Each portrait is 4 quadrant records with their own 15-colour palette (k-means quantisation).
- **Where it lives.** A block at the start of his graphics entry (`tools/zangief.py` `build_portraits`): two lists, two palette rows of 10, and 8 records. The record bank is full, and record offsets are relative to the graphics entry anyway.
- **Hooks.**
  - `xp_zlist` at `0x80123BF0`: Dan's list becomes his select or VS list.
  - `xp_zkid` at `0x80123C34`: the children take his banks.
  - `xp_zportpal` at `0x8010773C`: his palettes.
  - `xp_zport` finds the banks holding his file and tells the screens apart: on the select screen a "loaded file" cache byte is 0xFF; on the VS screen MODE = 3 and MODE_NEXT = 0.

### His file on the select screen

- **When it loads.** The select screen has no data of his. In Versus his file is loaded into the banks SELECT.EMI did not take, right after SELECT.EMI: `xp_zselload` at `0x8012BF7C` queues it.
- **Waiting for it.** Loads are asynchronous: `0x801043C0` starts a load, `0x8010436C` runs it once a frame, and `0x80104354` says "busy". The select scene waits for the loader at `0x80128768`, and `xp_zselbusy` (replacing that call) starts his load once SELECT.EMI is in and reports busy until it is done.
- **Cache byte and load destinations.** His cache byte is set to group 11, so the match load skips it or redoes it as usual. The load destinations `0x801B8180/84` are put back afterwards.
- **Why the wait is needed.** Starting the second load while the first one is running corrupts SELECT.EMI.

### Select-screen chibi

- **How the game draws it.** States 23 (choosing) and 24 (chosen) start through `0x80136400`, which picks SELECT.EMI's banks (`0x80123960`).
- **Zangief's chibi.**
  - `xp_zselst` gives him his own state 23/24 scripts from his file (23 = stance, 24 = arms up).
  - `xp_zselbank` (at `0x8013648C`) gives him his banks.
  - `xp_zchibipal` (at `0x8010789C`) gives him his palette, colour set as chosen.
  - While the cursor is on him, his own colours are shown (set 0). The cursor-move call is told apart by its return address, `xp_mv_ret`.

### Names

- **Select label:** already done in step 2 (label 0x40).
- **VS label:** the same setter as the select label. `xp_labelkey2` now also accepts MODE = 3 with MODE_NEXT = 0.
- **Match HUD.** Four 16×16 sprites per player, built once by `0x8014CD50` from a 256×256 4bpp page (FIRST.EMI entry 25, VRAM 960,0).
  - Layout: P1 names are left-aligned at u 128–191, P2 names right-aligned at u 192–255, and the row comes from table `0x8018BF38`.
  - Space: the page has no free 64×16 block, so ZANGIEF replaces MORRIGAN's P2 copy (row 48). P2 Morrigan reads her P1 copy (one pixel of alignment difference). Hooks: `xp_zhud1/2` at `0x8014CE38/60`.
  - Art: the name is built from the other names' letters plus a hand-drawn Z (`tools/labels.py` `put_hud_name`).
- **Name call on confirm.**
  - The voice comes from `0x8013CB88(character, side)` through table `0x8016FED4` (Dan = id 0x1A), out of SELECT.EMI's sound bank.
  - Ids 0x14 and 0x19 are never used by the US game. Id 0x14 (program 1, tone 20, VAG 13) gets Pocket Fighter's "Zangief!" (`/SE/SE0D.PAC` VAG 4), resampled to fit VAG 13 (nothing moves, tone centre 79). Built by `tools/zangief.py name`, which uses the ADPCM encoder in `tools/vab.py`.
  - `xp_zname` picks id 0x14.

### WINNER screen

- **What the game draws.** The WINNER screen draws, from the winner's own record bank:
  - one of four win quotes: frames 239–242, text strips with two lines of 8×16 text;
  - a small icon: frame 246.
- **Dan's effect frames.** Dan's file also has effect frames 243–245.
- **The bug this caused.** Zangief's file had about 70 frames. The higher indices were zero records pointing at graphics offset 0, which became the portrait block after this step. The game then decoded the block as LZ, and the match ending crashed (and the K.O. effect was missing).
- **The fix.** Every index up to 246 is now valid: an empty record where he has nothing, his own quotes and icon where the screen needs them.
- **Quotes.** Zangief's own four Pocket Fighter win quotes. At build time they are decoded from the user's `MDL/SELMES.MDL` (`pf_win_quotes`, using `tools/pf_texts.py`).
  - **Font.** The letters are taken from every character's SPF2T quote frames (`QUOTE_SOURCES`: PL00–PL08 and PL9A). The transcriptions are checked against the glyph cells: a 1-line quote is drawn at y 8.
  - **Hand-drawn glyph.** The closing double quote is missing from SPF2T and is drawn by hand (`EXTRA_GLYPHS`).
  - **Without `XP_PF`.** The old stand-in quotes stay.
- **Icon palette.** The icon is drawn with Dan's body palette (Dan's own path at `0x80110088`). `xp_zwinpal` loads palette 0 of Zangief's colour set instead.
- **RESULT table.** As agreed at the time, his wins counted as Dan's on the RESULT table (superseded: see "Select screen icons and RESULT").

### Code space

New never-run, unreferenced functions:
- `0x80152C14` (332 bytes);
- `0x8015515C`–`0x801554C4` (three functions, 872 bytes);
- `0x80153AF4` (236 bytes; first `0x8013BBB4` was used, see the correction below).

All are checked with coverage over boot, menus, Versus select, VS and a match. Since the correction below, they are also checked over a whole Arcade run with its ending, Street Puzzle and the option menus.

## Step 6: stage and music (done)

Zangief has his own Versus stage: Pocket Fighter's castle, with its music. It is index 11. Index 10 stays Dan's (Ken's picture, Dan's music).

### SPF2T stage file (`DATA/STAGEnn.EMI`, 36 sectors)

An EMI with 5 entries. For each entry the header holds the size, the parameters and **the first 4 bytes of the entry's data**. The loader checks those 4 bytes: if they do not match, the load never ends and the game hangs on the VS screen.

| Entry | Size | Content |
|---|---|---|
| 0 | 0x8000 | VRAM page (768, 256): 256 tiles of 16×16, 4bpp, 16 per row |
| 1 | 0x8000 | VRAM page (832, 256): 64×64 rock texture of the well frames (top left) |
| 2 | 0x300 | tile map, 24 × 16 halfwords: tile (bits 0–7) \| palette << 8 |
| 3 | 0x400 | 32 palettes, bank 1 (`0x801A0A2C`) |
| 4 | 0x400 | 32 palettes, bank 2 |

- **Picture.** Rows 0–5 of the map are the 384×96 picture the match shows. It is placed at x −10, y 80 and seen through the middle area and, dimmed, the wells. Tests with a numbered grid showed nothing of rows 6–15 in a match.
- **Reserved palettes.** Bank-1 palette 15 is the frame rock's palette (no stage uses 15 in its picture). The stages use at most 0–28.
- **Entry 2 on load.** It goes to `0x800F5600`. `0x80108CF4` / `0x80108D2C` copy it to `0x8019FEB8` and `0x801A01B8`.

### Stage tables and readers

`STAGE_IDX` (`0x8019FC98`, halfword) has only five readers (watched over a full match):

| Reader | Table | Role |
|---|---|---|
| `0x80107944` | `0x80166728` | load function |
| `0x801079DC` | `0x80166754` | set-up function |
| `0x80107A50` | `0x80166780` | per-frame function |
| `0x8010EDD8` | `0x8016A29C` | stage object list |
| `0x8012BE54` | `0x8016D474` | song (halfwords) |

- Each table has 11 entries, with no room for a 12th.
- They are copied with entry 11 added (Zangief's load function, then Ken's set-up, per-frame and empty object list), and the five readers are repointed.
- The "loaded stage" cache is `0x801BF114`.

### XA music

- **Call.** `0x80106284(cmd, song)` → `0x801062F4`.
- **Song to entry.** entry = `0x8016621C[song]`, or `[song + 24]` with the arranged music.
- **Entry fields:**
  - `0x8016615C[entry]` (4 bytes per entry; the halfword holds file index << 8 | channel);
  - file id = `0x80166060[file index]` (halfwords: 5–10 = `STR/ORG00–02`, `QSD00–02`);
  - `0x8016606C[entry]`: length in sectors per channel, top bit = loop;
  - `0x8016612C[entry]`: volume.
- **Playback.** Start = file LBA + channel, end = start + 8 × length.
- **SPF2T's XA format.** The same as Pocket Fighter's: 8 interleaved channels, one song each, stereo 37.8 kHz, file number 1.
- **Free slot.** All 48 song ids are used: 0–23 are songs, 24–47 their arranged versions, and song 23 maps to entry 11 in both cases. **Entry 47** is unused.
- **Zangief's song.**
  - It is song id 47. `xp_songent` returns entry 47 for it, original or arranged.
  - Entry 47 is set to file index `0xDD` and channel 6. Its file id is read from `0x80166060 + 2 × 0xDD` = `0x8016621A`, the unused upper half of entry 47 itself.
  - Its length is 3376 sectors, looped.

### Pocket Fighter stage file (`STAGE/STnn.PAC`)

- **Type 5:** palettes.
- **Type 6:** tile map in blocks of 16×16 entries (256×256 px), row-major. Entry: tile = bits 0–10, palette = bits 11–15 plus the layer's base.
- **Type 257:** 16×16 4bpp tiles.
- **Types 0, 1, 264:** stage sprites (the witch silhouette, for example).
- **ST06 in a match.** The match shows three layers, two blocks each, side by side:
  - sky and moon: blocks 12–13, palette base 64, y −10;
  - floating castle: blocks 2–3, base 0, y −9;
  - statue, steps and wagon: blocks 6–7, base 32, y −8.
- **How the layout was found.** It was read from the game's display list in RAM: 16×16 sprite packets (GP0 `0x7C`), each tile and CLUT matched back to the PAC.

### Pocket Fighter music

`KYOKU/XA00.XA` (LBA 201): channel n is the music of stage n. The castle's is channel 6: 3376 sectors, about 3 minutes.

### Build (`tools/pf_stage.py`)

- **Picture.**
  - The three layers are composed (512×256), scaled to 75 % and cropped at y 36. This is the crop with the floating castle's islands, chosen by the user.
  - Quantised to 28 palettes of 16 colours (k-means), 144 tiles.
  - Written over Ken's stage file. The frame rock texture is kept, with its palette recoloured lilac (chosen by the user).
- **Music.** Pocket Fighter's XA00 is copied sector by sector up to the last sector of channel 6, with the other channels zeroed and silent sectors up to the player's end. That is 27,022 sectors (about 63 MB on the disc, mostly silence).
- **New files.** `ZG_STAGE.EMI` (id 0x58) and `ZG_MUSIC.XA` (id 0x59).
- **`tools/discexpand.py`.** It writes a `*.XA` file as raw Form 2 sectors, with 16 empty data sectors before it.

### Selector

- **NORMAL.** Zangief as P1 plays on his stage.
- **Fixed entry.** ZANGIEF is a fixed entry after AKUMA.
- **RANDOM.** Zangief's stage has 1 ticket in 11. With a Zangief in the match it has 3 in 13 (`xp_zstg_tickets`). The previous stage is still never repeated.
- **Without `XP_PF`.** There is no 11th stage: the code is assembled out (`ZG_HAVE`).

### Bug found on the way

`xp_zstg_load` first ended with `lw ra` directly followed by `jr ra`. On the R3000 the loaded value is not available to the next instruction, so the function returned to the old `ra` (its own `jal`). That started the load twice, and the VS screen hung. The fix is an instruction between the two.

### Code space

- **New space:** the rest of `0x80163CDC` (tables and the load function).
- **Moved:** `xp_done` and `xp_notdone`, to the X' area at `0x80134D80`, to make room for `xp_stage`.

## Pocket Fighter texts (win quotes, rival dialogue, Arcade story)

All of them are decoded from the user's disc by `tools/pf_texts.py` (Markdown output). The repository stores no text and no glyph data: only, for each glyph strip, the letter of each index.

### Encoding

- **Not ASCII.** Each byte is an index into a strip of 16×16 4bpp glyphs (128 bytes each).
  - 0 is a space; 1 and 2 are the "more text" prompt icons.
  - Each strip has its own order: the order in which its letters first appear in its texts.
- **How it was found.** A line on screen was searched for in RAM by its letter-repetition pattern, then looked up in the files.

### Where the texts are

| Texts | File | Glyph strip |
|---|---|---|
| Win quotes | `MDL/SELMES.MDL` from offset 4: lines of `0x80 \| length` + glyphs, two lines per quote, padding bytes (< 0x80) between lines | `STAGE/SELECT.PAC`, first entry (60 glyphs, shared) |
| Rival dialogue (the Arcade "special" opponent) | `MDL/PLxxA.MDL`, the last 4 messages | `PLAYER/BMESxx.PAC` |
| Arcade story: opening, then ending | `MDL/ENDING.MDL`, every character in order (the tool has each one's start offset) | `STAGE/OPENxx.PAC` type 269 (= `ENDxx.PAC` type 270) |

- **Win quotes.** There are 4 per character, in character order (48 quotes), followed by the gameplay tips shown on the CONTINUE screen.
- **Message format.** Rival dialogue and story messages are (length, glyphs). The length is a multiple of 38: one line is 38 characters, padded with spaces.
- **Character order:** Ryu, Ken, Chun-Li, Sakura, Morrigan, Hsien-Ko, Felicia, Tessa, Ibuki, Zangief, Dan, Akuma (`xx` = 00–0B).
- **Loss quotes.** Pocket Fighter has none. The loser gets the CONTINUE screen, with a gameplay tip.

### Zangief's Arcade mode (for a later Arcade Zangief in SPF2T)

Seen in the emulator with a forced win in every match. The RAM pokes are below; they are test aids, not part of the build.

- **Opening.** 4 messages, in an airplane: his superior sends him to invite Felicia.
- **Rival.** Felicia, with 4 lines of dialogue before the fight (`PL09A.MDL`), on her stage.
- **Ending.** 9 messages, in three scenes plus a black screen:
  1. Felicia gives in, on her stage.
  2. Felicia on stage in Russia.
  3. A black screen with text.
  4. Zangief with his superior, on a blue background.
- **Graphics.** The scenes are in `STAGE/END09.PAC`:
  - type 36: tiles;
  - type 37: tile map (8 blocks of 16×16);
  - types 15/16/17/267: a large sprite set (the characters' close-ups);
  - types 38/39: extra sprites;
  - type 270: the text glyphs.

  `OPEN09.PAC` has the same layout for the opening. Composing the scenes (layers, palettes) still needs the display-list tracing used for the castle.
- **Test aids** (Pocket Fighter RAM, in a match):
  - round timer: `0x801E0099` (decimal) / `0x801E0098` (BCD);
  - P1 vitality: `0x801E1DF8` (max at `+2`, 144);
  - P2 vitality: `0x801E20E0` (player block stride `0x2E8`).

  Setting P2's vitality to 1 and the timer to 1 wins every round by time over.

## Correction: Arcade hang (step 5 code space)

- **The bug.** From step 5 on, Arcade hung after the first match won, while loading the next opponent. Builds without `XP_PF` were not affected.
- **The cause.** The step-5 code area `0x8013BBB4` (308 bytes) was taken for an unreferenced, never-run function. Only its first 36 bytes are that. From `0x8013BBD8` on, it is a function that `0x8013BCC8` calls, and the Arcade runs it between matches. The coverage then covered Versus only, so it missed it.
- **The fix.**
  - The select-chibi code (`xp_zselst`, `xp_zselbank`, `xp_zchibipal`) moves to `0x80153AF4` (236 bytes, no references).
  - Coverage was redone on the original disc over a whole Arcade run (10 opponents, ending, staff roll), Street Puzzle and the option menus. None of the code areas this project uses runs there.
- **New regression check.** `tools/regress.py` now plays Arcade with P1 winning every match. It must reach 4 different opponents (`arcade_ok`).
- **Original Arcade order with Ryu,** as seen in that run: Morrigan, Sakura, Hsien-Ko, Ken, Felicia, Chun-Li, Donovan, Ryu, Dan, Akuma (the opponents vary with the random seed).

## Step 7: Arcade

### How the Arcade works (original game)

- **Level select.** It comes before the character select: EASY, NORMAL ("8 stages") or HARD.
- **Opponent order.**
  - `0x8012CD18` copies 16 bytes from `0x8016D49C + [state + 0x37]` to `0x8019F45C`. There are 8 rows: each lists the 8 regular characters (the player's own included: there is a mirror match), then Dan (10).
  - It may then put Devilot (8) or Dan in place 6 (flags at state `+0x45` / `+0x47`) and Akuma (9) in place 8 (`+0x46`).
  - The next opponent is the first one of the list that is not in the beaten mask (state `+0x10`). It is chosen by `0x8012CBCC` (first match, char stored at `0x8012CCD4`) or by the next-opponent code (stored in the delay slot of `0x8012CEB8`). Both then call `0x8012CDBC` with a2 = the CPU's player struct.
- **Modes.**
  - Arcade and Street Puzzle are both `MODE` 1 in a match; `0x8019C3F5` is 1 in Street Puzzle.
  - On the select screen `MODE_NEXT` is 1 for both, and 3 in Versus.
  - Player struct `+0x6C` is 1 for a CPU player.
- **Ending.**
  - After the last win comes a staff roll: the player's character stands beside the credits, alternating with wordless vignettes of chibi characters.
  - The vignette set is one of `ENDING00`–`03.EMI` (file ids `0x12`–`0x15`), chosen at random: `0x801247B4() & 3` → `0x8019377E` → table `0x8017173C`. It is loaded over the P1 sprite banks (`0x80024000` / `0x80035000`).
  - Each file has 9 sprite sets (graphics + 44-byte records, as `PLxx_OBJ`): 8 sets of characters, and one of large pieces (the staff-roll figures).
  - There are no story texts.
  - **Levels.** `0x801BAACF` holds the level chosen in LEVEL SELECT: 0 EASY, 1 NORMAL, 2 HARD. The three cases were checked by playing them through on the original game:
    - EASY has 3 stages, then GAME OVER with "TRY NORMAL LEVEL!": no ending.
    - NORMAL ends with the staff roll, then "THANK YOU FOR PLAYING / PRESENTED BY CAPCOM" on black.
    - HARD has the same staff roll, then the extra ending:
      - after the last credits page, state `+0x18` goes to 10 instead of 12 (`0x80143D94`; any level other than NORMAL);
      - `0x80143FC4` → `0x80144638` loads `HARD_END.EMI` (file `0x18`) over the P1 sprite banks and plays song 4;
      - on the "THANK YOU" screen the whole cast (the 12 characters) walks in and gathers under the CAPCOM logo;
      - then GAME OVER.
- **Gallery.** `IMG00`–`IMG20.EMI` are TIM images (8bpp): the gallery (title art, flyers, character art). They are not endings.

### Changes

- **Mode tests.**
  - `xp_frame` runs every frame, hooked on the main loop's call of the loader step at `0x80102458`.
  - It sets `XP_ZOK` / `XP_ZOKN` to 3 when `MODE` / `MODE_NEXT` is Versus or Arcade (Street Puzzle excluded).
  - All the Zangief tests read these bytes instead of the mode, so they hold in Arcade too: selection, sprites, voices, portraits, HUD, WINNER screen and damage.
- **CPU challenger.** `xp_zopp1` / `xp_zopp2` → `xp_zcpu` sets the CPU struct's Zangief bit:
  - when the opponent is Dan, one time in two (bit 0 of root counter 0);
  - not when the player is Zangief;
  - only for a CPU player (`+0x6C`).

  Any other opponent clears the bit. The castle stage follows (`xp_stage`'s Arcade path).
- **His order.** `xp_zorder` is hooked on the `jr ra` of `0x8012CD18`. When a player is Zangief, it swaps Felicia (6) into place 7 of the list: the 8th opponent.
- **Code space.** `0x8010868C`–`0x80108924`: six unreferenced functions that never run. This was checked against:
  - a static reference scan (`jal` / `j` / branches from outside, data pointers, `lui` + `addiu` / `ori` pairs);
  - coverage over Versus, a whole Arcade run, Street Puzzle, options and the demo;
  - a scan of the `DATA` files for pointers.
- **Tests.** `tools/regress.py`:
  - `arcade_ok`: Ryu's Arcade reaches 4 opponents;
  - `arcade_z_ok`: Zangief's whole run on HARD, with Felicia 8th, then Dan and the bosses;
  - `staff_z_ok`: his staff roll figure comes from his block;
  - `hard_z_ok`: he is the 13th object of the HARD finale, drawn from his own file.

### Staff roll figure

- **How the game draws it.** The staff roll's figure set-up is `0x801102D8`; the character is read from `0x8019FCCD`.
  - **Dan (10):** a small single frame, record 45 of the figure banks (path `0x80110364`).
  - **Everyone else:** position (0x100, 0x80) and the portrait palettes (`0x8010773C` / `0x801077E0`). The script comes from `0x80189818[character]`, with the figure banks `0x800A1000` (graphics) and `0x800B1000` (records). The scripts are list mode (`0xC0000FFF`, then the list index: 252 + character) into the portrait list table `0x8018B66C`, so the figure is child sprites, like the select portraits.
  - **Where the banks come from.** Every `ENDINGnn.EMI` loads these banks as its last set (destinations 30 and 31 of `0x8017174C`), with the figures of every character.
  - **No animation.** The figure is static (Ryu: no pixel changes over 128 frames).
- **Zangief's figure.** It is the one picture of his Pocket Fighter Arcade opening: Zangief in a suit on the airplane, adjusting his glasses.
  - **Source format.** `/STAGE/OPEN09.PAC` holds the picture:
    - type 16: 14 frame records (u16 index, u8 columns, u8 rows, x, y, cells, flags), then one u16 per cell (column-major; `0xFFFF` = empty; tile = bits 0–10, palette = bits 11–15);
    - type 17: palettes;
    - type 267: uncompressed 16×16 4bpp tiles.

    Frame 0 is the scene's frame; frames 1 and 2 are the bust in its two poses, 240×128, cut at the bottom by the scene's frame.
  - **The file.** `tools/zangief.py build_end` writes `ZG_END.EMI` (file id `0x5A`). Its first entry is a block shaped like the select portrait block:
    - a list at +0;
    - `ZGND` at +0x7C;
    - 10 palettes at +0x80;
    - records at +0x300, then the LZ cells.

    The bust is split by its own Pocket Fighter palettes (exact colours, palette 3 avoided) into 7 pieces of at most 6×8 cells.
  - **Loading.** `xp_zendbusy` replaces the loader wait of ending state 0/1 (`0x80143A78`). Once the ENDING file is in and the human player is Zangief, it loads `ZG_END.EMI` over the figure banks; the other figures are not needed then.
  - **Set-up.** `xp_zendfig` (at `0x80110314`) sends him down the regular path and sets `XP_ZEND`. `xp_zendscr` (at `0x801103E8`) gives him a list-mode script with Dan's portrait list (20). The existing portrait hooks (`xp_zlist`, `xp_zkid`, `xp_zportpal` through `xp_zport`) then take the block at `0x800A1000` while `XP_ZEND` is set. `XP_ZEND` is cleared on the select screen and whenever the mode is neither Versus nor Arcade.
  - **Placement.** `END_POS`: the bust stands on the bottom edge and touches the right edge (the visible area ends at x ≈ 330, as for Ryu), so its cut sides are hidden.

### HARD finale

- **How the game builds it.** On HARD, after the staff roll, ending state 10 loads `HARD_END.EMI` over P1's banks.
  - **Spawning.** `0x8011F004` spawns 12 objects of type `0x41`, index 0–11.
  - **Init and tables.** The init is `0x8011ED04`. Per index it reads:
    - a delay before appearing, `0x8016C828`;
    - a draw priority and a facing, `0x8016C7B0` (lower priority = drawn in front);
    - x / y, `0x8016C7C8`;
    - a palette, `0x8016C840`, copied to bank 3 by `0x80108C68`;
    - a script, `0x8016C7F8`, with banks P1 hard-coded.
  - **Appearing.** The characters do not move. Each fades in (`0x80106D28`: palette brightness by bit mask) once its delay is over.
  - **Landing.** A common timer (`+0x1C` = 336 frames from spawning) triggers the landing script (`0x8016C880`; index 11 keeps its own).
  - **One-credit bonus.** Finishing on one credit adds a scrolling message ("YOU COMPLETED THE MASTER ARCADE MODE USING ONLY ONE CREDIT! YOU ARE THE SUPREME MASTER PUZZLE FIGHTER!", `0x80171618`, `0x80144484`).
- **Zangief as the 13th.** He is part of the cast now, so he appears whoever the player is.
  - **His file.** `xp_zhbusy` replaces the wait at `0x80144028`. After `HARD_END.EMI`, it loads his own `PL0B_OBJ.EMI` into what the ENDING file left in RAM, which nothing uses then (graphics `0x80070000`, records `0x80082000`).
  - **Spawning and init.** The spawner makes 13 objects. `xp_zhinit` (at `0x8011ED40`) gives index 12:
    - his idle script and his own colours (palette set 0, into bank 3 slot 12);
    - the back row's middle gap, under the logo (x 184);
    - priority 11 (behind everyone, as the back row's big man);
    - a delay of 260 frames: last, but his 42-frame fade-in must end before the 336-frame landing timer, or he never lands and stays half faded.
  - **Landing.** `xp_zhland` (at `0x8011EF78`) gives him his finale script when he lands (`zangief.py`: entry 58 of his script list). He flexes for about two seconds (8 × 14 frames), then holds still with his arms up.
  - **Coordinates.** His frames are in-match frames: the y of his feet on screen is about 256 − y, not y + 144 as for the `HARD_END` frames.
- **Code space.**
  - `0x801080BC`–`0x801082BC` and `0x80156360`–`0x801564B0`: functions with no references that never run. This was checked by coverage over the earlier runs plus a whole staff roll and HARD finale on the original disc.
  - The existing `0x8010868C` / `0x80153AF4` areas also stay unused there.

## Select screen icons and RESULT (branch experimental-arcade)

Zangief and Dan are no longer hidden: they get icons on the select screen,
and the Versus RESULT table lists them with separate counters. Code:
`src/select.asm` and `src/result.asm`; the icon picture is built by
`tools/zangief.py icon`.

### RESULT (0x80138864)

- **Counters.** 4 arrays × 11 words at 0x801D2678: wins side 0, wins side 1 (+0x2C), losses side 0 (+0x58), losses side 1 (+0x84); index = character. Zangief has his own 4 words (XP_ZST), updated instead of Dan's when his bit is set (xp_zinc, replacing the update at 0x801382B8).
- **Lines.** A 12th line, ZANGIEF; DAN and ZANGIEF are always shown, AKUMA and DEVILOT when unlocked (12-entry copies of the name, column and line tables). Totals go from row 19 to 20, the menu from rows 22/24/26 to 23/25/27.
- **Card block.** The save is one 0x400-byte block built at 0x80010000 (card frame 0x2000 in a fresh card: 0x200 of header and icon, then the game data). The counters are at +0x268 (44 words), copied back by 0x80104054, which also runs at boot (the game loads the card by itself).
- **Dan on the card.** Vanilla zeroes a secret character's counters before saving when it was only reached by its code this session (Dan: 0x80103F04, flag 0x8016CAFA clear, "used" 0x801BF120 set). Dan is listed like everyone now, so that step is skipped (0x80103F10 branches over it).
- **Tested in the emulator with a memory card** (pcsx_rearmed option `pcsx_rearmed_memcard1 = libretro`; lr.py has no card unless it is passed). Zangief beats Dan, then BACKUP → SAVE DATA. On a fresh boot with that card, ZANGIEF 1 / DAN 1 come back; one more match gives 2 / 2. `tools/cardtest.py` runs this test.
- **Save.** His counters go in the unused tail of the save block (+0x380: 'ZGST', 4 words, sum), written by xp_rssave and read back by xp_rsload; an older save gives zero. CLEAR RESULT clears them too.

### Icon grid

- **Objects.** The icons are type 0x17 objects, subtype = character 0–7, made by 0x8013C29C (8 calls to 0x80114260(subtype, mode)). Their init (0x80113F2C) reads per subtype a delay (0x8016A840), a position (0x8016A850, y counted upwards) and an animation (0x8016A870, through 0x8010B734). Subtypes 8 (Zangief) and 9 (Dan) are added when MODE_NEXT is Versus/Arcade, with 10-entry tables and their own 2-step scripts.
- **Tile lists.** 0x801667C4 + 0x94 × char: 9 tiles of the picture (u << 8 | v, x, y, attr; list y 0 is the bottom row), then 9 tiles of the white frame (icon 20 at 0,192, palette 11, navy inside), then 0xFFFF, 5. The picture's 0 pixels let the navy show.
- **Icon page.** FIRST.EMI / FIRSTE.EMI entry 25, VRAM (704,0), 48×48 icons, 5 per row: 0–9 characters, 10–17 Dan's gag variants, 18 "?", 19 frame fill, 20 frame. **All of Dan's variants are used** by his gag animation (scripts 0x80167B84–0x80167C5C; (96,144) is its last frame, held 0x782 frames). The right-hand strip x 240–255, y 0–191 is empty: 12 free tiles.
- **Zangief's icon.** Pocket Fighter /STAGE/SELECT.PAC frame 775 (3×3 cells, palette 634), found by matching its VRAM tiles against the decompressed cells. Its background and frame colours become transparent, it is clipped to the frame's inside and mapped to Dan's icon palette (10). It is written as 9 loose tiles in strip slots 0–8.
- **Dan's icon.** His laughing variant (0,96). Its ponytail crosses the frame's top edge, so its two top-right tiles are replaced by copies clipped to the frame's inside (strip slots 9–10).

### Cursor and screen

- **Positions.** 0–3 top row, 4–7 bottom row; 8 = Zangief, 9 = Dan. The cursor/badge position table 0x8016A974 is relocated with two more entries (read at 0x80116150, 0x8011618C, 0x801161B8). Position → character goes through a 10-entry copy of CURSOR_CHARS; position 8 also sets his bit.
- **Moves** (xp_move): Up on Chun-Li (1) / Sakura (2) → 8 / 9, only in Versus/Arcade; on 8/9, Down → 1/2, Left/Right swap.
- **Down ring.** In Versus/Arcade it becomes Devilot → Akuma → Mei-Ling → Anita → cell; Street Puzzle keeps Dan after Akuma.
- **Mirror colours.** Confirming the character the other player already has gives the second one the other colour set (0x8013B058). Dan and Zangief are both character 10, so xp_samechar (0x8013B05C) makes them count as different unless both are Zangief or both Dan.
- **Big portrait.** The portrait object (0x80114510) redraws only when the character differs from the one it shows (+0x58). Dan and Zangief are both character 10, so +0x58 now holds a key, character | 0x10 for Zangief.
- **Logo and timers.** The logo's tile script (0x8016FACC) goes from row 5 to row 2; row 1 would be cut by the top of the visible area, so for a little more room the whole grid (icons, cursors) is 4 pixels lower (GRID_DY). Arcade's STAGE n / FINAL STAGE scripts and digits move up by the same 3 rows, and their erase (0x8013CB38) covers rows 2–11. The select timers (0x8013C428 / 0x8013C4B4) move one column outwards.

### Code space

Functions with no references that never run (coverage: boot, menus, Versus
with RESULT, Arcade to the HARD finale, Street Puzzle, option menus):
0x801609C0, 0x80161170, 0x801653C0, 0x80163574, 0x80160FF4, 0x801618A4.

- **Overlap found.** A first placement at 0x80152CAC overlapped Zangief's step-5 area (0x80152C14, 332 bytes) and crashed Versus. There is no overlap check in armips across `.area` blocks, so any new area has to be checked against the existing ones.
