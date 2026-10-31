"""Zangief for the arcade set: his in-match animations, from the user's
Pocket Fighter arcade set (sgemf), rebuilt in SPF2T's format.

The choice of animations is the PSX one (tools/zangief.py): the arcade and PSX
Pocket Fighter keep Zangief's animation entries in the same order, so the
entry numbers carry over; the frames are identified by their address in the
arcade program (REC: PSX record number -> arcade frame).

Output: the data blob (state table, palette, entries, frames, position lists)
for pzf.04 at ZBLOB, and the graphics tiles (codes 0x8000- of SPF2T's sprite
bank, i.e. graphics region 0xC00000-)."""
import struct
import numpy as np

SCALE = 0.9
ZBLOB = 0x90000             # must match arcade/src/code_zangief.s
N_STATES = 63               # Dan's state table (0x7AB6C): 63 words
PALOFF = 0x80               # palette (16 words) in the blob
TILE0 = 0x8000              # first sprite code of the new graphics
DAN_PAL_ATTR = 0x0C         # Dan's sprite palette (P1; P2 adds 4)

# Pocket Fighter arcade program addresses (sgemf, decrypted)
PF_ENTRIES = 0x1A1FC6       # Zangief's first animation entry (= PSX entry 1)
PF_TABLES = (0x1A355A, 0x1A6F54)   # his other two state tables, between entries
PF_PALS = {0: 0x20B1A8, 2: 0x22FC3C}   # sprite palette 0 / 2 of his frames (P1 colours)
REC = {0: 0x1A97C6, 1: 0x1A9862, 2: 0x1A98A6, 3: 0x1A990A, 4: 0x1A99BC, 42: 0x1AA958,
       43: 0x1AA308, 46: 0x1AA3C8, 47: 0x1AA434, 48: 0x1AA456, 77: 0x1AA648, 79: 0x1AA692,
       81: 0x1AA726, 83: 0x1AA768, 85: 0x1AA7A6, 87: 0x1AA7EC, 88: 0x1AA826, 89: 0x1AA85C,
       90: 0x1AA8B4, 94: 0x1AAA10, 95: 0x1AAA92, 96: 0x1AAA2A, 97: 0x1AAC32, 98: 0x1AAC08,
       99: 0x1AABEE, 100: 0x1A98A6, 112: 0x1AAFCA, 118: 0x1AB0FA, 119: 0x1AB120,
       120: 0x1AB146, 121: 0x1AB164, 122: 0x1AB186, 123: 0x1AB1B0, 124: 0x1AB1D6,
       125: 0x1AB1F4, 164: 0x1AB8C8, 165: 0x1AB91A, 166: 0x1AB938, 167: 0x1AB966,
       168: 0x1AB99C, 169: 0x1AB9BE, 170: 0x1AB9E4, 337: 0x1ACFEE, 338: 0x1AD042,
       339: 0x1AD092, 485: 0x1AED16, 486: 0x1AED54}
PTR2REC = {v: k for k, v in REC.items()}

# --- the PSX choices (tools/zangief.py), in PSX entry / record numbers -------
PF = dict(idle=1, hit=111, hit2=121, ko=127, bear=150, taunt=166, punch=225,
          pile=282, lariat=372, win=685)
LIFT = {118: 8, 119: 18, 120: 26, 121: 30, 122: 26, 123: 18, 124: 8}

# SPF2T arcade states (Dan's 0x7AB6C, same numbering as the PSX for 0-34) -> animation.
# 23/24 (select screen poses) and the states the arcade does not use stay Dan's.
STATES = {
    0: 'idle', 1: 'pinch1', 2: 'pinch2',
    **{s: 'still' for s in range(17, 23)},
    3: 'flex', 16: 'flex',
    4: 'win', 31: 'taunt', 32: 'flex', 33: 'win', 34: 'taunt',
    5: 'ko', 30: 'ko',
    6: 'hit', 7: 'hit2', 8: 'hit2',
    15: 'taunt', 42: 'hit',
    9: 'hit', 25: 'hitloop', 26: 'hit', 27: 'hit', 28: 'hit2', 29: 'flex',
    10: 'punch', 11: 'lariat', 12: 'pile', 13: 'pile', 14: 'bear',
}

class PFData:
    def __init__(self, prog):
        self.d = prog
        self.entries = []           # PSX entry k -> (duration, last, frame pointer)
        W = lambda a: struct.unpack('>H', prog[a:a + 2])[0]
        a = PF_ENTRIES
        self.entries.append(None)   # PSX entry 0 has no arcade twin here
        while len(self.entries) < 1023:
            if a in PF_TABLES: a += W(a)
            dur, fl = W(a), prog[a + 2]
            fr = struct.unpack('>I', prog[a + 4:a + 8])[0]
            self.entries.append((dur, fl >= 0x80, fr))
            a += 24 + (4 if fl >= 0x80 else 0)

    def anim(self, start):
        out, k = [], start
        while True:
            dur, last, fr = self.entries[k]
            out.append((dur, PTR2REC.get(fr, fr)))
            if last: return out
            k += 1

def anim(seq, loop=None):
    return [(min(dur, 4095), fr) for dur, fr in seq], loop

def build_anims(P):
    a = {k: P.anim(v) for k, v in PF.items()}
    S = {}
    S['idle'] = anim(a['idle'], 0)
    S['still'] = anim([(3, 0)], None)
    S['hit'] = anim([(4, 42), (4095, 43)], None)
    S['hit2'] = anim([(4, 46), (4095, 47)], None)
    S['ko'] = anim([(4, 46), (6, 47), (4095, 48)], None)
    S['taunt'] = anim([(4, 87), (4, 88), (4, 89), (4, 90), (4, 90), (4, 89)], 2)
    S['flex'] = anim([(6, 337), (8, 338)], 0)
    S['win'] = anim([(6, 337), (8, 338)], 0)
    S['punch'] = anim(a['punch'], 1)
    S['lariat'] = anim(a['lariat'][:17], 5)
    S['pile'] = anim(a['pile'], 1)
    bear = a['bear']
    S['bear'] = anim(bear[:3] * 3 + bear[3:7] + [(6, 337), (8, 338)], 3 * 3 + 4)
    S['hitloop'] = anim([(4, 42), (4, 43)], 0)
    S['pinch1'] = anim(P.anim(195), 0)
    S['pinch2'] = anim([(8, 485), (8, 486)], 0)
    return S

def rgb(w):
    return ((w >> 8) & 15) * 17, ((w >> 4) & 15) * 17, (w & 15) * 17

def render_rgba(pf, rec, pals, size=256, ox=128, oy=200):
    """frame (PSX record number or arcade pointer) as RGBA, feet at (ox, oy - lift)"""
    ptr = REC.get(rec, rec)
    lift = LIFT.get(rec, 0)
    img, pal = pf.render(ptr, size=size, ox=ox, oy=oy - lift)
    out = np.zeros((size, size, 4), np.uint8)
    for p, cols in pals.items():
        m = pal == p
        out[m, :3] = cols[img[m]]
        out[m, 3] = 255
    return out

def build(pf_prog, pf_gfx, verbose=False):
    import pfarc
    from PIL import Image
    pf = pfarc.PF(pf_prog, pf_gfx)
    P = PFData(pf_prog)
    S = build_anims(P)
    pals = {p: np.array([rgb(struct.unpack('>H', pf_prog[a + 2 * i:a + 2 * i + 2])[0]) for i in range(16)],
                        np.uint8) for p, a in PF_PALS.items()}
    used = sorted({fr for name in set(STATES.values()) for _, fr in S[name][0]}, key=str)
    # frames: scaled RGBA around the feet
    SZ, OX, OY = 256, 128, 200
    imgs = {}
    for fr in used:
        im = Image.fromarray(render_rgba(pf, fr, pals, SZ, OX, OY), 'RGBA')
        w, h = round(SZ * SCALE), round(SZ * SCALE)
        im = im.resize((w, h), Image.BOX)
        a = np.array(im)
        a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
        imgs[fr] = a
    ax, ay = round(OX * SCALE), round(OY * SCALE)
    # one 15-colour palette for all of them
    px = np.concatenate([a[a[..., 3] > 0][:, :3] for a in imgs.values()])
    strip = Image.fromarray(px.reshape(1, -1, 3), 'RGB')
    q = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    qp = np.array(q.getpalette()[:45], np.int32).reshape(-1, 3)
    qp = np.concatenate([qp, np.zeros((15 - len(qp), 3), np.int32)]) if len(qp) < 15 else qp
    def index(a):
        m = a[..., 3] > 0
        out = np.full(a.shape[:2], 15, np.uint8)
        c = a[m][:, :3].astype(np.int32)
        dist = ((c[:, None, :] - qp[None, :, :]) ** 2).sum(-1)
        out[m] = dist.argmin(1)
        return out
    # tiles and sprite lists
    tiles, tkey = [], {}
    frames = {}
    for fr, a in imgs.items():
        ix = index(a)
        ys, xs = np.nonzero(ix != 15)
        if len(xs) == 0:
            frames[fr] = []; continue
        x0, y0 = xs.min(), ys.min()
        spr = []
        for ty in range(y0, ys.max() + 1, 16):
            for tx in range(x0, xs.max() + 1, 16):
                t = np.full((16, 16), 15, np.uint8)
                blk = ix[ty:ty + 16, tx:tx + 16]
                t[:blk.shape[0], :blk.shape[1]] = blk
                if (t == 15).all(): continue
                k = t.tobytes()
                if k not in tkey:
                    tkey[k] = len(tiles); tiles.append(t)
                spr.append((tx - ax, ty - ay, TILE0 + tkey[k]))
        frames[fr] = spr
    # blob
    blob = bytearray(b'\0' * PALOFF)
    pal = [0xF000 | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4) for r, g, b in qp.tolist()] + [0xF000]
    blob += struct.pack('>16H', *pal)
    fpos = {}
    def addr(): return ZBLOB + len(blob)
    for fr, spr in frames.items():           # position lists, then frames
        fpos[fr] = addr()
        for x, y, c in spr: blob += struct.pack('>hh', x, y)
    fptr = {}
    for fr, spr in frames.items():
        fptr[fr] = addr()
        n = max(1, len(spr))
        blob += struct.pack('>HHHI', 12, n, n - 1, fpos[fr])
        for x, y, c in spr or [(0, 0, TILE0)]:
            blob += struct.pack('>HH', c, DAN_PAL_ATTR)
    sptr = {}
    for name in sorted(set(STATES.values())):
        ents, loop = S[name]
        start = addr(); sptr[name] = start - ZBLOB
        for i, (dur, fr) in enumerate(ents):
            last = i == len(ents) - 1
            blob += struct.pack('>HBBIHBBI', dur, 0x80 if last else 0, 0, fptr[fr], 0, 0, 0, 0)
            if last:
                tgt = start + 16 * (loop if loop is not None else i)
                blob += struct.pack('>I', tgt)
    for s, name in STATES.items():
        struct.pack_into('>H', blob, 2 * s, sptr[name])
    if len(blob) > 0x10000: raise SystemExit('zangief blob too big: %x' % len(blob))
    if verbose:
        print('zangief: %d frames, %d tiles, blob %x bytes' % (len(frames), len(tiles), len(blob)))
    return bytes(blob), tiles

def gfx_roms(tiles):
    """the four 1 MB ROMs for graphics 0xC00000-0xFFFFFF (tile code 0x8000 = first)"""
    import cps2gfx
    G = cps2gfx.Gfx([bytes(0x100000)] * 4)
    for i, t in enumerate(tiles): G.set_tile(i, t)
    return G.roms()
