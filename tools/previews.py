#!/usr/bin/env python3
"""Redraw the character-select "Counter Gem" previews from the EXE's drop
pattern table.

The previews are pre-drawn in a 4bpp texture page stored in FIRST.EMI /
FIRSTE.EMI (VRAM 640,0; file offset 0x9D800, 128 bytes per row). Each
character has a 36x24 preview (6x4 gems of 6x6 pixels, top row = pattern
row 4).

usage: previews.py EXE IN.EMI OUT.EMI [--chars 0,2,4,6,7] [--check]
  --chars  character ids to redraw (default: all). The original art of
           Devilot (8) has rows 2 and 4 swapped versus its table, so the
           build only redraws the characters whose pattern X' changes.
  --check  only verify that the previews in IN.EMI match EXE's table
"""
import struct, sys

PAGE = 0x9D800
STRIDE = 128
PATTERNS = 0x6EE84          # file offset of 0x8016E684 in SLUS_004.18
# preview origin (u, v) in the texture page, per character id
ORIGIN = [(0, 96), (40, 96), (80, 96), (120, 96), (160, 96),
          (0, 120), (40, 120), (80, 120), (120, 120), (160, 120),
          (72, 152)]
# colour id -> (light, dark) palette index
SHADES = {1: (4, 5), 2: (8, 9), 3: (6, 7), 4: (2, 3)}
BORDER, SHINE = 1, 0xD

def pattern(exe, ch):
    """4 bottom rows of a character's pattern, as lists of 6 colour ids."""
    base = PATTERNS + ch * 0xC0
    return [list(struct.unpack_from('<6H', exe, base + r * 16)) for r in range(4)]

def cell(colour):
    light, dark = SHADES[colour]
    rows = [[BORDER, SHINE] + [light] * 4]
    rows += [[BORDER, light] + [dark] * 4 for _ in range(4)]
    rows += [[BORDER] * 6]
    return rows

def render(rows4):
    """36x24 index image; top line of the image = pattern row 4."""
    img = [[0] * 36 for _ in range(24)]
    for r, row in enumerate(reversed(rows4)):
        for c, colour in enumerate(row):
            for y, line in enumerate(cell(colour)):
                for x, val in enumerate(line):
                    img[r * 6 + y][c * 6 + x] = val
    return img

def get_px(emi, x, y):
    b = emi[PAGE + y * STRIDE + x // 2]
    return (b >> 4) if x & 1 else (b & 15)

def put_px(emi, x, y, v):
    o = PAGE + y * STRIDE + x // 2
    emi[o] = (emi[o] & 0x0F) | (v << 4) if x & 1 else (emi[o] & 0xF0) | v

def main(argv):
    exe = open(argv[0], 'rb').read()
    emi = bytearray(open(argv[1], 'rb').read())
    check = '--check' in argv
    chars = range(len(ORIGIN))
    if '--chars' in argv:
        chars = [int(c) for c in argv[argv.index('--chars') + 1].split(',')]
    bad = []
    for ch in chars:
        u, v = ORIGIN[ch]
        img = render(pattern(exe, ch))
        for y in range(24):
            for x in range(36):
                if check:
                    if get_px(emi, u + x, v + y) != img[y][x]:
                        bad.append(ch)
                        break
                else:
                    put_px(emi, u + x, v + y, img[y][x])
            if check and bad and bad[-1] == ch:
                break
    if check:
        print('mismatching previews:', sorted(set(bad)) or 'none')
        return 1 if bad else 0
    open(argv[2], 'wb').write(emi)
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1:]))
