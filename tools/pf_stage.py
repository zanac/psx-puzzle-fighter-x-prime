#!/usr/bin/env python3
"""Zangief's stage: Pocket Fighter's castle (STAGE/ST06.PAC) as an SPF2T
stage file (DATA/STAGEnn.EMI).

Pocket Fighter STAGE/STnn.PAC (container as in pf_sprites.py):
  type 5:   palettes, 16 colours each (BGR555)
  type 6:   tile map, in blocks of 16x16 entries (256x256 px), row-major;
            entry: tile = bits 0-10, palette = bits 11-15 (+ layer base)
  type 257: 16x16 4bpp tiles, 128 bytes each
In a match on the castle the camera shows three layers, back to front:
  sky and moon (blocks 12, 13, palette base 64, y -10),
  floating castle (blocks 2, 3, base 0, y -9),
  statue, steps and wagon (blocks 6, 7, base 32, y -8),
the two blocks of each layer side by side from x = 0 (traced from the
game's display list in an emulator; the witch silhouette is a sprite and
is not included).

SPF2T STAGEnn.EMI (5 entries, header: per entry u32 size, params, and the
first 4 bytes of the entry, which the loader checks):
  0: VRAM page (768, 256), 256 tiles 16x16 4bpp, 16 per row
  1: VRAM page (832, 256), shared graphics (kept from the template)
  2: tile map, 24 x 16 halfwords: tile (bits 0-7) | palette << 8;
     rows 0-5 are the 384x96 picture the match shows
  3: 32 palettes (bank 1): the picture's in 0-14 and 16-28; 29-31 kept from
     the template; 15 is the rock texture of the well frames (page 1): the
     template's, recoloured lilac (colours 1-12) to suit the castle
  4: 32 palettes (bank 2), kept from the template

The castle's music is Pocket Fighter's KYOKU/XA00.XA, channel 6: 8
interleaved channels of stereo 37.8 kHz XA ADPCM, one song per channel
(stage n = channel n), the same layout as SPF2T's STR/ORGnn.XA. The new file
is copied sector by sector from the first sector to the last one of
channel 6, so the interleave and the channel number stay as they are; the
other channels' audio is zeroed (silence; the player never decodes them).
Output: 2336 bytes per sector (subheader twice, data, EDC), the form
tools/discexpand.py writes for a *.XA file.

usage: pf_stage.py ST06.PAC TEMPLATE_STAGE.EMI OUT.EMI [--scale S] [--top Y]
       [--left X] [--png PREVIEW.png]
       pf_stage.py music PF_IMAGE OUT.XA [REMIX.wav]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

W, H = 384, 96
LAYERS = ((64, (12, 13), -10), (0, (2, 3), -9), (32, (6, 7), -8))
PAL_SLOTS = list(range(15)) + list(range(16, 29))   # as the stages use them
N_PALS = len(PAL_SLOTS)
FILLER = 31 << 8        # rows 6-15: tile 0 (blank: colour 0 is transparent)
DEF_SCALE, DEF_TOP, DEF_LEFT = 0.75, 36, 0

def pac_entries(d):
    n = struct.unpack_from('<I', d, 0)[0]
    out, off = {}, 0x800
    for i in range(n):
        t, s = struct.unpack_from('<II', d, 8 + 8 * i)
        out[t] = d[off:off + s]
        off += (s + 0x7FF) & ~0x7FF
    return out

def rgb(c):
    return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)

def compose(pac):
    """the castle as the match camera shows it, 512x256 RGB"""
    from PIL import Image
    e = pac_entries(pac)
    tm = struct.unpack_from('<%dH' % (len(e[6]) // 2), e[6])
    pal = struct.unpack_from('<%dH' % (len(e[5]) // 2), e[5])
    tiles = e[257]
    im = Image.new('RGB', (512, 256))
    px = im.load()
    for base, blocks, oy in LAYERS:
        for k, b in enumerate(blocks):
            for i in range(256):
                v = tm[b * 256 + i]
                t, p = v & 0x7FF, base + (v >> 11)
                X, Y = k * 256 + (i % 16) * 16, (i // 16) * 16 + oy + 10
                for y in range(16):
                    if not 0 <= Y + y < 256:
                        continue
                    row = tiles[t * 128 + y * 8:t * 128 + y * 8 + 8]
                    for x in range(16):
                        n = (row[x >> 1] >> (4 * (x & 1))) & 15
                        if n:
                            px[X + x, Y + y] = rgb(pal[p * 16 + n])
    return im

def crop(im, scale, top, left):
    from PIL import Image
    if scale != 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    return im.crop((left, top, left + W, top + H))

def _quant(pixels, n=16):
    from PIL import Image
    strip = Image.new('RGB', (len(pixels), 1))
    strip.putdata(pixels)
    q = strip.quantize(colors=n, method=Image.Quantize.MAXCOVERAGE, kmeans=3)
    p = q.getpalette()[:3 * n]
    cols = [tuple(p[i:i + 3]) for i in range(0, len(p), 3)]
    while len(cols) < n:
        cols.append(cols[-1] if cols else (0, 0, 0))
    return cols

def _nearest(cols, c):
    best, bi = 1 << 30, 0
    for i, k in enumerate(cols):
        dd = (k[0] - c[0]) ** 2 + (k[1] - c[1]) ** 2 + (k[2] - c[2]) ** 2
        if dd < best:
            best, bi = dd, i
    return bi, best

def to_tiles(im):
    """144 tiles, each with one of N_PALS 16-colour palettes"""
    tiles = []
    for ty in range(H // 16):
        for tx in range(W // 16):
            b = im.crop((tx * 16, ty * 16, tx * 16 + 16, ty * 16 + 16)).convert('RGB').tobytes()
            tiles.append([tuple(b[i:i + 3]) for i in range(0, 768, 3)])
    # first grouping: by mean colour
    means = [tuple(sum(p[c] for p in t) // 256 for c in range(3)) for t in tiles]
    groups = _quant(means, N_PALS)
    assign = [_nearest(groups, m)[0] for m in means]
    pals = None
    for _ in range(4):
        pals = []
        for g in range(N_PALS):
            pix = [p for t, a in zip(tiles, assign) if a == g for p in t]
            pals.append(_quant(pix) if pix else [(0, 0, 0)] * 16)
        cache = {}
        def err(t, g):
            s = 0
            for p in t:
                k = (g, p)
                if k not in cache:
                    cache[k] = _nearest(pals[g], p)[1]
                s += cache[k]
            return s
        assign = [min(range(N_PALS), key=lambda g: err(t, g)) for t in tiles]
    idx = [[_nearest(pals[a], p)[0] for p in t] for t, a in zip(tiles, assign)]
    return idx, assign, pals

def bgr(c):
    v = (c[0] >> 3) | ((c[1] >> 3) << 5) | ((c[2] >> 3) << 10)
    return v or 0x0421          # 0x0000 would be transparent

FRAME_PAL = 15

def lilac(c):
    """lighter, lilac version of a BGR555 colour (the well frame)"""
    r, g, b = c & 31, (c >> 5) & 31, (c >> 10) & 31
    l = 0.3 * r + 0.59 * g + 0.11 * b
    l += (31 - l) * 0.30
    r, g, b = (max(0, min(31, round(l * k))) for k in (0.98, 0.88, 1.10))
    return (r | g << 5 | b << 10) or 0x0421

def emi_entries(d):
    out, off = [], 0x800
    n = struct.unpack_from('<I', d, 0)[0]
    for i in range(1, n + 1):
        size = struct.unpack_from('<I', d, 16 * i)[0]
        out.append((off, size))
        off += (size + 0x7FF) & ~0x7FF
    return out

def build(pac, template, scale=DEF_SCALE, top=DEF_TOP, left=DEF_LEFT, png=None):
    img = crop(compose(pac), scale, top, left)
    if png:
        img.save(png)
    idx, assign, pals = to_tiles(img)
    out = bytearray(template)
    ents = emi_entries(out)
    assert len(ents) == 5 and [s for o, s in ents] == [0x8000, 0x8000, 0x300, 0x400, 0x400]
    page = bytearray(0x8000)             # tile 0 stays blank
    uniq, tmap = {}, []
    for t, a in zip(idx, assign):
        key = (bytes(t), a)
        if key not in uniq:
            n = len(uniq) + 1
            assert n < 256
            uniq[key] = n
            x0, y0 = (n % 16) * 16, (n // 16) * 16
            for y in range(16):
                for x in range(0, 16, 2):
                    page[(y0 + y) * 128 + (x0 + x) // 2] = t[y * 16 + x] | (t[y * 16 + x + 1] << 4)
        tmap.append(uniq[key] | (PAL_SLOTS[a] << 8))
    tmap += [FILLER] * (24 * 16 - len(tmap))
    po = ents[0][0]
    out[po:po + 0x8000] = page
    struct.pack_into('<384H', out, ents[2][0], *tmap)
    for slot, p in zip(PAL_SLOTS, pals):
        struct.pack_into('<16H', out, ents[3][0] + slot * 32, *[bgr(c) for c in p])
    fo = ents[3][0] + FRAME_PAL * 32
    frame = list(struct.unpack_from('<16H', out, fo))
    frame[1:13] = [lilac(c) for c in frame[1:13]]
    struct.pack_into('<16H', out, fo, *frame)
    for i, (o, s) in enumerate(ents):      # the loader checks these
        out[16 * (i + 1) + 8:16 * (i + 1) + 12] = out[o:o + 4]
    return bytes(out), len(uniq)

XA_PATH, XA_CHANNEL = '/KYOKU/XA00.XA', 6
RMX_CHANNEL = 7

def build_music(pf_image, remix=None):
    """-> (2336-byte units, sectors of the song)"""
    import discout, discpatch as D
    img = discout.load(pf_image).img
    lba, size = D.iso_find(img, XA_PATH)
    secs = [img.get(lba + i) for i in range(size // 2048)]
    mine = [i for i, x in enumerate(secs) if x[17] == XA_CHANNEL and x[18] & 4]
    out = bytearray()
    for i in range(mine[-1] + 1):
        x = bytearray(secs[i][16:16 + 2336])
        if x[1] != XA_CHANNEL and x[2] & 4:          # another song: silence
            x[8:2336] = bytes(2328)
        out += x
    # the player's end is first + 8 * length: pad past it with silence
    end = mine[0] + 8 * len(mine) + 8
    pad = bytes([1, 7, 0x64, 1]) * 2 + bytes(2328)
    out += pad * (end - len(out) // 2336)
    # channel 7 (an unused song of XA00, now silent) gets the remix, played
    # with the arranged music on (src/zangief.asm xp_songent), or else a copy
    # of channel 6: the same number of sectors either way
    def chan(c):
        return [i for i in range(len(out) // 2336)
                if out[i * 2336 + 1] == c and out[i * 2336 + 2] & 4]
    src, dst = chan(XA_CHANNEL), chan(RMX_CHANNEL)
    assert len(dst) >= len(src) == len(mine)
    if remix is not None:
        import xa
        bodies = xa.encode(remix)[:len(src)]
        bodies += [bytes(2304)] * (len(src) - len(bodies))
    else:
        bodies = [bytes(out[i * 2336 + 8:i * 2336 + 8 + 2304]) for i in src]
    for i, b in zip(dst, bodies):
        out[i * 2336 + 8:i * 2336 + 8 + 2304] = b
    return bytes(out), len(mine)

def main(a):
    if a[0] == 'music':
        remix = None
        if len(a) > 3:
            import wave, numpy as np
            w = wave.open(a[3])
            assert w.getframerate() == 37800 and w.getnchannels() == 2
            remix = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2)
        data, n = build_music(a[1], remix)
        open(a[2], 'wb').write(data)
        print('%s: %d sectors, song %d sectors' % (a[2], len(data) // 2336, n))
        return
    opts = {'--scale': DEF_SCALE, '--top': DEF_TOP, '--left': DEF_LEFT, '--png': None}
    pos = []
    i = 0
    while i < len(a):
        if a[i] in opts:
            opts[a[i]] = a[i + 1]
            i += 2
        else:
            pos.append(a[i])
            i += 1
    pac, tpl, dst = pos
    data, n = build(open(pac, 'rb').read(), open(tpl, 'rb').read(),
                    float(opts['--scale']), int(opts['--top']), int(opts['--left']), opts['--png'])
    open(dst, 'wb').write(data)
    print('%s: %d tiles' % (dst, n))

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
