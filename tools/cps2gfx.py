"""CPS2 graphics ROMs <-> 16x16 4bpp tiles (MAME's ROM_LOAD64_WORD + unshuffle +
cps1_gfx_decode, and the inverse). A tile is 16 rows of 16 colour indices."""
import numpy as np

BANK = 0x200000

def interleave(roms):
    """four ROMs (14m,16m,18m,20m order) -> the region as MAME loads it (ROM_LOAD64_WORD)"""
    n = len(roms[0]); out = np.zeros(n * 4, np.uint8)
    for k, r in enumerate(roms):
        a = np.frombuffer(r, np.uint8).reshape(-1, 2)
        out.reshape(-1, 8)[:, 2 * k:2 * k + 2] = a
    return out

def deinterleave(region):
    v = region.reshape(-1, 8)
    return [v[:, 2 * k:2 * k + 2].tobytes() for k in range(4)]

def _perm(n):
    """index permutation of MAME's unshuffle on n 64-bit units: new[i] = old[p[i]]"""
    p = list(range(n))
    def rec(lo, ln):
        if ln == 2: return
        h = ln // 2
        rec(lo, h); rec(lo + h, h)
        for i in range(h // 2):
            a, b = lo + h // 2 + i, lo + h + i
            p[a], p[b] = p[b], p[a]
    rec(0, n)
    return np.array(p)

_P = None
def unshuffle(region):
    global _P
    if _P is None: _P = _perm(BANK // 8)
    v = region.view(np.uint64).reshape(-1, BANK // 8)
    return v[:, _P].reshape(-1).view(np.uint8)

def shuffle(region):
    global _P
    if _P is None: _P = _perm(BANK // 8)
    inv = np.argsort(_P)
    v = region.view(np.uint64).reshape(-1, BANK // 8)
    return v[:, inv].reshape(-1).view(np.uint8)

def to_pixels(region):
    """planar dwords -> one 4-bit pixel per byte, 8 per dword (MAME's cps1_gfx_decode)"""
    d = region.view(np.uint32)
    out = np.zeros((len(d), 8), np.uint8)
    for j in range(8):
        m = (np.uint32(0x80808080) >> np.uint32(j)) & d
        n = ((m & 0xff) != 0).astype(np.uint8) | (((m & 0xff00) != 0).astype(np.uint8) << 1) | \
            (((m & 0xff0000) != 0).astype(np.uint8) << 2) | (((m & 0xff000000) != 0).astype(np.uint8) << 3)
        out[:, j] = n
    return out.reshape(-1)

def from_pixels(px):
    p = px.reshape(-1, 8).astype(np.uint32)
    d = np.zeros(len(p), np.uint32)
    for j in range(8):
        n = p[:, j]
        for b in range(4):
            d |= ((n >> b) & 1) * (np.uint32(0x80) >> np.uint32(j)) << np.uint32(8 * b)
    return d.view(np.uint8)

class Gfx:
    """pixels of the whole graphics region: tile t (16x16) = px[t*256:(t+1)*256].
    roms: four ROMs loaded at 0, or groups=[(region offset, [four ROMs]), ...]"""
    def __init__(self, roms=None, base=0, groups=None):
        if groups is None:
            reg = interleave(roms)
            if base: reg = np.concatenate([np.zeros(base, np.uint8), reg])
        else:
            size = max(o + 4 * len(r[0]) for o, r in groups)
            reg = np.zeros(size, np.uint8)
            for o, r in groups: reg[o:o + 4 * len(r[0])] = interleave(r)
        self.base = base
        self.px = to_pixels(unshuffle(reg))
    def tile(self, t):
        return self.px[t * 256:(t + 1) * 256].reshape(16, 16)
    def set_tile(self, t, a):
        self.px[t * 256:(t + 1) * 256] = np.asarray(a, np.uint8).reshape(-1)
    def roms(self):
        reg = shuffle(from_pixels(self.px).copy())[self.base:]
        return deinterleave(reg)
