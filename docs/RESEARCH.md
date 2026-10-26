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
| Branding | `X'` between win counters in matches; title line "X' BALANCE PATCH" | `0x16C0C`, `0x2DE8` |
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
- **The Counter Gem preview is rendered from the drop pattern table.** Forcing characters 8/9/10 shows the Devilot/Akuma/Dan patterns. No graphics work is needed for previews, unlike the arcade hack.
- There is **no screen space for a third row**. Positions ≥ 8 make the cursor disappear, and the grid already touches the bottom edge.
- Vanilla PSX secret access: codes on Morrigan/Felicia, or, after clearing Street Puzzle, L1 (Akuma), R1 (Devilot) or L1+R1 (Dan) while confirming.

## 6. Options

The Options menu has Difficulty, Damage Level, Game Speed, rounds, audio, BGM and controller config.
There is no handicap or free-play setting: free play is meaningless on console, and the handicap is chosen per player in Versus.

---

## 7. Open design decisions

1. **Akuma/Devilot/Dan access.** The arcade solution (third row) has no room on screen. Candidates:
   - unlock the L1/R1/L1+R1 shortcuts from the start;
   - make the grid wrap ("down" from the bottom row cycles to the hidden characters, keeping the cursor on a visible cell);
   - redraw the grid.
2. **Mei-Ling / Anita.** These are PSX-only and get +25 % in vanilla. X' doesn't define them. Options: keep them as in vanilla, or treat them like Hsien-Ko/Donovan.
3. **Handicap in Versus.** Ignore it in the formula (like X'), and optionally skip the Difficulty 1-5 selector.
4. **Branding.** X' marker in matches and on the title screen, drawn with the PSX sprite/text system.
5. **Bosses.** In vanilla `+0x6C` exempts Devilot/Akuma from their penalty. Under X' their send rates replace that penalty, so the flag becomes irrelevant.
