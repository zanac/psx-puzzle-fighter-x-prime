"""Zangief's stage on the arcade set: Pocket Fighter's castle as an SPF2T stage,
from the user's Pocket Fighter arcade set (sgemf).

Pocket Fighter (arcade) draws the castle stage on three layers; the stage
index (0xFF8180) is 12. Each layer is filled at match setup from a block list
per stage (the same scheme as SPF2T):
  scroll3 (sky, moon): list 0x2045A, 64 bytes; block n = 64 cells at
           0x276300 + n * 0x100, code + 0x690; 32x32 tiles
  scroll1 (floating castle): list 0x202B2, 4 superblocks; superblock n = 8x8
           words at 0x23B280 + n * 0x80 (column after column), each a 4x4
           cell metatile at 0x23DC80 + word * 0x40; 8x8 tiles
  scroll2 (statue, steps, wagon): list 0x20342, 16 bytes; block n = 256 cells
           at 0x258B00 + n * 0x400, code + 0x4440; 16x16 tiles
(list = table + word[table + stage * 2]; a cell is two words: code, attribute
with the palette in bits 0-4 and the flips in bits 5-6; colour 15 is
transparent.) The palettes, 32 per layer, 12-bit RGB: scroll1 0x21D114, scroll2
0x2215D0, scroll3 0x227ACC. Graphics: scroll2 code c is tile 0x10000 + c,
scroll3 32x32 tile 0x4000 + c, scroll1 8x8 tile 0x20000 + c (the right half of
16x16 tile c / 2, top or bottom).

The picture is composed as on the PSX (tools/pf_stage.py, which uses the PSX
files): the layers' 512x256 parts the match camera shows, aligned on the PSX
composition (sky from scroll3 (0, 1792), castle from scroll1 (0, 255),
foreground from scroll2 (0, 766): the PSX layers' offsets are already in
these), scaled by 0.75 and cut to the 384x96 band.

SPF2T: the stage of the match is scroll2, the frames of the wells included;
0x17ADC fills the 16 blocks of scroll2 from the list 0x17D08 + word[0x17D08 +
stage * 2] (block n at 0xC5880 + n * 0x400, code + 0x5800). The picture of
each screen is a 24x6 cell band at rows 5-10 of two blocks side by side; the
cells over the wells use palettes 16-30, darker copies of 0-14. The castle
replaces Dan's stage (stage 20) when code_castle.s says so: Dan's blocks with
the band cells replaced, as new blocks 0x89-, its own palette block (Dan's,
with 0-14 the castle's and 16-30 their darker copies), no stage objects and
Pocket Fighter's castle music (song 24)."""
import struct
import numpy as np

PF_STAGE = 12                         # 0xFF8180: stage 6 * 2
PF_S1 = (0x202B2, 0x23B280, 0x23DC80, 0x21D114)
PF_S2 = (0x20342, 0x258B00, 0x4440, 0x2215D0)
PF_S3 = (0x2045A, 0x276300, 0x690, 0x227ACC)
CAMERA = {'s3': (0, 1792), 's1': (0, 255), 's2': (0, 766)}
SCALE, TOP = 0.75, 36
W, H = 384, 96

SPF_LIST = 0x17D08
SPF_LIB = 0xC5880
SPF_CODE = 0x5800
DAN_STAGE = 20
BAND_ROW = 5
FIRST_BLOCK = 0x89                    # free: 0xE7C80- in pzf.04 (32 blocks)
N_PALS = 15                           # 0-14 (15 and 31: the frames)
DIM = (0.55, 0.5, 0.55)               # 16-30 = 0-14 darker (as SPF2T's stages)

CPAL = 0xB2E00                        # palette block (0x400) (code_castle.s)
CLIST = 0xB3202                       # word 0x16 at CLIST - 2, then the list

def W16(b, a): return struct.unpack('>H', b[a:a + 2])[0]

def _list(prog, table, n):
    a = table + W16(prog, table + PF_STAGE)
    return prog[a:a + n]

def _pal(prog, a):
    w = struct.unpack('>512H', prog[a:a + 1024])
    return np.array([[((x >> 8) & 15) * 17, ((x >> 4) & 15) * 17, (x & 15) * 17] for x in w],
                    np.uint8).reshape(32, 16, 3)

def _put(img, mask, t, attr, pal, y, x):
    if attr & 0x20: t = t[:, ::-1]
    if attr & 0x40: t = t[::-1]
    m = t != 15
    n = t.shape[0]
    sub = img[y:y + n, x:x + n]; sm = mask[y:y + n, x:x + n]
    sub[m] = pal[attr & 0x1F][t][m]; sm[m] = True

def layers(prog, G):
    """the three layers' maps from ROM: name -> (RGB, opaque mask)"""
    out = {}
    # scroll2: 4x4 blocks of 16x16 cells
    table, lib, add, pa = PF_S2
    pal = _pal(prog, pa)
    img = np.zeros((1024, 1024, 3), np.uint8); mask = np.zeros((1024, 1024), bool)
    for k, n in enumerate(_list(prog, table, 16)):
        for i in range(256):
            code, attr = struct.unpack('>HH', prog[lib + n * 0x400 + 4 * i:lib + n * 0x400 + 4 * i + 4])
            c = (0x10000 + ((code + add) & 0xFFFF))
            t = G.px[c * 256:(c + 1) * 256].reshape(16, 16)
            _put(img, mask, t, attr, pal, (16 * (k >> 2) + (i & 15)) * 16, (16 * (k & 3) + (i >> 4)) * 16)
    out['s2'] = (img, mask)
    # scroll3: 8x8 blocks of 8x8 cells of 32x32
    table, lib, add, pa = PF_S3
    pal = _pal(prog, pa)
    img = np.zeros((2048, 2048, 3), np.uint8); mask = np.zeros((2048, 2048), bool)
    for k, n in enumerate(_list(prog, table, 64)):
        for i in range(64):
            code, attr = struct.unpack('>HH', prog[lib + n * 0x100 + 4 * i:lib + n * 0x100 + 4 * i + 4])
            c = 0x4000 + ((code + add) & 0xFFFF)
            t = G.px[c * 1024:(c + 1) * 1024].reshape(32, 32)
            _put(img, mask, t, attr, pal, (8 * (k >> 3) + (i & 7)) * 32, (8 * (k & 7) + (i >> 3)) * 32)
    out['s3'] = (img, mask)
    # scroll1: 2x2 superblocks of 8x8 metatiles of 4x4 cells of 8x8
    table, sup, meta, pa = PF_S1
    pal = _pal(prog, pa)
    img = np.zeros((512, 512, 3), np.uint8); mask = np.zeros((512, 512), bool)
    for s, n in enumerate(_list(prog, table, 4)):
        for j in range(64):
            w = W16(prog, sup + n * 0x80 + 2 * j)
            my, mx = j & 7, j >> 3
            for q in range(16):
                code, attr = struct.unpack('>HH', prog[meta + w * 0x40 + 4 * q:meta + w * 0x40 + 4 * q + 4])
                c = 0x20000 + code
                t = G.px[(c // 2) * 256:(c // 2 + 1) * 256].reshape(16, 16)[(c % 2) * 8:(c % 2) * 8 + 8, 8:16]
                cy, cx = q & 3, q >> 2
                _put(img, mask, t, attr, pal, 256 * (s >> 1) + my * 32 + cy * 8, 256 * (s & 1) + mx * 32 + cx * 8)
    out['s1'] = (img, mask)
    return out

def compose(prog, G):
    """the castle as the PSX version shows it: 384x96 RGB (PIL image)"""
    from PIL import Image
    L = layers(prog, G)
    pic = np.zeros((256, 512, 3), np.uint8)
    for name in ('s3', 's1', 's2'):
        img, mask = L[name]
        x, y = CAMERA[name]
        m = mask[y:y + 256, x:x + 512]
        pic[m] = img[y:y + 256, x:x + 512][m]
    im = Image.fromarray(pic).resize((round(512 * SCALE), round(256 * SCALE)), Image.LANCZOS)
    return im.crop((0, TOP, W, TOP + H))

def _c4(c): return tuple(min(15, (v + 8) // 17) for v in c)

def quantise(im, n_pals=N_PALS):
    """144 cells, each a 16x16 tile of colours 0-14 in one of n_pals palettes
    (4-bit RGB) -> (tiles, palette per cell, palettes)"""
    import pf_stage as P
    rgb = np.array(im.convert('RGB'))
    cells = []
    for ty in range(H // 16):
        for tx in range(W // 16):
            b = rgb[ty * 16:ty * 16 + 16, tx * 16:tx * 16 + 16].reshape(-1, 3)
            cells.append([tuple(int(v) for v in p) for p in b])
    means = [tuple(sum(p[c] for p in t) // 256 for c in range(3)) for t in cells]
    groups = P._quant(means, n_pals)
    assign = [P._nearest(groups, m)[0] for m in means]
    for _ in range(4):
        pals = []
        for g in range(n_pals):
            pix = [p for t, a in zip(cells, assign) if a == g for p in t]
            q = P._quant(pix, 15) if pix else [(0, 0, 0)] * 15
            pals.append([tuple(v * 17 for v in _c4(c)) for c in q[:15]])
        cache = {}
        def err(t, g):
            s = 0
            for p in t:
                k = (g, p)
                if k not in cache: cache[k] = P._nearest(pals[g], p)[1]
                s += cache[k]
            return s
        assign = [min(range(n_pals), key=lambda g: err(t, g)) for t in cells]
    tiles = [np.array([P._nearest(pals[a], p)[0] for p in t], np.uint8).reshape(16, 16)
             for t, a in zip(cells, assign)]
    return tiles, assign, pals

def _word(c, k=(1, 1, 1)):
    r, g, b = (min(15, int(round(v / 17 * f))) for v, f in zip(c, k))
    return r << 8 | g << 4 | b

def build(spfprog, pfprog, pfgfx, tile0):
    """-> (data patches [(address, bytes)], new tiles (16x16 index arrays),
    preview image). tile0 = scroll2 code of the first new tile."""
    im = compose(pfprog, pfgfx)
    tiles, assign, pals = quantise(im)
    # the new tiles (identical cells share one)
    uniq, code = {}, []
    new = []
    for t in tiles:
        k = t.tobytes()
        if k not in uniq:
            uniq[k] = tile0 + len(new); new.append(t)
        code.append(uniq[k])
    # palettes: Dan's block, 0-14 and 16-30 replaced
    pa = 0xA22C0 + DAN_STAGE * 0x200
    pb = list(struct.unpack('>512H', spfprog[pa:pa + 0x400]))
    for g, p in enumerate(pals):
        pb[g * 16:g * 16 + 16] = [_word(c) for c in p] + [0]
        pb[(g + 16) * 16:(g + 16) * 16 + 16] = [_word(c, DIM) for c in p] + [0]
    # blocks: Dan's, the band cells of every screen replaced
    la = SPF_LIST + W16(spfprog, SPF_LIST + DAN_STAGE)
    dan = list(spfprog[la:la + 16])
    lst = list(dan)
    blocks = []
    nb = FIRST_BLOCK
    for k in range(0, 16, 2):
        if dan[k] == 0 and dan[k + 1] == 0: continue
        for half in (0, 1):
            src = SPF_LIB + dan[k + half] * 0x400
            blk = bytearray(spfprog[src:src + 0x400])
            for col in range(16 if half == 0 else 8):
                cx = col + 16 * half
                for row in range(6):
                    i = (BAND_ROW + row) | (col << 4)
                    attr = W16(blk, 4 * i + 2)
                    dim = 16 if (attr & 0x1F) >= 16 else 0
                    c = row * 24 + cx
                    blk[4 * i:4 * i + 4] = struct.pack('>HH', (code[c] - SPF_CODE) & 0xFFFF, assign[c] + dim)
            lst[k + half] = nb; nb += 1
            blocks.append(bytes(blk))
    assert nb <= FIRST_BLOCK + 32
    patches = [(CPAL, struct.pack('>512H', *pb)),
               (CLIST - 2, struct.pack('>H', 0x16) + bytes(lst)),
               (SPF_LIB + FIRST_BLOCK * 0x400, b''.join(blocks))]
    return patches, new, im
