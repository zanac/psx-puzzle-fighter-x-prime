# Arcade (CPS2) research notes — branch arcadeenh

The arcade set `spf2enh` is built by `tools/arcade.py` from the user's `spf2t`
(Euro 960529) and `sgemf` MAME sets. KScl's X' (arcade/xprime) is applied first,
then the X" patches in `arcade/src`. These notes record what is known about the
68000 program, for the patches that are done and the ones to come.

## ROMs and encryption

- Program: `pzfe.03` (0x000000-0x07FFFF) and `pzf.04` (0x080000-0x0FFFFF), files
  stored as little-endian words. The spf2t key encrypts opcodes up to 0x80000
  (word index <= 0x40000); data reads are never encrypted. So:
  - code blocks below 0x80000 are patched into the decrypted image, which is then
    encrypted again (`tools/cps2crypt.py` does both directions, bit-exact with MAME);
  - code above 0x80000 (pzf.04) and every data block go in as they are.
- Free space: pzfe.03 0x3A913-0x3FFFF (0xFF; KScl uses 0x3F000-0x3F9xx),
  pzf.04 0x8EF2A-0x9FFFF, 0xB2D60-0xBFFFF, 0xE7C80-0xFFFFF (0xFF). X" code: 0xF0000-.
- Graphics: 4 x 1 MB (`pzf.14m/16m/18m/20m`, ROM_LOAD64_WORD) at 0x800000 of a
  0xC00000 region; the lower 8 MB are empty. `tools/cps2gfx.py` converts to and from
  16x16 tiles (tile t = region 0x800000 + t*128). Only 21 of the 32768 tiles are
  blank: there is no free space in the 4 MB.
  - Scroll1 8x8 tile c = right half of 16x16 tile c//2, rows (c%2)*8.
  - Sprites: code + ((y & 0x6000) << 3); the game always sets y bit 0x2000, so its
    sprite codes reach 0x800000-0xFFFFFF: 0xC00000-0xFFFFFF (codes 0x8000-0xFFFF)
    would be free space if the region grows to 16 MB (new ROMs in the set).
- Sound: `pzf.01/02` Z80 program (QSound driver "2.01b /CPS2 1996 /APRIL"),
  `pzf.11m/12m` QSound samples (4 MB). Pocket Fighter: driver "1.30 /CPS2 1996 /OCT.",
  samples 8 MB.

## RAM

- a5 = 0xFF8000 throughout.
- Player structs: P1 0xFF8300, P2 0xFF8700 (+0x82 character, +0x3F6 a copy).
- Select cursors: P1 0xFF8C82 (+0 character, +1 position), P2 0xFF8C86.
- Select/fighter objects: P1 0xFF8B00, P2 0xFF8C00 (+0x82 character, +0x1C animation
  entry pointer, +0x18 duration/flags, +0x9A buttons held, +0x9C previous).
  Buttons: bits 0-3 directions (1 R, 2 L, 4 D, 8 U), 0x100 / 0x200 buttons 1 / 2,
  0x8000 START.
- 0xFF80E0: 1 in VS HUMAN (also on its select screen), 0 in VS COM and challenges.
- 0xFF80AC: 3 when both players play (set when the match is prepared).
- 0xFF8100: stage * 2 (word). 0xFF8032: layer control shadow (port 0x800166).
- Free RAM (never written in boot, attract, menus, select, matches): 0xFF1400-0xFF7xxx.
  X" uses 0xFF3000-.

## Screens and routines

- Mode select: VS COM / VS HUMAN ("two players can play head-to-head with 1 credit").
- Select, per player still choosing, per frame: state 0 of 0x77E0. 0x784A computes
  the newly pressed buttons; 0x789E is the movement (KScl's nav tables 0x3F800).
- Stage of the match: 0xBA44. VS: the character of one of the players; VS COM: the
  CPU opponent's (0xBAB2 picks it).
- Sprite list builder: 0x14962, every frame, into 0x708000; a2 = next entry, d7 =
  entries left; 0x149BE writes the end mark. Entry: x | priority, y | 0x2000 (tile
  bank), code, attr (palette 0-4, flips 5-6, block size 8-15).
- Sprite font: tile 0x5880 + ASCII, 8 pixels a character, palette 9 (the game's
  "1CREDIT").
- Scroll1 text (8x16 font, KScl's routine): tile 0x40 + (c & 0x0F) + 2 * (c & 0xF0),
  bottom half + 0x10, palette 0x1F. On the select screen scroll1 is under scroll2
  (layer order 0x270E), so text there is invisible.
- Counter Gem preview: 5x5 scroll1 tiles per character at 0x87D80 + 0x11E * char
  (`tools/cps2preview.py` draws one for a new pattern).
- Drop patterns: 0x10188 + 0xC0 * char (X'), rates /20 at 0x10120 (receive) and
  0x10140 (send).

## Characters in a match (for Zangief)

- Animation: 0x14390 / 0x143B2 (d0 = animation id): base = table 0x143F6[char]
  (Morrigan 0x54CA4, Chun-Li 0x57DDE, Ryu 0x5B4AE, Ken 0x5ECB2, Hsien-Ko 0x617DC,
  Donovan 0x6747A, Felicia 0x6C290, Sakura 0x6E9BC, Devilot 0x725B8, Akuma 0x77922,
  Dan 0x7AB6C); entry = base + word[base + 2*id]. Entries are 16 bytes: +0 duration
  (word) and flags (byte +2, negative = jump to the long at +0x10 of the last entry),
  +4 sprite frame, +8 word (-> object +0xD4), +0xB event index (per-character
  event routines, table 0x14422[char]). Ticker: 0x1444E.
- Sprite frame (emitter 0x14C64): word sprites, word count-1, word position list
  offset into the pointer table 0x2DB1C, then count longs (attr << 16 | code); the
  position list gives x, y per sprite.

## Pocket Fighter arcade (sgemf), for Zangief

- Program `pcfu.03` + `pcf.04`-`pcf.07` (2.5 MB), encrypted up to 0x100000 with
  `sgemf.key`; `tools/cps2crypt.py` decrypts it. Graphics: 20 MB.
- Same engine family as SPF2T: the same sprite emitters (0x1D5CA..., variant with the
  position list pointer inline: word sprites, word count-1, long positions, then
  count longs attr << 16 | code; y is or-ed with the object's +0x3E tile bank).
- Player objects in a match: P1 0xFF8400, P2 0xFF8800; character at +0x381
  (Zangief = 9), animation entry at +0x1C.
- Player animations: 0x10E0A, base = one of three per-character tables (13 longs):
  0x72B10, 0x72B44, 0x72B78; Zangief's bases 0x1A1F2A, 0x1A355A, 0x1A6F54 (his data
  0x1A1F2A-0x1AF8AE). Entry = base + word[base + 2*id]; entries are 24 bytes
  (+0 duration and flags, +4 sprite frame).
- Select screen grid: Ryu Ken / Chun-Li Sakura Morrigan Hsien-Ko / Felicia Tessa
  Zangief Ibuki (Akuma right of Ryu). Default coinage 2 coins a credit.

## Zangief in the match (done)

- `tools/arcade_zangief.py`: the arcade PF keeps Zangief's animation entries in
  the PSX order (entry k of PL09A.MDL = k-th arcade entry from 0x1A1FC6, skipping
  the two state tables in between), so the PSX choice of animations carries over.
  Frames come composited (costumes included); scale 0.9, one 15-colour palette,
  1394 tiles at sprite codes 0x8000- (graphics 0xC00000-, four new ROMs
  pzfen.13m/15m/17m/19m). Blob at 0x90000: state offsets (63 words, 0 = Dan's),
  palette at +0x80, position lists, frames (type 12), entries.
- The game reads its jump tables pc-relative, i.e. through the decryption:
  hooks that need them keep copies (state tables 0x143F6, frame types 0x14BE2).
- Palette: Dan's sprite palette slot (P1 12, P2 16 = 12 + the object's +0x0D)
  overwritten every frame while Zangief's animation runs (sprite list hook).
- HUD name: scroll1 lists at 0x84560 (16 bytes per char*2+side, +4 list: word,
  word, columns-1, then top code/attr, bottom code/attr per column). ZANGIEF is
  composed by `tools/cps2label.py` (PSX method), lists at 0x9F000 / 0x9F080,
  hook 0x16C78. The labels use the PSX pixel coordinates in other colours
  (outline 8/D/C/B by row, F transparent, 0 shadow).
- Zangief bit: 0xFF3010 (bit 0 P1, bit 1 P2). Not set by the select screen yet.

## Select screen (to do)

- Scroll2 (base 0x904000, 16x16): the grid is ONE 12x6-tile picture (rows 8-13,
  columns 6-17, codes 0x7070-0x70B7); the PLAYER SELECT logo is 8x4 tiles (rows 3-6,
  columns 8-15). Screen y = row * 16 - 16. Free: rows 1-2 above the logo, row 7.
- Scroll2 codes reach the new graphics (0xC00000-) like sprites do.
- Cursor movement: 0x789E (KScl's tables: offsets 0x3F800, navigation 0x3F840,
  8 columns x 5 rows of characters, FF = none; start positions per character
  0x3F880). Row 0 is free for the new icon row; row 3 holds Devilot, Akuma, Dan.
- Select names: 0x79B0 copies the character's name tiles into scroll1 0x90212C
  (P1) / 0x90302C (P2), from the 0x84560 table (+0x0C variant).
