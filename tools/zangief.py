#!/usr/bin/env python3
"""Build Zangief's in-match character file (PL0B_OBJ.EMI) from Pocket Fighter.

Inputs come from the user's own discs at build time (no game data in the repo):
  ZANGIEF.PAC  Pocket Fighter /PLAYER/ZANGIEF.PAC (frames, cells, palettes)
  PL09A.MDL    Pocket Fighter /MDL/PL09A.MDL (Zangief's animation array)
  FIRST.EMI    SPF2T /DATA/FIRST.EMI (Dan's effect palettes are reused)
  PL9A_OBJ.EMI SPF2T /DATA/PL9A_OBJ.EMI (EMI header template)

Output: an SPF2T character file with the usual two entries.
  entry 0: halfword-LZ graphics, one stream per frame (tools/lzh.py)
  entry 1: loaded at the player's record bank (P1 0x800E7600, P2 0x800EBB00):
           +0       44-byte frame records
           +PALOFF  palette block: 4 colour sets x 4 palettes (palette 0 =
                    Zangief, 1-3 = Dan's effect palettes), like FIRST.EMI's
                    per-character blocks (see xp_zpal in src/zangief.asm)
           +LISTOFF 51 state offsets (relative to the bank), then the
                    16-byte animation scripts (see xp_zstate)

Frames: Pocket Fighter records are composited (costume overlays: a record with
flag bit 0 is drawn with the next record on top), kept facing left (the game mirrors P1),
scaled to 0.65 around the feet anchor and quantised to one 15-colour palette.
The Spinning Piledriver frames get a vertical lift (jumps are object motion in
Pocket Fighter, not part of the frames).

usage: zangief.py ZANGIEF.PAC PL09A.MDL FIRST.EMI PL9A_OBJ.EMI OUT.EMI [--sheet PNG]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_sprites as P
import lzh

SCALE = 0.65
PALOFF = 0x2C00             # must match src/zangief.asm
LISTOFF = 0x2E00
BANK_MAX = 0x4500
N_STATES = 51
MDL_ANIM = 0x565C           # Zangief's animation array in PL09A.MDL
DAN_PALS = 0x61C00          # Dan's palette block in FIRST.EMI (0x800F9840)

# --- Pocket Fighter animations used (start entry in the MDL array) ---------
PF = dict(idle=1, hit=111, hit2=121, ko=127, bear=150, taunt=166, punch=225,
          pile=282, lariat=372, win=685)
# lift (native pixels) of the Piledriver frames
LIFT = {118: 8, 119: 18, 120: 26, 121: 30, 122: 26, 123: 18, 124: 8}

def pf_anim(mdl, start):
    out, i = [], start
    while True:
        dur, fl, jump, fr = struct.unpack_from('<HhhH', mdl, MDL_ANIM + 24 * i)
        out.append((dur, fr))
        if fl < 0:
            return out
        i += 1

# --- SPF2T scripts -----------------------------------------------------------
# An animation is ([(dur, frame_key, flags, event), ...], loop_index).
# frame_key = (pf_frame, lift). loop_index None = hold the last entry.
def anim(seq, loop=None, flag1=None, event=None, ev_at=1):
    ents = []
    for k, (dur, fr) in enumerate(seq):
        ents.append([min(dur, 4095), (fr, LIFT.get(fr, 0)),
                     1 if flag1 == k else 0, event if (event and k == ev_at) else 0])
    return ents, loop

def build_anims(mdl):
    a = {k: pf_anim(mdl, v) for k, v in PF.items()}
    idle = a['idle']
    S = {}
    IDLE = anim(idle, 0)
    S['idle'] = IDLE
    S['still'] = anim([(3, 0)], None)
    S['hit'] = anim([(4, 42), (4095, 43)], None)
    S['hit2'] = anim([(4, 46), (4095, 47)], None)
    S['ko'] = anim([(4, 46), (6, 47), (4095, 48)], None)
    S['taunt'] = anim([(4, 87), (4, 88), (4, 89), (4, 90), (4, 90), (4, 89)], 2)
    S['flex'] = anim([(6, 337), (8, 338)], 0)
    S['win'] = anim([(6, 337), (8, 338)], 0, flag1=1)
    S['punch'] = anim(a['punch'], 1, flag1=1)
    S['lariat'] = anim(a['lariat'][:17], 5)
    S['pile'] = anim(a['pile'], 1)
    bear = a['bear']                       # walk in the skin, burst, pose
    S['bear'] = anim(bear[:3] * 3 + bear[3:7] + [(6, 337), (8, 338)], 3 * 3 + 4)
    S['hitloop'] = anim([(4, 42), (4, 43)], 0)
    return S

# Dan's 51 states (0x8018779C) -> Zangief animation. 23/24 are the select
# screen poses (another bank): they stay Dan's (see xp_zstate).
STATES = {
    0: 'idle', 1: 'idle', 2: 'idle', 37: 'idle', **{s: 'idle' for s in range(43, 51)},
    **{s: 'still' for s in range(17, 23)},
    3: 'flex', 36: 'flex', 16: 'flex', 39: 'flex',
    # win poses, picked at random by Dan's code (tables 0x80171C18/20)
    4: 'win', 31: 'taunt', 32: 'flex', 33: 'win', 34: 'taunt',
    5: 'ko', 30: 'ko', 38: 'ko', 40: 'hit2',
    # reaction to an incoming attack: 6 + strength (0x801355EC)
    6: 'hit', 7: 'hit2', 8: 'hit2',
    15: 'taunt', 41: 'hit', 42: 'hit',
    9: 'hit', 25: 'hitloop', 26: 'hit', 27: 'hit', 28: 'hit2', 29: 'flex',
    35: 'hitloop',
    10: 'punch', 11: 'lariat', 12: 'pile', 13: 'pile', 14: 'bear',
    23: 'idle', 24: 'idle',
}

# --- frames ------------------------------------------------------------------
class PFFrames:
    def __init__(self, pac):
        self.e, self.words, self.recs = P.frames(pac)
        self.cols = P.palette(self.e, 0, 16)

    def rgba(self, n):
        from PIL import Image
        img = P.render(self.e, self.words, self.recs[n])
        im = Image.new('RGBA', (len(img[0]), len(img)))
        im.putdata([(*self.cols[v & 0xFF], 255) if v else (0, 0, 0, 0)
                    for row in img for v in row])
        r = self.recs[n]
        ax, ay = struct.unpack('<hh', struct.pack('<HH', r[3], r[4]))
        return im, ax, ay, r[6]

    def composite(self, n, lift):
        """RGBA on a canvas with the feet origin at (OX, OY), facing left."""
        from PIL import Image
        OX, OY = 130, 200
        c = Image.new('RGBA', (260, 240), (0, 0, 0, 0))
        im, ax, ay, fl = self.rgba(n)
        c.alpha_composite(im, (OX - ax, OY - lift - ay))
        if fl & 1:
            im2, bx, by, _ = self.rgba(n + 1)
            c.alpha_composite(im2, (OX - bx, OY - lift - by))
        ox = OX                 # SPF2T records face left (P2); P1 is mirrored
        w, h = round(c.width * SCALE), round(c.height * SCALE)
        c = c.resize((w, h), Image.BOX)
        a = c.split()[3].point(lambda v: 255 if v > 110 else 0)
        c.putalpha(a)
        return c, round(ox * SCALE), round(OY * SCALE)

def quantise(images):
    from PIL import Image
    px = [p[:3] for im in images for p in im.getdata() if p[3]]
    strip = Image.new('RGB', (len(px), 1))
    strip.putdata(px)
    q = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:45]
    cols = [tuple(pal[i:i + 3]) for i in range(0, 45, 3)]
    while len(cols) < 15:
        cols.append((0, 0, 0))
    return cols

def nearest(cols, rgb, cache):
    if rgb not in cache:
        cache[rgb] = min(range(len(cols)), key=lambda i: sum((a - b) ** 2 for a, b in zip(cols[i], rgb)))
    return cache[rgb]

def bgr555(rgb):
    r, g, b = (min(31, (v + 4) >> 3) for v in rgb)
    v = r | g << 5 | b << 10
    return v if v else 0x8000            # black must not be transparent

def recolour(cols, mode):
    out = []
    for r, g, b in cols:
        if r > 100 and r > 1.6 * g and r > 1.6 * b:     # trunks, boots, bands
            r, g, b = {1: (b, g, r), 2: (g, r, b), 3: (r // 2 + 20, g // 2 + 20, r // 2 + 60)}[mode]
        out.append((r, g, b))
    return out

def lz_fast(hw):
    """Greedy halfword LZ (lzh.py format) with a hash chain: fast enough for
    the build; the game's decoder accepts any valid stream."""
    items, chains = [], {}
    i, n = 0, len(hw)
    def add(k):
        if k + 1 < n:
            chains.setdefault((hw[k], hw[k + 1]), []).append(k)
    while i < n:
        best_len, best_dist = 0, 0
        z = 0
        while i + z < n and hw[i + z] == 0 and z < 0xFFFF:
            z += 1
        if z >= 2:
            best_len = z
        if i + 1 < n:
            for j in reversed(chains.get((hw[i], hw[i + 1]), [])[-48:]):
                dist = i - j
                if dist > 0x7FF:
                    break
                l = 0
                while i + l < n and l < 0xFFFF and hw[i + l] == hw[j + l]:
                    l += 1
                if l > best_len:
                    best_len, best_dist = l, dist
        if best_len >= 2:
            if best_dist and best_len < 32:
                items.append((1, [(best_len << 11) | best_dist]))
            else:
                items.append((1, [best_dist, best_len]))
            for k in range(i, i + best_len):
                add(k)
            i += best_len
        else:
            items.append((0, [hw[i]]))
            add(i)
            i += 1
    return lzh._pack(items)

def make_record(img, ox, oy, cols, cache):
    """img: RGBA, origin (ox, oy). -> (record bytes without offset, LZ bytes)"""
    bb = img.getbbox()
    if not bb:
        bb = (ox, oy - 1, ox + 1, oy)
    x0, y0 = bb[0], bb[1]
    cw, ch = (bb[2] - x0 + 15) // 16, (bb[3] - y0 + 15) // 16
    assert cw <= 17 and cw * ch <= 256, (cw, ch)
    data = img.load()
    cells, mask = [], []
    for cy in range(ch):
        for cx in range(cw):
            cell = []
            for yy in range(16):
                row = []
                for xx in range(16):
                    x, y = x0 + cx * 16 + xx, y0 + cy * 16 + yy
                    if x < img.width and y < img.height and data[x, y][3]:
                        row.append(1 + nearest(cols, data[x, y][:3], cache))
                    else:
                        row.append(0)
                cell.append(row)
            present = any(any(r) for r in cell)
            mask.append(present)
            if present:
                cells.append(cell)
    if not cells:                       # empty frame: one blank cell
        mask[0] = True
        cells.append([[0] * 16 for _ in range(16)])
    assert len(cells) <= 48, len(cells)
    units = (len(cells) + 15) // 16 * 16
    rows = [[0] * 256 for _ in range(units)]
    for k, cell in enumerate(cells):
        sx, sy = (k % 16) * 16, (k // 16) * 16
        for yy in range(16):
            rows[sy + yy][sx:sx + 16] = cell[yy]
    hw = lzh.from_pixels(rows)
    lz = lz_fast(hw)
    assert lzh.decode(lz)[0][:len(hw)] == hw
    words = [0] * 8
    for i, m in enumerate(mask):
        if m:
            words[i // 32] |= 1 << (31 - i % 32)
    rec = struct.pack('<hhBBBB', x0 - ox, y0 - oy, ch, cw, units, 0x40)
    rec += struct.pack('<8I', *words)
    return rec, lz

def build(pac, mdl, first, template, sheet=None):
    pf = PFFrames(pac)
    anims = build_anims(mdl)
    used = {name: anims[name] for name in set(STATES.values())}
    keys = sorted({e[1] for ents, _ in used.values() for e in ents})
    comps = {k: pf.composite(*k) for k in keys}
    cols = quantise([c[0] for c in comps.values()])
    cache = {}
    index, recs, gfx = {}, [], bytearray()
    for k in keys:
        img, ox, oy = comps[k]
        rec, lz = make_record(img, ox, oy, cols, cache)
        index[k] = len(recs)
        recs.append(struct.pack('<I', len(gfx)) + rec)
        gfx += lz
        if len(gfx) % 4:
            gfx += bytes(4 - len(gfx) % 4)
    assert len(recs) * 44 <= PALOFF, len(recs)
    # palettes: 4 sets x (Zangief, Dan's 3 effect palettes)
    pals = bytearray()
    dan = first[DAN_PALS:DAN_PALS + 0x200]
    for s in range(4):              # set 1 is the default (confirm with X)
        mode = {0: 1, 1: 0, 2: 2, 3: 3}[s]
        c = recolour(cols, mode) if mode else cols
        pals += struct.pack('<16H', 0, *[bgr555(x) for x in c])
        pals += dan[s * 0x80 + 0x20:s * 0x80 + 0x80]
    # scripts
    scripts, where = bytearray(), {}
    base = LISTOFF + 4 * N_STATES
    for name, (ents, loop) in sorted(used.items()):
        where[name] = base + len(scripts)
        for k, (dur, key, f1, ev) in enumerate(ents):
            last = k == len(ents) - 1
            flags = f1 | (0x8000 if last else 0)
            jump = ((loop if loop is not None else k) - k) if last else 0
            scripts += struct.pack('<HHhh', dur, flags, index[key], jump)
            scripts += bytes([0, 0, 0, 0, ev, 0, 3, 0])
    lst = b''.join(struct.pack('<I', where[STATES[s]]) for s in range(N_STATES))
    e1 = bytearray(b''.join(recs))
    e1 += bytes(PALOFF - len(e1)) + pals
    e1 += bytes(LISTOFF - len(e1)) + lst + scripts
    assert len(e1) <= BANK_MAX, hex(len(e1))
    assert len(gfx) <= 0x48000, hex(len(gfx))
    # EMI: header sector like the template, then the two entries 0x800-aligned
    hdr = bytearray(template[:0x800])
    struct.pack_into('<I', hdr, 16, len(gfx))
    struct.pack_into('<I', hdr, 32, len(e1))
    out = hdr + gfx + bytes(-len(gfx) % 0x800) + e1 + bytes(-len(e1) % 0x800)
    if sheet:
        from PIL import Image
        n = len(keys)
        S = Image.new('RGBA', (12 * 90, ((n + 11) // 12) * 90), (40, 40, 60, 255))
        for i, k in enumerate(keys):
            S.alpha_composite(comps[k][0].crop((comps[k][1] - 45, comps[k][2] - 85,
                                                comps[k][1] + 45, comps[k][2] + 5)),
                              ((i % 12) * 90, (i // 12) * 90))
        S.save(sheet)
    return bytes(out), len(recs), len(gfx), len(e1)

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 5:
        print(__doc__); sys.exit(1)
    sheet = a[a.index('--sheet') + 1] if '--sheet' in a else None
    rd = lambda p: open(p, 'rb').read()
    out, n, g, e1 = build(rd(a[0]), rd(a[1]), rd(a[2]), rd(a[3]), sheet)
    open(a[4], 'wb').write(out)
    print('%d frames, graphics 0x%X bytes, bank 0x%X bytes' % (n, g, e1))
