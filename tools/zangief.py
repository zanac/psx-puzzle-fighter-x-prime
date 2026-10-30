#!/usr/bin/env python3
"""Build Zangief's in-match character file (PL0B_OBJ.EMI) from Pocket Fighter.

Inputs come from the user's own discs at build time (no game data in the repo):
  ZANGIEF.PAC  Pocket Fighter /PLAYER/ZANGIEF.PAC (frames, cells, palettes)
  PL09A.MDL    Pocket Fighter /MDL/PL09A.MDL (Zangief's animation array)
  FIRST.EMI    SPF2T /DATA/FIRST.EMI (Dan's effect palettes are reused)
  PL9A_OBJ.EMI SPF2T /DATA/PL9A_OBJ.EMI (EMI header template)
  SLUS_004.18  SPF2T executable (Dan's scripts: voice cues and flags per state)

Output: an SPF2T character file with the usual two entries.
  entry 0: halfword-LZ graphics, one stream per frame (tools/lzh.py)
  entry 1: loaded at the player's record bank (P1 0x800E7600, P2 0x800EBB00):
           +0       44-byte frame records
           +PALOFF  palette block: 4 colour sets x 4 palettes (palette 0 =
                    Zangief, 1-3 = Dan's effect palettes), like FIRST.EMI's
                    per-character blocks (see xp_zpal in src/zangief.asm)
           +0x200   burnt and frozen special palettes (3 each, see xp_zpal3)
           +LISTOFF 51 state offsets (relative to the bank), 3 hit-tail
                    offsets (states 0-2), the hit-script range, then the
                    16-byte animation scripts (see xp_zstate)

Frames: Pocket Fighter records are composited (costume overlays: a record with
flag bit 0 is drawn with the next record on top), kept facing left (the game mirrors P1),
scaled to 0.65 around the feet anchor and quantised to one 15-colour palette.
The Spinning Piledriver frames get a vertical lift (jumps are object motion in
Pocket Fighter, not part of the frames).

usage: zangief.py ZANGIEF.PAC PL09A.MDL FIRST.EMI PL9A_OBJ.EMI SLUS_004.18 OUT.EMI [--sheet PNG]
       zangief.py voices SE0AA.PAC SE_PL0A.EMI OUT.EMI [--wav DIR]   (SE_PL0B.EMI)
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_sprites as P
import lzh

SCALE = 0.65
PALOFF = 0x2C00             # must match src/zangief.asm
LISTOFF = 0x2F00
BANK_MAX = 0x4500
N_STATES = 51
MDL_ANIM = 0x565C           # Zangief's animation array in PL09A.MDL
DAN_PALS = 0x61C00          # Dan's palette block in FIRST.EMI (0x800F9840)
DAN_SPECIAL = 0x62C80       # Dan's burnt palettes (0x800F9A40 + 0xE80); frozen at +0x60

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
    # pinch (field filling up): struggling, then crying out
    S['pinch1'] = anim(pf_anim(mdl, 195), 0)                # frames 94-96
    S['pinch2'] = anim([(8, 485), (8, 486)], 0)
    return S

# Zangief's own voice cues (script byte 11 = index into Dan's voice table
# 0x8016EFF4; indices 7/8 are unused by Dan and set to ids 14/15 by
# src/zangief.asm): a cry when he gets into trouble. xp_zstate skips the cue
# entry unless he comes from his idle (0) or the first pinch (1).
ZG_EVENTS = {1: [(0, 0, 7)], 2: [(0, 0, 8)]}

# Dan's 51 states (0x8018779C) -> Zangief animation. 23/24 are the select
# screen poses (another bank): they stay Dan's (see xp_zstate).
STATES = {
    0: 'idle', 1: 'pinch1', 2: 'pinch2', 37: 'idle', **{s: 'idle' for s in range(43, 51)},
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

DAN_STATES = 0x8018779C     # Dan's state list in SLUS_004.18

def dan_events(exe):
    """Per state: [(time, flag1, voice)] from Dan's scripts (first pass).
    Script byte 11 is a voice index (0x80136554 plays the character's voice
    table 0x8016EFFC entry byte11 - 1); flag bit 0 is kept as Dan has it."""
    o = lambda a: a - 0x80100000 + 0x800
    out = {}
    for st in range(N_STATES):
        p = struct.unpack_from('<I', exe, o(DAN_STATES + 4 * st))[0]
        t, ev = 0, []
        for _ in range(64):
            dur, fl = struct.unpack_from('<HH', exe, o(p))
            v = exe[o(p) + 11]
            if fl & 1 or v:
                ev.append((t, fl & 1, v))
            if fl & 0x8000:
                break
            t += dur
            p += 16
        out[st] = ev
    return out

def place(ents, loop, events):
    """Put Dan's events on the Zangief entry playing at the same time. A
    looping body is unrolled until the last event, then one clean copy loops,
    so a cue never repeats unless Dan's does. -> (ents, loop, sig)"""
    ents = list(ents)
    last_t = max((w for w, _, _ in events), default=-1)
    if loop is not None and events:
        body = ents[loop:]
        while sum(e[0] for e in ents) <= last_t:
            ents += body
        loop = len(ents)
        ents += body
    starts, t = [], 0
    for e in ents:
        starts.append(t)
        t += e[0]
    sig = []
    for when, f1, v in events:
        j = max(i for i, st in enumerate(starts) if st <= when)
        if loop is not None and j >= loop:
            j = loop - 1
        sig.append((j, f1, v))
    return ents, loop, tuple(sig)

def build(pac, mdl, first, template, exe, sheet=None):
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
    # special palettes (burnt / frozen, 0x80136908 / 0x80136990): Dan's
    # versions remapped to Zangief's colours by brightness
    lum = lambda c: c[0] * 3 + c[1] * 6 + c[2]
    def unpal(b):
        return [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('<16H', b)]
    dnorm = unpal(first[DAN_PALS + 0x80:DAN_PALS + 0xA0])
    for off in (DAN_SPECIAL, DAN_SPECIAL + 0x60):
        dsp = unpal(first[off:off + 0x20])
        pairs = sorted((lum(dnorm[i]), dsp[i]) for i in range(1, 16))
        z = [min(pairs, key=lambda p: abs(p[0] - lum(c)))[1] for c in cols]
        pals += struct.pack('<16H', 0, *[bgr555(x) for x in z])
        pals += first[off + 0x20:off + 0x60]
    assert len(pals) <= LISTOFF - PALOFF
    # scripts: one per (animation, Dan's events of the state). The hit
    # reactions come first, so their range can be told apart (see xp_zstate:
    # leaving a hit for idle 0-2 goes through a short hit tail).
    devents = dan_events(exe)
    scripts, where, per_state = bytearray(), {}, {}
    base = LISTOFF + 4 * (N_STATES + 7)
    HITS = ('hit', 'hit2', 'hitloop')
    order = [st for st in range(N_STATES) if STATES[st] in HITS] + [0, 1] + \
            [st for st in range(N_STATES) if STATES[st] not in HITS and st not in (0, 1)]
    hit_hi = calm_hi = None
    for st in order:
        if hit_hi is None and STATES[st] not in HITS:
            hit_hi = base + len(scripts)
        if calm_hi is None and st not in (0, 1) and STATES[st] not in HITS:
            calm_hi = base + len(scripts)
        name = STATES[st]
        ents, loop = used[name]
        ents, loop, sig = place(ents, loop, devents[st] + ZG_EVENTS.get(st, []))
        key2 = (name, sig)
        if key2 not in where:
            where[key2] = base + len(scripts)
            for k, (dur, key, _f1, _ev) in enumerate(ents):
                f1 = v = 0
                for j, ef, ev in sig:
                    if j == k:
                        f1 |= ef
                        v = v or ev
                last = k == len(ents) - 1
                flags = f1 | (0x8000 if last else 0)
                jump = ((loop if loop is not None else k) - k) if last else 0
                scripts += struct.pack('<HHhh', dur, flags, index[key], jump)
                scripts += bytes([0, 0, 0, v, 0, 0, 4 if name == 'still' else 3, 0])
        per_state[st] = where[key2]
    # hit tails for states 0-2: hold the hit pose a little, then the idle
    tails = []
    for st in range(3):
        t0 = base + len(scripts)
        tails.append(t0)
        scripts += struct.pack('<HHhh', 14, 0, index[(43, 0)], 0) + bytes([0, 0, 0, 0, 0, 0, 3, 0])
        target = per_state[st] + (16 if st in ZG_EVENTS else 0)    # skip the cue
        jump = (target - (t0 + 16)) // 16
        assert (target - (t0 + 16)) % 16 == 0
        scripts += struct.pack('<HHhh', 6, 0x8000, index[(42, 0)], jump) + bytes([0, 0, 0, 0, 0, 0, 3, 0])
    lst = b''.join(struct.pack('<I', per_state[s]) for s in range(N_STATES))
    lst += b''.join(struct.pack('<I', t) for t in tails)
    lst += struct.pack('<II', base, hit_hi)
    lst += struct.pack('<II', hit_hi, calm_hi)          # idle 0 + pinch 1 scripts
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

# --- voices (step 4) -----------------------------------------------------------
# SE_PL0B.EMI = Dan's SE_PL0A.EMI layout (sound id table, VAB header, VAG
# body) with Zangief's Pocket Fighter samples (PF /SE/SE0AA.PAC) in Dan's 24
# slots. Dan's slot roles come from the voice ids the game plays (see
# docs/NEW-CHARACTER-RESEARCH.md); Zangief's from Pocket Fighter's own use.
# Pocket Fighter's samples are 8 kHz: each tone gets center = note + 30 and
# shift 57, as in Pocket Fighter's own VAB (SPF2T's are 11.025 kHz).
VOICE_MAP = {   # Dan VAG slot (1-24) -> Zangief VAG (SE0AA, 1-31)
    1: 30, 2: 31,
    3: 5,       # attack (id 31): punch shout
    4: 28,      # attack / super start (id 30)
    5: 26,      # attack (id 32)
    6: 13, 7: 10,
    8: 21,      # opponent knocked out (id 27): his taunt line
    9: 4,       # win (id 28)
    10: 15, 11: 11, 12: 16, 13: 18, 14: 14,
    15: 7, 16: 6,   # in trouble 1 / 2 (ids 14/15, ZG_EVENTS)
    17: 17,     # bear
    18: 24,
    19: 23,     # attack (id 33): Double Lariat shout
    20: 8, 21: 9,   # hit reactions (ids 19, 20)
    22: 27, 23: 29,
    24: 12,     # lose (id 23)
}

def emi_entries(d):
    out, off = [], 0x800
    n = struct.unpack_from('<I', d, 0)[0]
    for i in range(1, n + 1):
        size = struct.unpack_from('<I', d, 16 * i)[0]
        out.append((off, size))
        off += (size + 0x7FF) & ~0x7FF
    return out

def build_voices(pf_se, dan_se):
    import vab
    zvh = vab.parse_vh(pf_se, 0x1000)
    zvb_off = 0x1000 + ((zvh['hdr_end'] + 0x7FF) & ~0x7FF)
    zvags = vab.vags(zvh, pf_se[zvb_off:])
    (o0, s0), (o1, s1), (o2, s2) = emi_entries(dan_se)
    vh = bytearray(dan_se[o1:o1 + s1])
    dvh = vab.parse_vh(dan_se, o1)
    body = bytearray()
    sizes = [0] * 256
    for slot in range(1, dvh['vs'] + 1):
        v = zvags[VOICE_MAP[slot] - 1]
        v = v + bytes(-len(v) % 16)
        body += v
        sizes[slot] = len(v) >> 3
    # tones: 8 kHz samples
    tbase = 32 + 128 * 16
    for i, t in enumerate(dvh['tones']):
        if t['vag'] <= 0:
            continue
        p = tbase + 32 * i
        vh[p + 4] = t['min'] + 30           # center
        vh[p + 5] = 57                      # shift
    struct.pack_into('<256H', vh, tbase + dvh['ps'] * 16 * 32, *sizes)
    struct.pack_into('<I', vh, 12, len(vh) + len(body))      # file size
    out = bytearray(dan_se[:0x800])
    struct.pack_into('<I', out, 48, len(body))                # entry 2 size
    out[0x800:] = dan_se[o0:o0 + s0] + bytes(-s0 % 0x800)
    out += vh + bytes(-len(vh) % 0x800)
    out += body + bytes(-len(body) % 0x800)
    return bytes(out)

def voices_main(a):
    # zangief.py voices SE0AA.PAC SE_PL0A.EMI OUT.EMI [--wav DIR]
    rd = lambda p: open(p, 'rb').read()
    out = build_voices(rd(a[0]), rd(a[1]))
    open(a[2], 'wb').write(out)
    print('voices: %d bytes' % len(out))
    if '--wav' in a:
        import vab
        d = a[a.index('--wav') + 1]
        os.makedirs(d, exist_ok=True)
        pf = rd(a[0]); zvh = vab.parse_vh(pf, 0x1000)
        zvags = vab.vags(zvh, pf[0x1000 + ((zvh['hdr_end'] + 0x7FF) & ~0x7FF):])
        for i, v in enumerate(zvags):
            vab.wav(os.path.join(d, 'zangief_%02d.wav' % (i + 1)), vab.decode_vag(v), 8000)
        dan = rd(a[1]); (o0, s0), (o1, s1), (o2, s2) = emi_entries(dan)
        dvh = vab.parse_vh(dan, o1)
        for i, v in enumerate(vab.vags(dvh, dan[o2:o2 + s2])):
            vab.wav(os.path.join(d, 'dan_%02d.wav' % (i + 1)), vab.decode_vag(v), 11025)

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'voices':
        voices_main(a[1:]); sys.exit(0)
    if len(a) < 6:
        print(__doc__); sys.exit(1)
    sheet = a[a.index('--sheet') + 1] if '--sheet' in a else None
    rd = lambda p: open(p, 'rb').read()
    out, n, g, e1 = build(rd(a[0]), rd(a[1]), rd(a[2]), rd(a[3]), rd(a[4]), sheet)
    open(a[5], 'wb').write(out)
    print('%d frames, graphics 0x%X bytes, bank 0x%X bytes' % (n, g, e1))
