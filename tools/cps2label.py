"""The match HUD name (scroll1, 8 columns x 2 rows of 8x8 tiles per player side)
for ZANGIEF, assembled from the other names' letters plus a Z drawn in the same
italic, outlined style. Same method as the PSX (tools/labels.py hud_name): the
arcade labels have the PSX coordinates, in other colours.

Name lists: 0x84560 (word offsets per variant) -> 16 bytes per character and
side (char * 2 + side): +4 the list: word, word, word columns-1, then per column
top code, top attr, bottom code, bottom attr."""
import struct
import numpy as np
import cps2preview

NAMES = 0x84560
CHAR = {'MORRIGAN': 0, 'KEN': 3, 'LEI': 4, 'FELICIA': 6, 'DAN': 10}
# letter: (label, first column, end column at the bottom row (11))
GLYPHS = {'A': ('DAN', 17, 26), 'N': ('DAN', 25, 34), 'G': ('MORRIGAN', 37, 46),
          'I': ('LEI', 17, 22), 'E': ('LEI', 8, 18), 'F': ('FELICIA', 3, 11)}
LIGHTNING = (0x9, 0xA)            # behind short names
OUTLINE = (0x8, 0xD, 0xC, 0xB, 0x0)
CLEAR = 0xF                       # transparent
Z = ["          ",
     "          ",
     "8888888888",
     "8444444448",
     "8888886448",
     "     d64d ",
     "    d53d  ",
     "   d33d   ",
     "  c63c    ",
     " c42ccccc ",
     "c222222222",
     "b111111111",
     " bbbbbbbbb",
     " 000000000",
     "  0000000 ",
     "          "]

def slant(y): return (11 - y) // 3

class Labels:
    def __init__(self, G, prog, variant=2):
        self.G, self.d = G, prog
        W = lambda a: struct.unpack('>H', prog[a:a + 2])[0]
        self.table = NAMES + W(NAMES + variant)
    def entry(self, ch, side): return self.table + (ch * 2 + side) * 16
    def lst(self, ch, side):
        return struct.unpack('>I', self.d[self.entry(ch, side) + 4:self.entry(ch, side) + 8])[0]
    def cells(self, ch, side):
        p = self.lst(ch, side)
        W = lambda a: struct.unpack('>H', self.d[a:a + 2])[0]
        return p, [tuple(W(p + 6 + 8 * i + 2 * k) for k in range(4)) for i in range(W(p + 4) + 1)]
    def image(self, ch, side):
        _, cells = self.cells(ch, side)
        im = np.zeros((16, 8 * len(cells)), np.uint8)
        for i, (c0, a0, c1, a1) in enumerate(cells):
            im[0:8, 8 * i:8 * i + 8] = cps2preview.code8(self.G, c0)
            im[8:16, 8 * i:8 * i + 8] = cps2preview.code8(self.G, c1)
        return im

    def compose(self, text):
        can = np.full((16, 80), CLEAR, np.uint8)
        cur = 0
        for ch in text:
            if ch == 'Z':
                w = len(Z[0]); g = np.full((16, w + 4), CLEAR, np.uint8)
                for y in range(16):
                    for x, c in enumerate(Z[y]):
                        if c != ' ': g[y, x + slant(y) + 1] = int(c, 16)
            else:
                n, a, b = GLYPHS[ch]
                src = self.image(CHAR[n], 0); w = b - a
                g = np.full((16, w + 4), CLEAR, np.uint8)
                for y in range(2, 15):
                    for x in range(a, b):
                        sx = x + slant(y)
                        if sx >= src.shape[1]: continue
                        c = src[y, sx]
                        if c in LIGHTNING or c == CLEAR: continue
                        g[y, x - a + slant(y) + 1] = c
            for y in range(16):
                for x in range(g.shape[1]):
                    q, p = g[y, x], can[y, cur + x]
                    if q == CLEAR: continue
                    if p == CLEAR or (p in OUTLINE and q not in OUTLINE):
                        can[y, cur + x] = q
            cur += w - 1
        used = max(x for x in range(80) if (can[:, x] != CLEAR).any()) + 1
        return can[:, :used]

    def build(self, alloc, text='ZANGIEF', model='MORRIGAN'):
        """two lists (side 0, side 1) in MORRIGAN's layout; bytes, big endian"""
        name = self.compose(text)
        out = []
        for side in (0, 1):
            base = self.image(CHAR[model], side)
            p, cells = self.cells(CHAR[model], side)
            im = base.copy()
            # the name rows 2-14: clear MORRIGAN's letters, then put ZANGIEF
            # where her name starts (left for side 0, right-aligned for side 1)
            body = im[2:15]
            cols = np.nonzero((body != CLEAR).any(0))[0]
            x0, x1 = cols.min(), cols.max() + 1
            im[2:15, x0:x1] = CLEAR
            w = name.shape[1]
            start = x0 if side == 0 else max(0, x1 - w)
            seg = name[2:15, :min(w, im.shape[1] - start)]
            m = seg != CLEAR
            im[2:15, start:start + seg.shape[1]][m] = seg[m]
            hdr = self.d[p:p + 6]
            body = b''
            for i, (c0, a0, c1, a1) in enumerate(cells):
                t = alloc.code(im[0:8, 8 * i:8 * i + 8]); b_ = alloc.code(im[8:16, 8 * i:8 * i + 8])
                body += struct.pack('>4H', t, a0, b_, a1)
            out.append(hdr + body)
        return out, name
