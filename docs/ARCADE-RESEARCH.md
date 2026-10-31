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
- Select cursors: P1 0xFF0C82 (+0 character, +1 position), P2 0xFF0C86 (a5 - 0x737E).
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
- Zangief bit: 0xFF3010 (bit 0 P1, bit 1 P2). Set by the select screen (cursor on
  his icon), by the CPU challenger rule (Arcade), cleared on every select set-up.
  Every check also needs character 10, so a stale bit never matters.

## Select screen (done)

- Scroll2 (base 0x904000, 16x16): the grid is ONE 12x6-tile picture (rows 8-13,
  columns 6-17, codes 0x7070-0x70B7); the PLAYER SELECT logo is 8x4 tiles (rows 3-6,
  columns 8-15). Screen y = row * 16 - 16. The logo moved to row 1; the new icon
  row (Zangief, Dan) is rows 5-7, columns 9-11 and 12-14.
- The white-bordered blue panels behind the icons are scroll1 (under scroll2 on this
  screen, layer order 0x270E), not part of the icons: 6x6 8x8 tiles 0x780-0x788
  (top 780 781x4 782, middle 783 784x4 785, bottom 786 787x4 788), palette 3,
  scroll1 rows 48-59 for the grid. Scroll1 cell (c, r >= 32) = 0x900000 +
  4 * ((r & 31) + 32 * c + 0x800); scroll1 row = 2 * scroll2 row + 32. Our row's
  panels: scroll1 rows 42-47 (xp_panels). The icon art fills only the panel's blue
  inside (42x42 from (3, 3), pen 5): `tools/cps2icons.py`.
- Cursor movement: 0x789E (KScl's tables: offsets 0x3F800, navigation 0x3F840,
  8 columns x 5 rows of characters, FF = none; start positions per character
  0x3F880). Row 0 holds the new icons (positions 1, 2).
- Select names: 0x79B0 copies the character's name tiles into scroll1 0x90212C
  (P1) / 0x90302C (P2), from the 0x84560 table (+0x0C variant).
- Name under the pose: 0x262A0, table 0x7DB20 (0x7DB78 when a5+0x90 is set: the
  same frames but for Hsien-Ko and Akuma), entry = table + 4 * char, frame = the
  long after it. The same routine draws the VS screen names (a4 = player struct
  there, select object on the select screen).
- Same character -> alternate colours: 0x7968 (confirm) and 0x7FC6 (challenge /
  STAGE screen pick) compare +0x82; hooked so that Zangief and Dan differ.

## VS screen

- Portraits: objects 0xFF9780 (P1) / 0xFF9700 (P2). 0x23B64-0x23BF8: 10 palettes
  loaded into slots 0-9 (P1) / 10-19 (P2) by 0x23E1C (d6 = brightness), then
  0x23C94 sets the entry from table 0x7DAC6[char + 11] (pseudo entries: the frame
  is the long after the entry). Dan's VS frame is his select portrait (0x7FF38),
  so Zangief's select portrait (ZPORT) is reused.
- Fighter objects keep their select pose on this screen; +1 = 0 there (not drawn):
  palette writes must check it.

## WINNER screen

- Quote: index = winner's char * 4 + random 0-3 (0xBC5A, English; Japanese uses
  19 per character), stored in 0xFF8136. Text 0x2A744: table per language
  (English base 0x46834), 136 bytes per quote = two lines of 34 words: glyph sprite
  code = ASCII | 0x80, '.' = 0x134, 0 = space, bit 15 marks capitals (stripped).
  A byte table gives the line count. Zangief: indexes 44-47 (`tools/cps2quotes.py`,
  text from PF's arcade program at 0xD1584: length word, then ASCII + 0x30 words,
  0x0C63 ',', 0x0C64 '.').
- Picture: object 0xFF9B80, entry 0x7DAC6[char] (0x23B5C, a4 = winner's struct):
  a full-body picture for 0-9, a 32x32 joke figure for Dan. Zangief: PF's select
  portrait full body at 0.72 (ZWIN), 36 pixels left of the object like Ryu's.

## Arcade (VS COM)

- Opponent order: made when Arcade starts (0xBAB2): 16 bytes from 0xBC78 + 16 *
  random row (8 rows: characters 0-7, then Dan 0x0A), copied to 0xFF0CA6; Devilot
  may take place 6, Akuma place 8. NORMAL has 8 stages (0xFF8114 = count), then the
  FINAL STAGE. Beaten characters: bits in 0xFF8110.
- STAGE screen (0x7F50): opponent = order[0xFF8112]; written to the CPU at 0x7FB6
  (fp/a4 = CPU, a0 = human). Player struct +0x9E set = played by the CPU.
- Dan as CPU (single player): 0xBDC6 sets 0xFF813E = 2: Akuma's ambush. Dan is
  never fought; an intruder object (0x27C54) runs in, taunts and is beaten, its
  animations from Dan's table 0x7AB6C (states 9, 4, 7), moved by code.
- X": Felicia moved to place 7 for Zangief (xp_zstage, xp_zorder); Zangief as the
  CPU in Dan's place one time in two (xp_zcpu, xp_zcpu2), and then in the ambush
  (xp_zintr, his intruder table at ZBLOB + 0xA0).
- CONTINUE screen: a fighter-sized figure, base = state table of fp+3, state 0-5
  by danger level (0x243D8): hooked (xp_zcont).
- Ending (NORMAL): staff roll with the player's picture, 0x23C84 (character from
  0xFF8130, dimmed: d6 = 0xC000C000): Zangief's ZCRED (0.85, centred). The scenes
  between the credits are the same for everybody.
- The random routine 0x2DB02 only moves when called: tests from a saved state need
  a different seed (0xFF80AE) each time.

## Stages

- Stage value 0xFF8100 = 2 * stage (0-20 the characters' stages, Dan 20; 22 is
  a special one). Set up by 0x20D78 (palettes), 0x1788C (layers), 0x1674E
  (stage objects); per frame 0x178A8 and 0x16A3A. The test menu's stage viewer
  (0x1C292) cycles 0-20.
- Layers: scroll2 (0x904000) holds the stage picture *and* the wells' frames,
  scroll3 (0x908000) the far background, the stage's animated things are
  sprites (objects from 0x16792). Layer control per stage at 0x178FC
  (0xFF8032, written to 0x800166 by 0x13C8; 0xFF812A set stops the write).
- Scroll2: 0x17AAE fills the 16 blocks (4x4 of 256x256) from the list 0x17D08
  + word[0x17D08 + stage]; block n = 256 cells at 0xC5880 + n * 0x400, code +
  0x5800 (blocks used: up to 0x86; 0xE7C80- is free, = block 0x89). Scroll3:
  0x17BD4, list 0x17DCE, 64 blocks of 64 cells at 0xE1080 + n * 0x100, code +
  0x1CC0.
- The camera: screen (0, 0) is scroll2 map (0x200, 0x310) in a match
  (0xFF810D = 1; 0 on the VS screen, 3 on WINNER: other parts of the map). Each
  screen's picture is a 24x6 cell band (rows 5-10 of a block pair); in the
  match the cells over the wells (columns 1-6 and 17-22) use palettes 16-30,
  darker copies of 0-14; 15 and 31 are the frames.
- Palettes: scroll2 0xA22C0 + stage * 0x200 (0x400 a stage, 32 palettes;
  loaders 0x20D06, 0x20ECC, 0x20FCE), scroll3 0xA5AC0, stage sprites 0xA0D40 +
  stage * 64.
- Music: 0x2BBF0, song = 1 + stage / 2 (pc-relative table 0x2BC12), played
  through 0x2B294.
- Scroll2 tile code c is graphics tile 0x10000 + c (16x16 units, the CPS2
  bank), the same mapping as sprites: the new ROMs (0xC00000-) are codes 0x8000-.

Zangief's stage (code_castle.s, tools/cps2castle.py): Pocket Fighter's castle
as on the PSX, built from the user's sgemf set. It is Dan's stage with its
own blocks (Dan's, band cells replaced), palette block, no stage objects and
song 24. Shown when the stage is 20 and XP_CASTLE is set (selector ZANGIEF,
RANDOM's 11th stage, or NORMAL / a challenge where the stage's player is
Zangief). In Arcade the CPU Zangief only comes in Akuma's ambush, on Akuma's
stage, so the castle is a Versus stage.

Pocket Fighter's castle (stage value 12): scroll3 sky and moon, scroll1
floating castle (8x8 tiles through 32x32 metatiles), scroll2 statue, steps and
wagon; lists, block libraries and palettes in `tools/cps2castle.py`.

## Test harness notes

- `arcade/test/stress.py`: random play with checks at every match start (stage
  selector, castle, palettes, music, the CPU's stage, rounds) and a watchdog;
  see its header. Settings live in RAM from the EEPROM: 0xFF80A2 / 0xFF80A3 =
  1P / 2P MAX ROUND (1, 2, 3 = 1, 3, 5 rounds), copied to 0xFF8121 per match;
  rounds won at player + 0xA3, consecutive wins (BCD) at + 0xA2. Boards: P1
  0xFFAB10, P2 0xFFAD10 (13 rows of 16 bytes, 6 cells; drop column at +8).
- Found by it: the next-opponent path (0xBB16 -> 0xBAB2) passes the player
  structs sign-extended from words (a0 = 0xFFFF8300): code comparing struct
  addresses must look at 24 bits only (xp_zis_ok, xp_zcpu). Before the fix
  Zangief's Arcade looped at the place Felicia was moved from.
- Random play can keep a round alive for ever (both drop columns kept clear by
  crash gems); this is the game's behaviour, not a hang.

- `tools/cps2emu.py`: breakpoints and watchpoints log registers only; the log's
  pc for a write is the writer (sprite list owners: a6 = the object).
- Making the CPU lose: fill its board's drop column (P2 board 0xFFAD10, 13 rows of
  16 bytes, cells are words, column offset 8) with alternating colours.
- Sound: see `docs/QSOUND.md`.
