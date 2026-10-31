"""Pocket Fighter (sgemf) arcade data: animations and sprite frames of a character.

Same engine as SPF2T: animation entries (24 bytes for players: +0 duration word,
+2 flags byte (negative: the long after the entry is where to go next), +4 frame);
frames: word sprites, word count-1, long position list, then count longs
(attr << 16 | code). Positions are x, y words per sprite, at the feet origin."""
import struct
import numpy as np

class PF:
    def __init__(self, prog, gfx, postable=None):
        self.d = prog          # big-endian program image (data view)
        self.G = gfx           # cps2gfx.Gfx of the graphics region
        self.postable = postable   # SPF2T: frames give a word offset into this pointer table
    def W(self, a): return struct.unpack('>H', self.d[a:a + 2])[0]
    def S(self, a): return struct.unpack('>h', self.d[a:a + 2])[0]
    def L(self, a): return struct.unpack('>I', self.d[a:a + 4])[0]

    def animations(self, base):
        n = self.W(base) // 2
        return [base + self.W(base + 2 * i) for i in range(n)]

    def entries(self, a, limit=200):
        """entries of one animation until its jump: [(addr, duration, flags, frame)], jump"""
        out = []
        for _ in range(limit):
            dur, fl, fr = self.W(a), self.d[a + 2], self.L(a + 4)
            out.append((a, dur, fl, fr))
            if fl & 0x80: return out, self.L(a + 24)
            a += 24
        return out, None

    def frame(self, f):
        """[(x, y, code, attr)] of one frame (x, y of the top-left of each block).
        Word 0 is the frame type (the emitter's jump table); type 2: word sprites,
        word count-1, long position list, count longs code << 16 | attr."""
        t = self.W(f)
        if t != 2: raise ValueError('frame %x: type %d' % (f, t))
        n = self.W(f + 4) + 1
        if self.postable is None:
            pos, first = self.L(f + 6), f + 10
        else:
            pos, first = self.L(self.postable + self.W(f + 6)), f + 8
        out = []
        for i in range(n):
            al = self.L(first + 4 * i)
            x, y = self.S(pos + 4 * i), self.S(pos + 4 * i + 2)
            out.append((x, y, al >> 16, al & 0xffff))
        return out

    def render(self, f, bank=0, size=256, ox=128, oy=200):
        """index image (0 = transparent) and palette numbers used, origin at (ox, oy).
        In the game y grows down from the anchor: screen y = anchor - y (CPS y up)."""
        img = np.zeros((size, size), np.uint8); pal = np.full((size, size), -1, np.int16)
        for x, y, code, attr in self.frame(f):
            w = ((attr >> 8) & 15) + 1; h = ((attr >> 12) & 15) + 1
            fx, fy = attr & 0x20, attr & 0x40
            for by in range(h):
                for bx in range(w):
                    t = self.G.tile(code + bank * 0x10000 + bx + by * 16)
                    if fx: t = t[:, ::-1]
                    if fy: t = t[::-1]
                    cx = (w - 1 - bx) if fx else bx
                    cy = (h - 1 - by) if fy else by
                    X = ox + x + cx * 16; Y = oy + y + cy * 16
                    if X < 0 or Y < 0 or X + 16 > size or Y + 16 > size: continue
                    m = t != 15
                    img[Y:Y + 16, X:X + 16][m] = t[m]
                    pal[Y:Y + 16, X:X + 16][m] = attr & 31
        return img, pal
