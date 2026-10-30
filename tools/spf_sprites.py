#!/usr/bin/env python3
"""Super Puzzle Fighter II Turbo (PSX) in-match character sprites.

DATA/PLxx_OBJ.EMI has two entries:
  entry 0: LZ graphics (codec: lzh.py, decoder 0x8010D5C0), loaded into the
           player's 0x48000-byte buffer (P1 0x80024000, P2 0x8006C000);
  entry 1: 44-byte frame records, loaded at 0x800E7600 (P1) / 0x800EBB00 (P2),
           room for 0x4500 bytes each.
Frame record: u32 offset in entry 0, s16 x, s16 y (anchor, e.g. -32,-63),
u8 rows, u8 columns (16 px cells), u8 units (decoded size / 128 bytes), u8 flags,
cell mask from +12 as big-endian-ordered words (bit 31 of +12 = first cell,
then +16), row-major (drawing loop 0x8010CCDC: rows outer, columns inner).
The decoded stream is a 256-px-wide 4bpp strip of the present cells, left to
right (uploaded by 0x8010D558).

usage: spf_sprites.py PLxx_OBJ.EMI OUTDIR   (grayscale sheet; no CLUT yet)
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzh

def entries(emi):
    n = struct.unpack_from('<I', emi, 4)[0]
    out, off = [], 0x800
    for i in range(1, 16):
        rec = emi[i * 16:i * 16 + 16]
        size = struct.unpack_from('<I', rec, 0)[0]
        if rec[:4] == b'....' or size == 0 or size > len(emi):
            break
        out.append(emi[off:off + size])
        off += (size + 0x7FF) & ~0x7FF
    return out

def records(e1):
    return [e1[i:i + 44] for i in range(0, len(e1) - 43, 44)]

def frame(e0, r):
    off, x, y, h, w, u, fl = struct.unpack_from('<IhhBBBB', r, 0)
    nw = (w * h + 31) // 32
    mask = 0
    for i in range(nw):
        mask = mask << 32 | struct.unpack_from('<I', r, 12 + 4 * i)[0]
    top = nw * 32 - 1
    hw, _ = lzh.decode(e0, off)
    rows = lzh.to_pixels(hw, 256, max(16, u))   # 128 bytes = one 256-px row
    cells = []
    for sy in range(0, len(rows), 16):
        for sx in range(0, 256, 16):
            cells.append([row[sx:sx + 16] for row in rows[sy:sy + 16]])
    px = [[0] * (w * 16) for _ in range(h * 16)]
    k = 0
    for c in range(w * h):
        if not (mask >> (top - c)) & 1:
            continue
        cx, cy = c % w, c // w
        if k < len(cells):
            for yy in range(16):
                px[cy * 16 + yy][cx * 16:cx * 16 + 16] = cells[k][yy]
        k += 1
    return (x, y), px

def main(src, out):
    from PIL import Image
    os.makedirs(out, exist_ok=True)
    e0, e1 = entries(open(src, 'rb').read())[:2]
    recs = records(e1)
    sheet = Image.new('L', (12 * 132, ((len(recs) + 11) // 12) * 132), 40)
    for i, r in enumerate(recs):
        _, px = frame(e0, r)
        im = Image.new('L', (len(px[0]), len(px)))
        im.putdata([v * 16 for row in px for v in row])
        sheet.paste(im, ((i % 12) * 132, (i // 12) * 132))
    sheet.save(os.path.join(out, 'sheet.png'))
    print('%d frame records' % len(recs))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    main(*sys.argv[1:])
