#!/usr/bin/env python3
"""Build the character-select name labels for Mei-Ling, Anita and Zangief,
and Zangief's in-match HUD name (see put_hud_name).

The labels are LZ-compressed 4bpp strips (256x16, see lzh.py) in FIRST.EMI /
FIRSTE.EMI: a graphics bank (container entry 30, file offset 0xC7800, loaded
at 0x800BF600) and 44-byte frame records at 0xEF8C4 (label index n, frame id
0x33 + n). The US game never shows the Japanese names LEI-LEI (n=4, frame
0x37) and GOUKI (n=9, frame 0x3C); they are redrawn as ANITA and MEI-LING,
assembled from letters of the other labels so the style matches.

MEI-LING with its hyphen needs ~630 bytes, more than GOUKI's 574. DAN's
label (n=10) follows GOUKI in the bank, so it is moved to the bank's file
padding (entry 30 grows from 0x275A8 to 0x27800 bytes; the RAM it lands in,
0x800E6BA8-0x800E6E00, is unused) and MEI-LING takes both slots.

usage: labels.py IN.EMI OUT.EMI [--preview out.png]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzh

BANK = 0xC7800
RECORDS = 0xEF8C4
REC_SIZE = 0x2C
MORRIGAN, KEN, LEILEI, DEVILOT, GOUKI, AKUMA = 0, 3, 4, 8, 9, 11
ZG_SLOT = 13                    # ZANGIEF: frame 0x33 + 13 = 0x40

# (source label, first column, end column) of each letter, outlines included
GLYPHS = {
    'M': (MORRIGAN, 1, 13),
    'I': (LEILEI, 29, 36),
    'G': (MORRIGAN, 48, 59),
    'N': (MORRIGAN, 68, 80),
    'E': (LEILEI, 15, 29),
    '-': (LEILEI, 35, 43),
    'L': (LEILEI, 43, 57),
    'A': (AKUMA, 0, 16),
    'n': (KEN, 32, 48),         # wide N, matches the wide A
    'T': (DEVILOT, 66, 80),
    'F': (6, 4, 15),            # FELICIA
}
# No vanilla label has a Z: drawn by hand in the same style (shades by row,
# 15 = outline), for ZANGIEF
CUSTOM = {
    'Z': [".............",
          "..ffffffffff.",
          ".f1333333333f",
          ".f2333333332f",
          ".fffffff443f.",
          "......f555f..",
          ".....f666f...",
          "....f777f....",
          "...f777f.....",
          "..f888f......",
          ".f999fffffff.",
          "f999999999af.",
          "faaaaaaaaaadf",
          "fbbbbbbbbbbdf",
          "fcbbbbbbbbbdf",
          "fffffffffffff"],
}
OUTLINE = 15
DAN = 10
BANK_ENTRY = 30                 # container entry holding the bank
BANK_SIZE_OLD, BANK_SIZE_NEW = 0x275A8, 0x27800

def record(emi, n):
    off = struct.unpack_from('<I', emi, RECORDS + n * REC_SIZE)[0] & 0xFFFFFF
    return off

def label_pixels(emi, n):
    return lzh.to_pixels(lzh.decode(emi, BANK + record(emi, n))[0])

def compose(emi, text, width=80):
    cols = []
    for ch in text:
        if ch in CUSTOM:
            rows = CUSTOM[ch]
            g = [[int(rows[y][x], 16) if rows[y][x] != '.' else 0 for y in range(16)]
                 for x in range(len(rows[0]))]
        else:
            n, a, b = GLYPHS[ch]
            src = label_pixels(emi, n)
            g = [[src[y][x] for y in range(16)] for x in range(a, b)]
        if cols:
            # letters share their outline column
            last = cols[-1]
            first = g[0]
            cols[-1] = [p if p not in (0, OUTLINE) else (q if q not in (0, OUTLINE) else (p or q))
                        for p, q in zip(last, first)]
            g = g[1:]
        cols += g
    if len(cols) > width:
        raise ValueError('%s is %d px wide (max %d)' % (text, len(cols), width))
    pad = (width - len(cols)) // 2
    cols = [[0] * 16] * pad + cols + [[0] * 16] * (width - len(cols) - pad)
    rows = [[cols[x][y] for x in range(width)] + [0] * (256 - width) for y in range(16)]
    return rows

def set_record(emi, n, off):
    struct.pack_into('<I', emi, RECORDS + n * REC_SIZE, off)

def put_stream(emi, n, rows, start, room):
    data = lzh.encode(lzh.from_pixels(rows))
    if len(data) > room:
        raise ValueError('label %d: %d bytes > %d available' % (n, len(data), room))
    emi[BANK + start:BANK + start + room] = data + b'\0' * (room - len(data))
    set_record(emi, n, start)
    assert lzh.to_pixels(lzh.decode(emi, BANK + start)[0]) == rows
    return len(data)

# --- in-match HUD name (ZANGIEF) -------------------------------------------------
# The match HUD draws each player's name as four 16x16 sprites from a texture
# page uploaded at boot (FIRST.EMI entry 25: VRAM 960,0, 4bpp, 256x256): P1
# names at u 128-191 (left-aligned), P2 at u 192-255 (right-aligned), one
# 16-pixel row per character (table 0x8018BF38). The page has no blank
# 64x16 block, so ZANGIEF takes MORRIGAN's P2 copy (row 48, u 192-255), and
# P2 Morrigan uses her P1 copy, which only differs by one pixel of alignment
# (xp_zhud). ZANGIEF is assembled from the other names' letters plus a
# hand-drawn Z in the same italic, outlined style (outline shades 9/e/d/c by
# row, 1 = shadow).
HUD_PAGE = 0xAD800              # FIRST.EMI / FIRSTE.EMI entry 25
HUD_ROW = 48                    # MORRIGAN
HUD_OUTLINE = (9, 0xE, 0xD, 0xC, 1)
HUD_ROWS = {'DAN': 208, 'MORRIGAN': 48, 'HSIEN-KO': 112, 'FELICIA': 144}
# (name row, first column, end column at the bottom (row 11) of the P1 name,
# u - 128); the letters lean right by one column every three rows
HUD_GLYPHS = {'A': ('DAN', 17, 26), 'N': ('DAN', 25, 34), 'G': ('MORRIGAN', 37, 46),
              'I': ('HSIEN-KO', 16, 21), 'E': ('HSIEN-KO', 20, 30), 'F': ('FELICIA', 3, 11)}
HUD_Z = ["          ",
         "          ",
         "9999999999",
         "9555555559",
         "9999997559",
         "     e75e ",
         "    e64e  ",
         "   e64e   ",
         "  d47d    ",
         " d33dddddd",
         "d333333333",
         "c22222222c",
         "cccccccccc",
         "1111111111",
         " 11111111 ",
         "          "]

def hud_slant(y):
    return (11 - y) // 3

def hud_name(page, text):
    px = lambda x, y: (page[y * 128 + x // 2] >> 4) if x & 1 else (page[y * 128 + x // 2] & 15)
    can = [[0] * 16 for _ in range(80)]
    cur = 0
    for ch in text:
        if ch == 'Z':
            w = len(HUD_Z[0])
            g = [[0] * 16 for _ in range(w + 4)]
            for y in range(16):
                for x, c in enumerate(HUD_Z[y]):
                    if c != ' ':
                        g[x + hud_slant(y) + 1][y] = int(c, 16)
        else:
            n, a, b = HUD_GLYPHS[ch]
            v, w = HUD_ROWS[n], b - a
            g = [[0] * 16 for _ in range(w + 4)]
            for y in range(2, 15):
                for x in range(a, b):
                    c = px(128 + x + hud_slant(y), v + y)
                    if c not in (0xA, 0xB):             # the lightning behind short names
                        g[x - a + hud_slant(y) + 1][y] = c
        for x, colm in enumerate(g):
            for y, q in enumerate(colm):
                p = can[cur + x][y]
                if q and (p == 0 or (p in HUD_OUTLINE and q not in HUD_OUTLINE)):
                    can[cur + x][y] = q
        cur += w - 1
    used = max(x for x in range(80) if any(can[x])) + 1
    assert used <= 62, used
    return can[:used]

def put_hud_name(emi, orig):
    page = orig[HUD_PAGE:HUD_PAGE + 0x8000]
    cols = hud_name(page, 'ZANGIEF')
    def put(x, y, c):
        o = HUD_PAGE + y * 128 + x // 2
        emi[o] = (emi[o] & 0x0F) | (c << 4) if x & 1 else (emi[o] & 0xF0) | c
    x0 = 256 - 2 - len(cols)                    # right-aligned, as P2 names
    for y in range(2, 15):
        for x in range(192, 256):
            put(x, HUD_ROW + y, 0)
        for x, colm in enumerate(cols):
            put(x0 + x, HUD_ROW + y, colm[y])
    return cols

def main(argv):
    orig = open(argv[0], 'rb').read()      # glyph source, never modified
    emi = bytearray(orig)
    hdr = 16 + BANK_ENTRY * 16
    assert struct.unpack_from('<I', emi, hdr)[0] == BANK_SIZE_OLD, 'unexpected FIRST.EMI layout'
    imgs = {}

    # 1. move DAN's stream to the bank padding and grow the bank entry
    dan_off = record(orig, DAN)
    _, dan_len = lzh.decode(orig, BANK + dan_off)
    assert BANK_SIZE_OLD + dan_len <= BANK_SIZE_NEW
    pad = orig[BANK + BANK_SIZE_OLD:BANK + BANK_SIZE_NEW]
    assert len(set(pad)) == 1, "bank padding is not plain filler"
    emi[BANK + BANK_SIZE_OLD:BANK + BANK_SIZE_OLD + dan_len] = orig[BANK + dan_off:BANK + dan_off + dan_len]
    set_record(emi, DAN, BANK_SIZE_OLD)
    struct.pack_into('<I', emi, hdr, BANK_SIZE_NEW)

    # 2. ANITA in LEI-LEI's slot
    lei_off = record(orig, LEILEI)
    _, lei_len = lzh.decode(orig, BANK + lei_off)
    imgs[LEILEI] = compose(orig, 'AnITA')
    put_stream(emi, LEILEI, imgs[LEILEI], lei_off, lei_len)

    # 3. MEI-LING in GOUKI's slot plus DAN's old one (contiguous)
    gou_off = record(orig, GOUKI)
    assert gou_off + lzh.decode(orig, BANK + gou_off)[1] == dan_off
    imgs[GOUKI] = compose(orig, 'MEI-LING')
    put_stream(emi, GOUKI, imgs[GOUKI], gou_off, dan_off + dan_len - gou_off)

    # 4. ZANGIEF (PSX X' hidden character) in the two small labels 13 and 14
    #    (small-font MORRIGAN / CHUN-LI, never decoded in boot, menus,
    #    Versus, Arcade or Street Puzzle), which are contiguous
    s13, s14 = record(orig, ZG_SLOT), record(orig, ZG_SLOT + 1)
    l14 = lzh.decode(orig, BANK + s14)[1]
    assert s13 + lzh.decode(orig, BANK + s13)[1] == s14
    imgs[ZG_SLOT] = compose(orig, 'ZANGIEF')
    put_stream(emi, ZG_SLOT, imgs[ZG_SLOT], s13, s14 + l14 - s13)
    set_record(emi, ZG_SLOT + 1, s13)            # label 14 now shows ZANGIEF too
    # the small labels are 4 cells (64 px) wide: give label 13 the 5-cell
    # geometry of the full-size ones (x -40, 5 columns, mask) from MORRIGAN
    r13 = RECORDS + ZG_SLOT * REC_SIZE
    emi[r13 + 4:r13 + 16] = orig[RECORDS + MORRIGAN * REC_SIZE + 4:RECORDS + MORRIGAN * REC_SIZE + 16]

    # untouched labels must decode exactly as before
    for n in range(15):
        if n == ZG_SLOT + 1:
            continue
        if n not in imgs:
            assert lzh.decode(emi, BANK + record(emi, n))[0] == lzh.decode(orig, BANK + record(orig, n))[0]
    # 5. ZANGIEF's in-match HUD name
    put_hud_name(emi, orig)
    if '--preview' in argv:
        from PIL import Image
        pal = [(0, 0, 0), (144, 112, 160), (208, 144, 192), (240, 176, 208), (240, 192, 224),
               (240, 208, 224), (240, 224, 240), (240, 240, 240), (224, 224, 240), (208, 208, 240),
               (192, 192, 240), (176, 176, 240), (144, 144, 224), (112, 112, 160), (240, 128, 32),
               (0, 48, 96)]
        im = Image.new('RGB', (80, 36))
        for k, n in enumerate(sorted(imgs)):
            for y in range(16):
                for x in range(80):
                    im.putpixel((x, k * 20 + y), pal[imgs[n][y][x]])
        im.resize((480, 216), Image.NEAREST).save(argv[argv.index('--preview') + 1])
    open(argv[1], 'wb').write(emi)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
