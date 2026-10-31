"""Counter Gem preview of a drop pattern on the arcade select screen.

Each character has a 5x5 list of 8x8 scroll1 tiles at PREVIEW + 0x11E*char
(long: code<<16 | attribute). The 3x5 inner tiles draw the first 4 rows of the
pattern as staggered gems. Which pixel shows which cell, and in which colour,
is learnt from the other characters (their pattern and their picture), so a
new pattern can be drawn without any hand-made graphics."""
import struct
from collections import Counter
import numpy as np

PREVIEW = 0x87D80
PATTERNS = 0x10188

def code8(G, c):
    """8x8 scroll1 tile c: right half of 16x16 tile c//2, top or bottom"""
    return G.tile(c // 2)[(c % 2) * 8:(c % 2) * 8 + 8, 8:16]

def set_code8(G, c, a):
    t = G.tile(c // 2).copy()
    t[(c % 2) * 8:(c % 2) * 8 + 8, 8:16] = a
    G.set_tile(c // 2, t)

def entries(prog, ch):
    a = PREVIEW + 0x11E * ch
    return list(struct.unpack('>25I', prog[a:a + 100]))

def picture(G, prog, ch):
    im = np.zeros((40, 40), np.uint8)
    for i, e in enumerate(entries(prog, ch)):
        im[(i // 5) * 8:(i // 5) * 8 + 8, (i % 5) * 8:(i % 5) * 8 + 8] = code8(G, e >> 16)
    return im

def pattern(prog, ch):
    w = struct.unpack('>96H', prog[PATTERNS + ch * 0xC0:PATTERNS + ch * 0xC0 + 0xC0])
    return [w[r * 8:r * 8 + 6] for r in range(4)]

def learn(G, prog, chars):
    pics = [picture(G, prog, c) for c in chars]
    pats = [pattern(prog, c) for c in chars]
    model = {}
    for y in range(40):
        for x in range(40):
            vals = [p[y, x] for p in pics]
            if len(set(vals)) == 1:
                model[y, x] = None; continue
            best = None
            for r in range(4):
                for c in range(6):
                    f = {}
                    for k, v in enumerate(vals): f.setdefault(pats[k][r][c], Counter())[v] += 1
                    score = sum(max(m.values()) for m in f.values())
                    if best is None or score > best[0]:
                        best = (score, r, c, {col: m.most_common(1)[0][0] for col, m in f.items()})
            model[y, x] = best[1:]
    return model

def draw(G, prog, ch, newpat, model):
    # a colour never seen at some pixel: translate from the colours seen there,
    # by how pixel values of one colour pair with those of another elsewhere
    trans = {}
    for m in model.values():
        if m is None: continue
        for ca, va in m[2].items():
            for cb, vb in m[2].items():
                trans.setdefault((ca, va, cb), Counter())[vb] += 1
    im = picture(G, prog, ch)
    for (y, x), m in model.items():
        if m is None: continue
        r, c, f = m
        col = newpat[r][c]
        if col in f:
            im[y, x] = f[col]; continue
        votes = Counter()
        for ca, va in f.items(): votes.update(trans.get((ca, va, col), Counter()))
        if not votes: raise SystemExit('preview: colour %d never seen at cell %d,%d' % (col, r, c))
        im[y, x] = votes.most_common(1)[0][0]
    return im

def install(G, prog, ch, im, free):
    """reuse identical tiles where they exist, else take codes from `free`;
    returns the new 25 entries (bytes, big endian)"""
    T = G.px.reshape(-1, 16, 16)
    t8 = np.stack([T[:, 0:8, 8:16], T[:, 8:16, 8:16]], 1).reshape(-1, 8, 8)
    have = {}
    for c in range(len(t8) - 1, -1, -1):
        if c not in free: have[t8[c].tobytes()] = c
    free = list(free); out = []
    for i, e in enumerate(entries(prog, ch)):
        blk = np.ascontiguousarray(im[(i // 5) * 8:(i // 5) * 8 + 8, (i % 5) * 8:(i % 5) * 8 + 8])
        c = have.get(blk.tobytes())
        if c is None:
            c = free.pop(0); set_code8(G, c, blk); have[blk.tobytes()] = c
        out.append((c << 16) | (e & 0xffff))
    return struct.pack('>25I', *out)
