# Research notes — porting X' to Super Puzzle Fighter II Turbo (PSX)

Target: **Super Puzzle Fighter II Turbo, NTSC-U, SLUS-00418**.
Reference: [KScl/puzzle-fighter-x-prime](https://github.com/KScl/puzzle-fighter-x-prime)
(CPS2 `spf2t`, 68000), itself a port of Sirlin's X' balance from HD Remix.

All PSX addresses are RAM addresses of the main executable `SLUS_004.18`
(text loaded at `0x80100000`, size `0x8E000`, entry `0x8015C8E8`).
File offset in the EXE = `addr - 0x80100000 + 0x800`.

The PSX port is compiled C, not a translation of the 68k code, but it keeps the
arcade logic, data layout and even the tables almost one-to-one.

---

## 1. What the arcade X' hack does (target behaviour)

| Area | Arcade hack | Where (CPS2 `pzfe.03`) |
|---|---|---|
| Drop patterns | New patterns for Morrigan, Ryu, Hsien-Ko, Felicia, Sakura | data `0x10188 + char*0xC0` |
| Garbage formula | Full rewrite of the damage routine (see §3) | code `0xFDA4` + tables `0x10110` |
| Diamond | Always 80 %, "diamond trick" removed | code `0x119A6` |
| Character select | Devilot/Akuma/Dan reachable by moving down from bottom row | code `0x789E`, tables `0x3F800` |
| Defaults | Free Play on, handicap off, join-in on | soft dips `0x1E936` |
| Branding | `X'` between win counters in matches; title line "X' BALANCE PATCH BY ZANAC" | `0x16C0C`, `0x2DE8` |
| Pattern preview | New preview tiles on char select (gfx IPS) | `0x7D80…`, gfx ROMs |

Character ids (same on both platforms): 0 Morrigan, 1 Chun-Li, 2 Ryu, 3 Ken,
4 Hsien-Ko, 5 Donovan, 6 Felicia, 7 Sakura, 8 Devilot, 9 Akuma, 10 Dan.

Colours: 1 Blue, 2 Yellow, 3 Green, 4 Red. Pattern rows are stored bottom row first.

### New drop patterns (period 4 rows; table repeats the 4 rows 3×)

| Char | row 1 (bottom) | row 2 | row 3 | row 4 |
|---|---|---|---|---|
| Morrigan | B Y R R Y B | B Y G R Y B | Y B G R B Y | Y B G G B Y |
| Ryu | R G B Y R G | R G B Y R G | B Y R G B Y | R G B Y R G |
| Hsien-Ko | B Y B G R G | B B G R Y G | B G R Y B G | B R Y B G G |
| Felicia | G R R B B Y | Y R B R B G | G R B R B Y | Y B B R R G |
| Sakura | G R R R R Y | G B B B B Y | Y R R R R G | Y B B B B G |

### Per-character multipliers

| Char | Send | Receive |
|---|---|---|
| Chun-Li | 120 % | 100 % |
| Devilot | 85 % (was ⌊x/4⌋+⌊x/2⌋) | 100 % |
| Akuma | 100 % (was ⌊x/4⌋+⌊x/2⌋) | 120 % |
| others | 100 % | 100 % |

---

## 2. PSX map

### Player structure

Two structs, stride `0x2AC`: **P1 `0x801AE500`**, **P2 `0x801AE7AC`**.

| Offset | Size | Meaning |
|---|---|---|
| `+0x67` | b | player index (0/1) |
| `+0x68` | b | character id |
| `+0x6C` | b | non-zero = Devilot/Akuma penalty skipped (believed CPU/boss flag) |
| `+0x73` | b | handicap level (Versus "Difficulty 1-5", default 2) |
| `+0x84` | w | pointer to opponent struct |
| `+0xEC`/`+0xEE` | h | bottom/top gem type of the falling pair (5 = diamond) |
| `+0x10C…+0x118` | h×7 | score components summed by the damage routine |
| `+0x1D2`/`+0x1D4` | h | drop pattern row / column cursor |
| `+0x1F0` | h | elapsed match time in seconds (margin time) |
| `+0x22A` | h | pending garbage (capped at 250) |
| `+0x23F` | b | diamond penalty flag (vanilla: halves damage) |
| `+0x296` | b | "diamond used" flag (equivalent of arcade `+0x38C`) |

### Globals

| Addr | Meaning |
|---|---|
| `0x8019C405` | Damage Level option (0..3 = Low..High, `&7` index) |
| `0x8019C40F` | Game mode (3 = Versus; handicap only applied here) |
| `0x801AE4D8` / `0x801AE4D9` | per-player bit: Hsien-Ko → **Mei-Ling**, Donovan → **Anita** (PSX/Saturn-only alternates) |
| `0x801BAAC4` / `+5` | char select: P1 character / cursor position (row*4+col, 0..7) |

### Data tables (all inside the EXE)

| Addr | File off | Content |
|---|---|---|
| `0x8016E5F4` | `0x6EDF4` | margin time thresholds (h): 90,120,…,420, then 2970 sentinel — same as CPS2 |
| `0x8016E614` | `0x6EE14` | margin multipliers (h): 0,1,…,12 (tenths added) |
| `0x8016E634` | `0x6EE34` | damage level (h): −2,0,3,5,5… (+10 → 8,10,13,15 tenths) |
| `0x8016E644` | `0x6EE44` | chain bonus table |
| `0x8016E684` | `0x6EE84` | **drop patterns**, 11 × `0xC0` (12 rows × 8 halfwords), same layout/order as CPS2 |
| `0x8016F6E4` | `0x6FEE4` | char select cursor → character: `2 1 7 3 / 0 4 5 6` |

### Code

| Addr | File off | Routine |
|---|---|---|
| `0x80134D80` | `0x35580` | **damage calculation** (end `0x80134FE0`), equivalent of arcade `0xFDA4` |
| `0x80134BFC` | | caller; then garbage offsetting vs opponent (`0x80134C4C`) |
| `0x801350E4` | | drop pattern lookup (reads `0x8016E684`) |
| `0x8012FC9C` | `0x3049C` | **diamond landing**, equivalent of arcade `0x119A6` |
| `0x8013AD30` | `0x3B530` | **char select cursor movement** (end `0x8013AEB4`) |

---

## 3. Damage formula: vanilla PSX vs X'

### Vanilla PSX (`0x80134D80`)

```
x  = sum(+0x10C .. +0x118)
i  = first index with thresh[i] >= time+15
x  = x + floor(x/10) * margin[i]
x  = floor(x/10) * (lvl[dmglevel] + 10)
x  = floor(x/100)
if diamond(+0x23F):              x = x >> 1
if !(+0x6C) and char in {8,9}:   x = (x>>1) + (x>>2)      # Devilot, Akuma
if char==4 and Mei-Ling bit:     x = x + (x>>2)           # +25 %
if char==5 and Anita bit:        x = x + (x>>2)           # +25 %
if mode==3 (Versus):             x += floor(x/10) * max(0, opp.handicap - my.handicap)
pending(+0x22A) = min(pending + x, 250)
```

### X' (arcade hack, to be reproduced bit-exact)

`mf(x, n, d) = floor(x/d) * n`, skipped when `n == d`:

```
x = mf(x, 10 + i, 10)               # margin, thresholds 90..270 (+15), max ×1.7
x = mf(x, recv[opp.char], 20)
x = mf(x, send[my.char], 20)
if diamond: x = mf(x, 8, 10)
x = mf(x, lvl[dmglevel], 10)        # 8,10,13,15
x = floor(x / 100)
```

Notes:

- The thresholds and damage-level values are identical to vanilla. Only the
  margin cap (×1.7 instead of ×2.2) and the rounding differ.
- The arcade hack drops the Devilot/Akuma penalty, the boss flag and the handicap.
  "Handicap off" is a soft dip there. On PSX the handicap is only used in Versus.
- The whole X' routine fits comfortably in the vanilla routine's 0x260 bytes.

## 4. Diamond (`0x8012FC9C`)

Vanilla PSX:

```
if bottom == diamond: +0x296 = 1; under = cell_below(bottom); if under in (0, 0xFF): under = 5
elif top == diamond:  +0x296 = 1; +0x23F = 1; under = cell_below(top)
```

The penalty flag `+0x23F` is set only when the diamond is the **top** gem.
Rotating the pair so the diamond lands at the bottom gives 100 % damage instead
of 50 %. That is the "diamond trick".

X': set the flag in both branches (and in the damage routine apply ×8/10
instead of `>>1`). The arcade hack additionally maps `under == 0xFF → 5` for the
top branch as well.

## 5. Character select (`0x8013AD30`)

- Input bits: `0x1000` up (−4), `0x4000` down (+4), `0x8000` left (−1), `0x2000` right (+1).
- The cursor is kept in 0..7, and moving left/right between 3 and 4 is blocked.
- After a move, the code writes the character from the `0x8016F6E4` table to `+0x74` and to `0x801BAAC4`, plays SE `0x17`, and clears the Mei-Ling/Anita bits.
- **The Counter Gem preview is pre-drawn art, not generated from the table.**
  It is a 4bpp texture page at VRAM (640,0), CLUT (0,491), stored raw in
  `DATA/FIRST.EMI` and `DATA/FIRSTE.EMI` (identical files) at offset `0x9D800`, 128 bytes per row.
  Each character has a 36×24 preview drawn as 5×3 8×8 sprites. Origins (u,v) are char×40 on rows v=96 (0–4) and v=120 (5–9), and Dan is at (72,152).
  Each gem is 6×6 pixels: border 1, shine D, light/dark 4/5 blue, 8/9 yellow, 6/7 green, 2/3 red.
  The top preview row is pattern row 4. The original Devilot art has rows 2/4 swapped versus its table.
  `tools/previews.py` regenerates previews from the EXE table.
- The "1P/2P" cursor badge (`0x80115F9C`) is drawn only when the character is < 8.
- Confirming (`0x8013AB04`): secret code results → a0 = 1/2/3 → character 8/9/10. The path writes `+0x74`, `0x801BAAC4/8` and the game struct `+0x68`, and sets the "secret used" globals `0x801BE050` (Devilot), `0x8019FE84` (Akuma) and `0x801BF120` (Dan). Mei-Ling/Anita codes only set the alt bit (`1 << player`).
- The select screen has no portrait or name art for Mei-Ling/Anita (the name strip has the vanilla names only); the alternates appear in the match.
- There is **no screen space for a third row**. Positions ≥ 8 make the cursor disappear, and the grid already touches the bottom edge.
- Vanilla PSX secret access: codes on Morrigan/Felicia, or, after clearing Street Puzzle, L1 (Akuma), R1 (Devilot) or L1+R1 (Dan) while confirming.

## 6. Options

The Options menu has Difficulty, Damage Level, Game Speed, rounds, audio, BGM and controller config.
There is no handicap or free-play setting: free play is meaningless on console, and the handicap is chosen per player in Versus.

---

## 7. Name labels, text layer, X' markers

**Name labels (select screen).** Each player has a label object: P1 at `0x801BE5A8`, P2 at `+0x150`.
- Every frame, `0x80116438` (P1) and `0x8011649C` (P2) compare the select character with `+0x58` and call the setter `0x801163A0` on change.
- The setter takes the frame from the table `0x801898E4[char]` (`0x33 + n`) and stores it in `+0x28`.
- The frames are 44-byte records in `FIRST.EMI` at `0xEF8C4` (RAM `0x800F41C4`). Their pixels are LZ streams in the graphics bank, which is container entry 30 (file `0xC7800`, RAM `0x800BF600`). They are decoded by `0x8010D5C0` into a 256×16 4bpp strip; see `tools/lzh.py`.
- US-unused frames: `0x37` LEI-LEI and `0x3C` GOUKI. They are redrawn as ANITA and MEI-LING.
- MEI-LING needs more room, so DAN's stream moves to the bank padding: entry 30 grows from `0x275A8` to `0x27800`, and RAM `0x800E6BA8–0x800E6E00` is otherwise unused.

**Text layer.** It is a 48×30 tilemap at `0x801C111C` (column stride `0x78`, cell = tile u16 + attr u16), drawn under the sprites.
- Redraw is requested by writing 2 to `0x801667C0`.
- API: `0x80107C98` colour, `0x80107CA8` font (0 = 8×8, 1 = 8×16, 2 = big), `0x80107CB8(col,row,str)` print, `0x80107C20` clear.
- 8×16 font tiles: top = `(c&0x1F) + ((c&0xE0)<<1) + 0x40`, bottom = top + `0x20`.

**X' markers.**
- In a match, "X'" (8×16 font, palette 5) is drawn at col 22, row 26, between the win counters. It is written by a hook on the three calls to the per-frame match update `0x801351C8`.
- It is erased on scene init (`0x80123FE4`).
- On the title screen, "X' BALANCE PATCH BY ZANAC" is printed at row 28.

**Task stacks are small.** Hooks running in the scene-init path must not open a stack frame: an extra 0x18 bytes there corrupted the next scene. The stubs keep `ra` in `t8`.

**Freed space.** The secret-code detectors (`0x8013CC60`, `0x8013CCF0`) and their call block in the select handler (`0x8013AA60–0x8013AACC`) are now unused and hold new code. The codes themselves no longer work; every secret character is reached by cycling.

**Versus RESULT screen.** Rows for Devilot/Akuma/Dan appear once their "used" globals are set, which the confirm hook does. Mei-Ling/Anita count as Hsien-Ko/Donovan, as in vanilla.

## 7b. Versus stage selector (experimental branch)

**Vanilla.**
- `0x8012CCE0`: `stage = player[s2].char` (P1 in Versus), stored as a halfword at `0x8019FC98`. It runs once per match, not per round.
- `0x80107944` loads the stage when it differs from the cached one (`0x801BF114`): `table[stage]` at `0x80166728` (11 entries; Dan, 10, shares Ken's function). Two more 11-entry tables follow at `0x80166754` and `0x80166780`.
- Stage files: `DATA/STAGE00..09.EMI`, file ids `0x4A + n` in the LBA table at `0x80165CC0`.
- The match music follows the stage, not the characters.
- Mode bytes: `0x8019C3FF` is the mode being set up (3 = Versus on the select screen), `0x8019C40F` the mode of the running match.
- Pads: pressed this frame at `0x801BF09E` (P1) / `0x801BF0AA` (P2), held at `0x801BF09C`; bits: SELECT `0x0100`, L2 `0x01`, R2 `0x02`, L1 `0x04`, R1 `0x08`, up/right/down/left `0x1000/0x2000/0x4000/0x8000`.
- RESULT screen cursor: `0x8019C3DA` (0 CONTINUE, 1 END, 2 CLEAR RESULT).

**Patch (`src/stage.asm`).**
- Line `L1 < STAGE: name > R1` at col 11, row 27, palette 5, Versus select only. It is drawn by the select handler (the old secret-code call block at `0x8013AA60` jumps to `xp_stagekey`) and erased on scene init with the X' marker.
- R1 moves forward and L1 back, both wrapping, through NORMAL → RANDOM → MORRIGAN … AKUMA. Only P1 can change it, while still choosing; P2's handler only draws the line.
- `xp_stage` replaces the `lbu` at `0x8012CCE0`. In a Versus match, NORMAL keeps vanilla, a fixed setting n gives stage n-2, and RANDOM draws one of the 10 stages. The draw uses an LCG stirred with root counters 0 and 1, excluding the stage of the previous match.
- `xp_title` resets the setting to NORMAL.
- The code and its variables live at `0x801544E4`, a 996-byte function with no references (no `jal`, no pointer, no `lui`/`addiu` pair). Emulator coverage never reached it.

## 8. Design decisions

1. **Secret characters:** Down on the bottom row cycles the cell's character through Devilot → Akuma → Dan → Mei-Ling → Anita → cell character. The cursor stays on the visible cell. Confirmation reuses the vanilla secret-code path, so all the vanilla side effects happen.
2. **Mei-Ling / Anita** count as Hsien-Ko / Donovan: no +25 %, same patterns and rates.
3. **Versus handicap** (Difficulty 1-5) is kept, with vanilla behaviour: `x += floor(x/10) * (diff + 1)` when the opponent's level is higher.
4. **Free play** is not applicable on console.
5. **Bosses:** the `+0x6C` flag is irrelevant under X' (no Devilot/Akuma penalty any more).
6. **Branding:** X' marker in matches, "X' BALANCE PATCH BY ZANAC" on the title.
7. **Mei-Ling / Anita labels** on the select screen (redrawn unused Japanese labels).
8. **Versus stage (experimental):** the selector starts at NORMAL. The choice is kept between matches until the title screen comes back. RANDOM never repeats the stage of the previous match.
