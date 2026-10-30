# Plan: Zangief from Pocket Fighter as a hidden character

Branch: `experimental/new-character`. Status: **step 0 (research) in progress**; findings in [NEW-CHARACTER-RESEARCH.md](NEW-CHARACTER-RESEARCH.md).

## Decisions (agreed)

- Only the NTSC-U Pocket Fighter (SLUS-00653) is supported.
- No Arcade and no ending: Zangief is **not selectable in Arcade**, only in Versus.
- **Option B** (alternate on an existing slot) is fine, provided it covers everything, his own stage background and music included.
- **Scale 0.65.** The in-match sprites are Pocket Fighter's frames at 65 % (stance about 68×53 px), which keeps his hands inside the middle area.

## Goal

1. Extract every Zangief asset from Pocket Fighter (PSX, NTSC-U, SLUS-00653):
   - sprites;
   - animations;
   - voices and sound effects;
   - music;
   - stage background;
   - portraits.
2. Make room on the Super Puzzle Fighter II Turbo disc and in its tables for these assets.
3. Add Zangief as a new hidden, playable character.

## Ground rules

- **No game data in the repository.** The build takes both discs as input, the SPF2T image and the user's own Pocket Fighter image. It extracts and converts Zangief's assets at build time. The data-free JSON patch cannot carry the assets, so `patch.sh` will also need the Pocket Fighter image.
- Every step ends with something that can be tested in the emulator, plus the full regression. The step is merged only when both pass.
- Pocket Fighter is chibi art in the same style as SPF2T, so the art fits as is. Scale and palette must still be checked; see step 0.

## What we know already (first look)

**Super Puzzle Fighter II Turbo (SLUS-00418).** All character data is per character, in `DATA/`:

| Asset | SPF2T file | Notes |
|---|---|---|
| In-match sprites | `PL00_OBJ.EMI` … `PL08_OBJ.EMI`, `PL9A_OBJ.EMI` | Each file has 2 entries: graphics, then data. Akuma and Dan share `PL9A`. The graphics are probably LZ, as in `FIRST.EMI` (`tools/lzh.py`). |
| Voices / SE | `SE_PL00.EMI` … `SE_PL0A.EMI` | Standard VAB (`pBAV`) inside the EMI. |
| VS / win portraits | `IMG00.EMI` … `IMG20.EMI` | Not mapped yet. |
| Select screen | `FIRST.EMI`, `SELECT.EMI` | We already redraw labels and previews there. |
| Stages | `STAGE00.EMI` … `STAGE09.EMI` | 36 sectors each; file ids `0x4A + n`. |
| Music | `STR/ORG00-02.XA`, `STR/QSD00-02.XA` | XA, probably original and arranged versions. |
| CD audio | tracks 2 and 3 | The EXE holds their LBAs (`0x80165E10`). |

- Files are loaded by index through the LBA table at `0x80165CC0`, not by name.
- The data track is almost full: about 150 free sectors before track 2.

**Pocket Fighter (SLUS-00653).**

| Asset | PF file | Notes |
|---|---|---|
| Sprites | `PLAYER/ZANGIEF.PAC` (488 KB), `ZANGIEFF.PAC` (702 KB) | `PAC` = count, total size, then (type, size) pairs. Type 0 looks compressed. `F` is probably the extra set (Mighty Combo / costumes). |
| Character code | `MDL/PLxxA/B/FA/FB.MDL` | MIPS overlays: move logic and animation scripts. |
| Voices / SE | `SE/SExxA/B/C.PAC` | Contain VAB (`pBAV` at `0x1000`), same family as SPF2T. |
| Music | `KYOKU/XA00-04.XA` | Multi-channel XA; Zangief's theme is one channel. |
| Stages | `STAGE/STxx.PAC` | Format to be found. |
| Portraits / select | `STAGE/SELECT.PAC`, `VSSEL.PAC`, `MDL/SELECT.MDL` | Format to be found. |

## The big design choice: new slot or alternate

**A. New character index 11.** The cleanest result: own stats, a RESULT screen row, Arcade, everything. It is also by far the most work and risk. Every per-character table in the EXE (patterns `11 × 0xC0`, damage, labels, portraits, stages, voices, AI, endings, names, RESULT rows…) must grow by one entry, and every `< 11` check must be found. The tables sit back to back, so most must be moved.

**B. "Alternate" on an existing slot**, the way the PSX version already does Mei-Ling (on Hsien-Ko) and Anita (on Donovan). The engine already swaps graphics and voices for an alternate; we would add a third. Zangief would take a slot such as Dan's, as an alternate reached by the Down cycle after Anita. Our own code (damage routine, patterns) can give him his own stats by testing the alternate bit. RESULT rows, Arcade order and ending would be the slot's.

**Recommendation.** Decide after step 0, once we know how Mei-Ling and Anita are wired. If the alternate path covers in-match graphics, voices, portraits and the label, B gives a usable Zangief in a fraction of the time. A can still follow later.

## Steps

### Step 0: research and extraction tools (game unchanged)

1. Pocket Fighter:
   - decode `PAC` and the sprite compression;
   - find the palettes and the animation scripts in `PLxx*.MDL`;
   - dump every Zangief frame to PNG, and each animation as a contact sheet with timings;
   - extract the VAB samples to WAV;
   - find Zangief's XA channel and his stage.
2. SPF2T:
   - map `PLxx_OBJ.EMI`: frame table, LZ graphics, palettes, animation scripts;
   - list the animation states a character needs (idle, attacks by chain size, Super / fever, hit, big hit, win, lose, and so on), and how projectiles and effects are drawn;
   - map `SE_PLxx` (which sample is which voice), `IMGxx` and stages;
   - find how Mei-Ling and Anita are implemented (choice A or B).
3. Measure:
   - Zangief's frame size against the SPF2T characters (scale);
   - the colour count (16-colour CLUTs?);
   - the RAM and VRAM budget of one character, including a mirror match (two Zangiefs).

*Deliverable:* `tools/pf_*.py` extractors, a frame/animation sheet of Zangief, WAV files on your side only, and a document with both formats and the A/B decision.

### Step 1: making room on the disc

- Rebuild the ISO with new files at the end of the data track: `PL0B_OBJ.EMI`, `SE_PL0B.EMI`, the portraits, a stage and a music file. Then move the CD-DA tracks after them and patch their LBAs in the EXE. The disc grows; CD and PBP limits are not an issue.
- Extend the file LBA table (move it if needed) so the new files get ids.
- Test with *dummy* new files: the game must behave exactly as before.

### Step 2: the slot (A or B)

- B: a third alternate, its bit, and the Down cycle (… Anita → Zangief → cell character, and back with Up).
- A: grow every per-character table and check.
- Both: label "ZANGIEF" on the select screen, a Counter Gem preview, a drop pattern, X' rates. Proposals for these will come for your approval, as was done for Dan.

### Step 3: in-match sprites and animations (the core)

- Convert Zangief's frames to the SPF2T format (LZ graphics, frame table, palettes, two colour sets).
- Map his Pocket Fighter moves onto SPF2T's states. For example:
  - small attack: jab;
  - medium attack: headbutt;
  - large attack: Double Lariat;
  - Super: Spinning Piledriver;
  - plus hit, win and lose poses.
- Write his animation scripts.
- Check in the emulator: attacks, mirror match, both colours.

### Step 4: voices and sound effects

- Build `SE_PL0B` from the Pocket Fighter samples, with the voice ids SPF2T expects (attacks, damage, win, lose). Resample if needed.

### Step 5: select, VS and win screens

- Select screen: portrait, name label, preview.
- VS screen and win screen: portraits from Pocket Fighter's select / VS art.
- Win quotes in English.

### Step 6: stage and music

- Convert Zangief's Pocket Fighter stage to the SPF2T stage format. The stage selector gets a ZANGIEF entry.
- Put his theme in a new XA file and point the stage's music at it.

### Step 7: Arcade lock-out

- Zangief cannot be picked in Arcade (the Down cycle skips him there). No ending, no Arcade order. Street Puzzle is not affected.

### Step 8: packaging

- `build.sh` / `patch.sh` with the second disc as input, plus checks of the Pocket Fighter image.
- README and screenshots.
- The release carries tools only, still no game data.

## Risks

- **Sprite format.** Pocket Fighter's compression and animation scripts are unknown. They are probably Capcom's usual formats, but that has to be confirmed.
- **Scale and animation set.** If Pocket Fighter's frames are bigger than SPF2T's middle-screen characters, we have to choose between a smaller set of frames and shrinking them (pixel art does not shrink well).
- **Memory.** A character must fit SPF2T's buffers and VRAM, for both players at once.
- **Choice A.** There are many hidden per-character tables, and any one we miss is a crash or a wrong value.

