# QSound: Pocket Fighter's music in Super Puzzle Fighter II Turbo (arcade)

Both games use Capcom's QSound sound driver on the CPS2 Z80, in two versions:
Pocket Fighter (`sgemf`) has **1.30**, SPF2T (`spf2t`) has **2.01B**. The samples,
the sample table and all the envelope, volume and modulation tables are the same;
the sequences and the instruments differ. `tools/qsconv.py` converts PF songs into
SPF2T's format; `tools/arcade.py` runs it for the set `spf2enh`.

Sources: VGMTrans (`src/main/formats/CPS`, game entries in `bin/mame_roms.json`)
for the table addresses and both track formats; superctr's QSound register
description for the chip; everything else below was read from the two Z80
programs and checked by recording both games.

## Layout

| | PF (pcf.01 + pcf.02) | SPF2T (pzf.01 + pzf.02) |
|---|---|---|
| Song table | 0x9005, 4-byte BE pointers (& 0xFFFFF) | 0x6004, the same, 907 slots |
| Instrument banks | 0x3B04, 16 LE pointers | 0x3FE4, 14 LE pointers |
| Instrument | 4 bytes: sample (LE), fine tune, articulation | 8 bytes: sample (LE), fine tune, AR DR SL SR RR |
| Articulations | 0x8000, 8 bytes: AR DR SL SR RR ... | (inside the instrument) |
| Sample table | 0x5000, 8 bytes | 0x4F78, 8 bytes, 443 entries |
| Track dispatcher | 0x1186 (opcodes 0x00-0x1F) | 0x110C, indexed from **0xC0** (0xFF = end) |

- The program is 256 KB: 0x0000-0x7FFF fixed, 0x8000-0xBFFF a 16 KB window; song
  pointers are linear, and the driver switches banks as it reads (`CP 0xC0`).
- Sample entry (both): bank, start, loop, end (16-bit LE, inside the 64 KB bank),
  unity key. A sample never crosses a bank; QSound address = bank << 16 | addr.
- Song header (both): 1 flags byte, 16 BE track offsets from the song start.
  Track 0 carries the tempo: the other tracks do not advance without it.
- Sound commands (68000 side): a queue of 16-byte records (PF base 0xFFE230,
  write index 0xFFF230, read 0xFFF232; SPF2T base 0xFFC7A0, indexes 0xFFD7A0/A2),
  sent to the Z80 at 0x618001/0x618003 (id high/low), 0x618005-... (d2: 0x1000
  for music). Id 0xFF05 stops everything.

## Track formats

**V1 (PF)** is a state machine. A byte >= 0x20 is a note or rest: duration =
`delta_table[t][(b >> 5) - 1]` (t from state bits 0x30), key = `(b & 0x1F) +
octave_table[state & 0x0F] - 1`, gate = `delta * duration_byte >> 8`; state 0x40 =
tie. Commands 0x00-0x1F: duration tables, tie, octave, tempo (05, word), gate
(06), volume (07), program (08), transpose (0A/0B), detune (0C), portamento (0D),
counted loops and breaks (0E-15), loop forever (16), end (17), pan (18), QSound
effect (19), master volume (1A), vibrato (1B), tremolo (1C), LFO rate (1D), LFO
reset (1E), bank (1F).

**V2 (SPF2T)**: 0x00-0x7F rest (7-bit groups, big-endian, ended by the next byte
>= 0x80); 0x80-0xBF note: `0x80 | velocity (0-63)`, key, duration (MIDI varlen);
commands C1 tempo (word), C2 bank, C3 pitch bend, C4 program, C5 vibrato, C6
volume, C7 pan, C8 expression, C9 portamento, CE goto, D0-D3 loop starts, D4-D7
loop (count 0 = forever), D8-DB loop breaks, DD transpose, E0 LFO reset, E1 LFO
rate, E2 tremolo, FF end.

## Mapping (V1 -> V2)

| V1 | V2 | Why |
|---|---|---|
| 05 tempo (word) | C1 (word) | the same unit (ticks << 8 per driver iteration) |
| 07 volume | C6 | the same curve (PF 0x34F1 = SPF 0x3685) |
| 18 pan 0-0x20 | C7 pan * 4 (0x20 -> 0x7F) | both end as QSound 0x110 + pan; V2 divides by 4 |
| 08 program, 1F bank | C2 bank, C4 program | all converted instruments in one new bank |
| 0C detune | instrument copy with the detune added to its fine tune | PF adds it to the pitch in 1/256 semitones, like the fine tune; V2's C3 is 24 times coarser |
| 0D portamento | C9 | both store value * 2 |
| 1B / 1C / 1D | C5 / E2 / E1 | identical tables (PF 0x38F1 / 0x39F1 / 0x37F1 = SPF 0x3B85 / 0x3C85 / 0x3A85) |
| 1E LFO reset | E0 | |
| 0A / 0B transpose | folded into the keys | |
| ties | merged into longer notes; a tie into another key starts a new note | |
| counted loops | unrolled | |
| 16 loop forever | D0 at the target time, D4 00 at the end | |
| — | note velocity: a constant (`VELOCITY` in arcade.py, 26) | V2 scales by a linear curve (0x3785); 26 makes the song as loud as SPF2T's own music (RMS ~2500) |

The envelope rate tables (0x35F1/0x36F1/0x3771 in PF, 0x3785/0x3985/0x3A05 in
SPF2T) are identical, so the ADSR bytes are copied as they are.

Not converted (not used by the songs so far): 07 with bit 7 set, 19 (QSound
effect depth), 1A (master volume). Portamento between tied notes of different keys
is approximated by a new note.

## Where the converted data goes

- Instrument bank pointer table moved to 0x3E88 (free 0x3E87-0x3FDF; 0x3FE0/2 are
  used words), 16 entries: SPF2T's 14, the new bank 14, 0. The four references
  (operands at 0x037D, 0x0404, 0x0C9C, 0x1182) are patched. Bank 14's instruments
  follow (room for 39).
- New sample entries after the 443 (free until 0x6004: 86 more).
- Songs in the free banked space 0x24B00-0x3FFFF, in empty song table slots
  (Pocket Fighter's song 7, the castle stage's music, is SPF2T's song **24**).
- Samples: PF's 64 KB banks that hold them are copied whole into the new ROM
  `pzfen.13s` (QSound 0x400000-0x7FFFFF, banks 0x40-), so the addresses inside a
  bank stay valid. mame2003-plus addresses 8 MB with 7 bank bits.
- The set `spf2enh` therefore has `pzfen.01/02` (Z80) and `pzfen.13s` in place of
  `pzf.01/02`, and an 8 MB QSound region.

Finding PF's stage music: 0x3B02 in PF's 68000 program plays `table[stage]` at
0x3B18, ids 1-...: the castle (stage index 6, the stage the PSX version uses for
Zangief) is song 7.

## Testing a conversion

`arcade/test/qsound_record.py` and `qsound_compare.py` do this:

1. Load a match state of each game (a select screen has a timer that changes the
   screen and mutes the sound, 0x619FFD).
2. Queue 0xFF05 (stop), then the song with d2 = 0x1000.
3. Every frame, set the queue's write index to its read index: the game's own
   commands are dropped.
4. Capture the audio (`lr.Emu.capture_audio`, 48 kHz stereo) and compare:
   envelope correlation in 3 s windows (lag must stay constant: no tempo drift),
   spectral peaks (pitch), RMS (level).
5. For one track alone, zero the other track offsets in the song header, but keep
   track 0 (it carries the tempo).

Results for the castle song: identical spectral peaks, constant lag over 45 s, RMS
~2300 against SPF2T's music 2100-3100, no clipping.

## Voices

- SPF2T plays a character's voice through 0x2BE50: id = base[character]
  (0x2BE7E: Morrigan 0x120, Chun-Li 0x140, Ryu 0x160, Ken 0x180, Hsien-Ko 0x1A0,
  Donovan 0x1C0, Felicia 0x1E0, Sakura 0x200, Devilot 0x220, Akuma 0x240, Dan
  0x250) + offset, + 0x200 for P2. The offset comes from the attack voice table
  0x14496 (character * 64 + category (+0xDB) * 8 + variant (+0xD8)); Dan uses
  offsets 2-7, 15, 20. fp there is the player struct.
- A voice is a song with flags 0x10 and one track: channel 10 for P1, 11 for P2
  (the two songs are otherwise the same).
- Pocket Fighter: Zangief's voices are the songs that play instrument bank 7
  (ids 0x1C6-0x1F7..., one track, track 12).
- Matching the PSX choices (docs/ZANGIEF-VOICES.md): Dan's arcade offset n is
  his PSX voice slot n + 1 (cross-correlation of the PSX VAGs, decoded, with the
  arcade samples, at a fixed 1.08 length ratio); PF's PSX VAGs match PF's arcade
  bank 7 instruments at 1.5 (correlation 0.84-0.998 for 19 of the 31; VAGs 6,
  10, 12, 29 and 31 have no arcade take).
- `tools/arcade.py` ZVOICES: Dan's offset -> (PF voice id, SPF2T slot s); each
  voice is converted twice (slot s on channel 10, s + 0x200 on channel 11, flags
  0x10, velocity 63 as Dan's) and code_voice.s (hook 0x2BE5E) plays s for
  Zangief. Free slot pairs used: 0x13C-0x13F, 0x199-0x19C (above the highest
  offset Morrigan and Ken use).
- Checked: the converted voices last exactly as PF's and are as loud as Dan's
  (RMS 3300-6000, peaks ~17000); in a match P1 Zangief plays 0x13C..., P2
  0x33C..., Dan keeps 0x25x / 0x45x.
