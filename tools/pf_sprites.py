#!/usr/bin/env python3
"""Pocket Fighter (PSX, SLUS-00653) character sprites.

PLAYER/<NAME>.PAC is a container:
  u32 count, u32 total size, then count x (u32 type, u32 size);
  entries are 0x800-aligned, starting at 0x800.
  type 0: compressed 16x16 4bpp cells (decoder at RAM 0x80192C34)
  type 1: u32 table; the first records are frames (3 words each)
  type 2: 16-colour BGR555 palettes (32 bytes each)

Frame record (12 bytes): u16 index, u8 w, u8 h (in 16 px cells), u16 x, u16 y
(anchor), u16 cells, u16 flags. At table[index]: a bit mask of the w*h cells
that are present, (w*h+31)/32 words, read byte by byte, MSB first, cells in
column-major order. Then one word per present cell: offset into type 0
(bits 0-23), palette offset (bits 24-28), flip (bits 30-31: 1 = vertical,
2 = horizontal).

Cell stream: flag byte, bits LSB first. 0 = literal byte. 1 = control byte
c: d = c >> 4, n = c & 15; d != 0: copy n bytes from d back (n may be 0);
d == 0: repeat the next byte n + 1 times. A cell is 128 bytes (16x16 4bpp).

usage: pf_sprites.py PAC OUTDIR [--pal N] [--sheet]
"""
import os, struct, sys

def pac_entries(d):
    n = struct.unpack_from('<I', d, 0)[0]
    out, off = {}, 0x800
    for i in range(n):
        t, s = struct.unpack_from('<II', d, 8 + 8 * i)
        out[t] = d[off:off + s]
        off += (s + 0x7FF) & ~0x7FF
    return out

def cell(data, off):
    out = bytearray()
    flags = bits = 0
    while len(out) < 128:
        if bits == 0:
            flags = data[off]; off += 1; bits = 8
        if flags & 1:
            c = data[off]; off += 1
            dist, n = c >> 4, c & 15
            if dist:
                for _ in range(n):              # n == 0: nothing
                    out.append(out[-dist] if dist <= len(out) else 0)
            else:
                v = data[off]; off += 1
                out += bytes([v]) * (n + 1)
        else:
            out.append(data[off]); off += 1
        flags >>= 1; bits -= 1
    return out[:128] + bytes(max(0, 128 - len(out)))

def cell_pixels(raw, flip):
    px = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            b = raw[y * 8 + x // 2]
            px[y][x] = (b >> 4) if x & 1 else (b & 15)
    if flip & 1:                        # routine 0x80192D34: rows reversed
        px = px[::-1]
    if flip & 2:                        # routine 0x80192D84: columns reversed
        px = [row[::-1] for row in px]
    return px

def frames(pac):
    e = pac_entries(pac)
    tbl = e[1]
    words = struct.unpack_from('<%dI' % (len(tbl) // 4), tbl)
    recs = []
    for i in range(0, len(tbl) - 11, 12):
        idx, w, h, x, y, n, fl = struct.unpack_from('<HBBHHHH', tbl, i)
        if not (w and h) or w > 16 or h > 16:
            break
        recs.append((idx, w, h, x, y, n, fl))
    return e, words, recs

def render(e, words, rec):
    """Pixels as (palette_offset << 4 | colour) per pixel, 0 = transparent.
    Drawing code: RAM 0x80191D50."""
    idx, w, h, x, y, n, fl = rec
    nmask = (w * h + 31) >> 5
    maskb = b''.join(struct.pack('<I', words[idx + i]) for i in range(nmask))
    img = [[0] * (w * 16) for _ in range(h * 16)]
    k = 0
    for c in range(w * h):                      # column-major
        if not (maskb[c >> 3] << (c & 7)) & 0x80:   # MSB first
            continue
        wd = words[idx + nmask + k]; k += 1
        if (wd & 0xFFFFFF) >= len(e[0]):
            continue                    # cell outside this bank
        px = cell_pixels(cell(e[0], wd & 0xFFFFFF), wd >> 30)
        po = (wd >> 24) & 0x1F          # palette offset of the cell
        cx, cy = (c // h) * 16, (c % h) * 16
        for yy in range(16):
            img[cy + yy][cx:cx + 16] = [(po << 4 | v) if v else 0 for v in px[yy]]
    return img

def palette(e, n, count=1):
    p = e[2][n * 32:(n + count) * 32]
    cols = []
    for i in range(16 * count):
        v = struct.unpack_from('<H', p, i * 2)[0]
        cols.append(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3))
    return cols

def main(argv):
    from PIL import Image
    src, out = argv[0], argv[1]
    pal = int(argv[argv.index('--pal') + 1]) if '--pal' in argv else 0
    os.makedirs(out, exist_ok=True)
    e, words, recs = frames(open(src, 'rb').read())
    cols = palette(e, pal, 16)
    flat = [c for rgb in cols for c in rgb]
    ims = []
    for i, r in enumerate(recs):
        img = render(e, words, r)
        im = Image.new('P', (len(img[0]), len(img)))
        im.putdata([v & 0xFF for row in img for v in row])
        im.putpalette(flat + [0] * (768 - len(flat)))
        im.info['transparency'] = 0
        im.save(os.path.join(out, 'f%03d.png' % i))
        ims.append(im)
    if '--sheet' in argv:
        cw, chh, cols_n = 132, 132, 20
        rows = (len(ims) + cols_n - 1) // cols_n
        sheet = Image.new('RGB', (cw * cols_n, chh * rows), (40, 40, 60))
        for i, im in enumerate(ims):
            t = im.convert('RGBA')
            sheet.paste(t, ((i % cols_n) * cw + 2, (i // cols_n) * chh + 2), t)
        sheet.save(os.path.join(out, 'sheet.png'))
    print('%d frames' % len(recs))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
