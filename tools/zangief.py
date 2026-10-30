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
       [--select PF_SELECT.PAC] [--quotefont PL00_OBJ.EMI,...] [--selmes SELMES.MDL]
       zangief.py voices SE0AA.PAC SE_PL0A.EMI OUT.EMI [--wav DIR]   (SE_PL0B.EMI)
       zangief.py name SELECT.EMI SE0D.PAC OUT.EMI    (his name call on the select screen)
       zangief.py ending OPEN09.PAC HARD_END.EMI OUT.EMI [--png PREVIEW]
                  (ZG_END.EMI: his Arcade staff roll figure, see build_end)
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
    23: 'idle', 24: 'flex',
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

# --- select / VS portrait (step 5) ---------------------------------------------
# Pocket Fighter's select art (/STAGE/SELECT.PAC frame 554: Zangief, fists
# crossed; palettes from 586, one per cell palette offset). SPF2T draws a
# portrait as up to 10 "child" sprites listed per character (table
# 0x8018B66C, see xp_zlist): Zangief's are 4 quadrants of a 128x112 box
# around the parent (like Dan's frames 143-146), each with its own 15-colour
# palette. Two versions: a close-up for the select screen, the whole art for
# the VS screen. The block is at the start of the graphics entry (the record
# bank is full); record graphics offsets are relative to that entry too:
#   +0x000 select list, +0x040 VS list (u16 count, then frame, palette, x, y)
#   +0x080 select palettes, +0x1C0 VS palettes (10 x 16 colours each, the
#          size of the game's per-character portrait palette copy)
#   +0x300 records (select 0-3, VS 4-7), graphics offsets after the frames
PORT_SIZE = 0x300 + 8 * 44
PF_SEL_FRAME, PF_SEL_PAL = 554, 586
# source rectangle (PF pixels, art mirrored to face right), scale, and where
# it goes in the 128x112 box (the select screen shows about x 13-127, y
# 10-80 of it: the screen edge and the Counter Gem panel cover the rest)
PORTRAITS = (((22, 0, 231, 127), 0.55, (13, 10)),      # select: face and fists
             ((7, 6, 245, 213), 0.5, (4, 4)))          # VS: the whole art

def quantise_fine(im):
    """15 colours, k-means refined (portraits: many shades per quadrant)"""
    from PIL import Image
    px = [p[:3] for p in im.getdata() if p[3]]
    strip = Image.new('RGB', (len(px), 1))
    strip.putdata(px)
    q = strip.quantize(colors=15, method=Image.Quantize.MAXCOVERAGE, kmeans=3)
    pal = q.getpalette()[:45]
    cols = [tuple(pal[i:i + 3]) for i in range(0, 45, 3)]
    while len(cols) < 15:
        cols.append((0, 0, 0))
    return cols

def pf_select_art(selpac):
    from PIL import Image
    e0 = P.pac_entries(selpac)
    e = {0: e0[11], 1: e0[10], 2: e0[12]}
    tbl = e[1]
    words = struct.unpack_from('<%dI' % (len(tbl) // 4), tbl)
    rec = struct.unpack_from('<HBBHHHH', tbl, PF_SEL_FRAME * 12)
    img = P.render(e, words, rec)
    cols = P.palette(e, PF_SEL_PAL, 32)
    im = Image.new('RGBA', (len(img[0]), len(img)))
    im.putdata([(*cols[v], 255) if v else (0, 0, 0, 0) for row in img for v in row])
    return im.transpose(Image.FLIP_LEFT_RIGHT)

def build_portraits(selpac, gfx_base):
    """-> (block bytes, graphics bytes, preview images)"""
    from PIL import Image
    art = pf_select_art(selpac)
    lists, pals, recs, gfx, shows = [], [], [], bytearray(), []
    for (x0, y0, x1, y1), s, (dx, dy) in PORTRAITS:
        crop = art.crop((x0, y0, x1, y1))
        crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
        a = crop.split()[3].point(lambda v: 255 if v > 128 else 0)
        crop.putalpha(a)
        crop = crop.crop((0, 0, min(crop.width, 128 - dx), min(crop.height, 112 - dy)))
        box = Image.new('RGBA', (128, 112), (0, 0, 0, 0))
        box.alpha_composite(crop, (dx, dy))
        if os.environ.get('XP_PORT_FRAME'):     # debug: show the 128x112 box
            from PIL import ImageDraw
            ImageDraw.Draw(box).rectangle((0, 0, 127, 111), outline=(255, 0, 0, 255))
            for k in range(0, 112, 16):
                ImageDraw.Draw(box).line((0, k, 6, k), fill=(0, 255, 0, 255))
        shows.append(box)
        lst = struct.pack('<H', 4)
        prow = bytearray()
        for q in range(4):
            qx, qy = (q & 1) * 64, (q >> 1) * 56
            part = Image.new('RGBA', (128, 112), (0, 0, 0, 0))
            part.alpha_composite(box.crop((qx, qy, qx + 64, qy + 56)), (qx, qy))
            cols = quantise_fine(part)
            rec, lz = make_record(part, 64, 56, cols, {})
            recs.append(struct.pack('<I', gfx_base + len(gfx)) + rec)
            gfx += lz + bytes(-len(lz) % 4)
            pi = (0, 1, 2, 4)[q]        # palette 3 of a side is rewritten by the game
            prow += bytes(pi * 32 - len(prow))
            prow += struct.pack('<16H', 0, *[bgr555(c) for c in cols])
            lst += struct.pack('<hhhh', len(recs) - 1, pi, 0, 0)
        lists.append(lst)
        pals.append(bytes(prow) + bytes(0x140 - len(prow)))
    blk = bytearray(0x300)
    blk[0:len(lists[0])] = lists[0]
    blk[0x40:0x40 + len(lists[1])] = lists[1]
    blk[0x80:0x1C0] = pals[0]
    blk[0x1C0:0x300] = pals[1]
    blk += b''.join(recs)
    return bytes(blk), bytes(gfx), shows

# --- staff roll figure (step 7) ----------------------------------------------
# The Arcade staff roll shows the player's character beside the credits: a
# "child sprite" figure like the select portraits, made from a list in the
# figure banks that every ENDINGnn.EMI loads at 0x800A1000 (graphics) /
# 0x800B1000 (records). Dan has a small single frame instead. For Zangief,
# ZG_END.EMI is loaded over those banks after the ENDING file (the other
# figures are not needed then); its first entry is a block like the select
# portrait block, at the start of the graphics:
#   +0x00  list: u16 count, then (record, palette, x, y) per child
#   +0x7C  'ZGND' (the code checks it to know the block is in)
#   +0x80  10 palettes (P1's portrait slots; palette 3 is avoided, the game
#          rewrites it)
#   +0x300 44-byte records (offsets relative to the block), then the LZ cells
# The figure is the one picture of his Pocket Fighter Arcade opening:
# Zangief in a suit on the airplane, adjusting his glasses
# (/STAGE/OPEN09.PAC):
#   type 16: 14 frame records (u16 index, u8 columns, u8 rows, u16 x, u16 y,
#            u16 cells, u16 flags), then per frame one u16 per cell
#            (column-major; 0xFFFF = empty; tile = bits 0-10, palette =
#            bits 11-15)
#   type 17: palettes; type 267: the tiles, 16x16 4bpp, uncompressed
# Frame 0 is the scene's frame, frames 1 and 2 the bust in its two poses
# (240x128, cut at the bottom by the scene's frame: on the staff roll it
# stands on the bottom edge of the screen).
PF_OPEN_FRAMES = (1, 2)
FINALE_FLEXES = 8           # HARD finale: 8 x 14 frames of flexing, then still
END_MAGIC = b'ZGND'
END_POS = (-150, -16)       # picture's top-left from the figure's position
                            # (its right and bottom edges, cut in the source,
                            # fall on the screen's edges)
END_PALS = (0, 1, 2, 4, 5, 6, 7, 8, 9)

def pf_open_art(openpac, frame):
    """-> RGBA picture, {(r,g,b): (palette, index)} of its pixels"""
    from PIL import Image
    e = P.pac_entries(openpac)
    t = e[16]
    hw = struct.unpack_from('<%dH' % (len(t) // 2), t)
    idx, cw, ch = struct.unpack_from('<HBB', t, frame * 12)
    im = Image.new('RGBA', (cw * 16, ch * 16), (0, 0, 0, 0))
    px = im.load()
    pal_of = {}
    for c in range(cw * ch):
        v = hw[idx + c]
        if v == 0xFFFF:
            continue
        tile, pal = v & 0x7FF, v >> 11
        cols = struct.unpack_from('<16H', e[17], pal * 32)
        raw = e[267][tile * 128:tile * 128 + 128]
        cx, cy = (c // ch) * 16, (c % ch) * 16
        for y in range(16):
            for x in range(16):
                b = raw[y * 8 + x // 2]
                k = (b >> 4) if x & 1 else (b & 15)
                if k:
                    px[cx + x, cy + y] = (pal, k, 0, 255)
                    pal_of.setdefault(pal, cols)
    return im, pal_of

def build_end(openpac, template, frame=PF_OPEN_FRAMES[0], preview=None):
    """-> ZG_END.EMI: entry 0 the block above, entry 1 a stub"""
    from PIL import Image
    art, pal_of = pf_open_art(openpac, frame)
    pals = sorted(pal_of)
    assert len(pals) <= len(END_PALS), pals
    slot = {p: END_PALS[i] for i, p in enumerate(pals)}
    rgb = lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    W, H = art.size
    bb = art.getbbox()
    pieces = []                 # (palette, image) per palette and column band
    for p in pals:
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        src, dst = art.load(), layer.load()
        cols = [rgb(c) for c in pal_of[p]]
        for y in range(H):
            for x in range(W):
                v = src[x, y]
                if v[3] and v[0] == p:
                    dst[x, y] = cols[v[1]] + (255,)
        lb = layer.getbbox()
        if not lb:
            continue
        for x0 in range(lb[0], lb[2], 96):      # <= 6 x 8 = 48 cells
            band = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            band.alpha_composite(layer.crop((x0, 0, min(x0 + 96, lb[2]), H)), (x0, 0))
            if band.getbbox():
                pieces.append((p, band))
    ox, oy = -END_POS[0], -END_POS[1]
    n = len(pieces)
    recs, gfx = [], bytearray()
    lst = struct.pack('<H', n)
    for k, (p, band) in enumerate(pieces):
        cols = [rgb(c) for c in pal_of[p][1:]]
        # exact colours: index i + 1 for the pixel's own index
        cache = {}
        for i, c in enumerate(cols):
            cache.setdefault(c, i)
        rec, lz = make_record(band, ox, oy, cols, cache)
        recs.append((rec, bytes(lz) + bytes(-len(lz) % 4)))
        lst += struct.pack('<hhhh', k, slot[p], 0, 0)
    base = 0x300 + 44 * n
    blk = bytearray(0x300)
    blk[0:len(lst)] = lst
    blk[0x7C:0x80] = END_MAGIC
    for p in pals:
        o = 0x80 + slot[p] * 32
        blk[o:o + 32] = struct.pack('<16H', 0, *[c or 0x0421 for c in pal_of[p][1:]])
    off = base
    for rec, lz in recs:
        blk += struct.pack('<I', off) + rec
        off += len(lz)
    for rec, lz in recs:
        blk += lz
    assert len(blk) <= 0x10000, hex(len(blk))
    if preview:
        show = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        for p, band in pieces:
            show.alpha_composite(band)
        show.save(preview)
    stub = bytes(4)
    hdr = bytearray(template[:0x800])
    struct.pack_into('<I', hdr, 0, 2)
    for i, e in enumerate((blk, stub)):
        struct.pack_into('<II', hdr, 16 * (i + 1), len(e), 0)
        hdr[16 * (i + 1) + 8:16 * (i + 1) + 12] = e[:4]
    out = hdr + blk + bytes(-len(blk) % 0x800) + stub + bytes(-len(stub) % 0x800)
    return bytes(out), n, len(blk)

# --- WINNER screen (step 5) ---------------------------------------------------
# The WINNER screen draws, from the winner's own record bank, one of four win
# quotes (frames 239-242: text strips, two lines of 8x16 monospace text) and a
# small icon (frame 246); Dan's file also has effect frames 243-245. Every
# index up to 246 must hold a valid record (an empty one where Zangief has
# nothing). The quotes are set with the glyphs of Dan's own quotes (only the
# letters those contain).
# WINNER screen quotes (frames 239-242): Zangief's own four win quotes from
# Pocket Fighter (MDL/SELMES.MDL, decoded with tools/pf_texts.py from the
# user's disc). Without it, these stand-ins:
WIN_QUOTES = (("Ahahaha! I crush you like a", "tin can! You are too tiny!"),
              ("Dance with me again when you", "grow some muscles!"),
              ("Gems or no gems! Strength", "wins in the end!"),
              ("Ahahaha! Strong muscles win", "again! I am the strongest!"))
ZG_PF_INDEX = 9                 # Zangief in Pocket Fighter's character order

# The quote font: every character's own win quotes on SPF2T's WINNER screen
# (2 lines of 8x16 text per frame; a 1-line quote is drawn at y 8). The
# letters are taken from these frames (first frame of each file, then the
# quotes in order; checked against the glyph cells).
QUOTE_SOURCES = {
    'PL00': (220, (("Baby, baby, baby...", "I didn't even sweat!"),
                   ("Oh Damn...I think I split a hair.", ""),
                   ("It's not whether I win or lose,", "just as long as I piss you off!"),
                   ("The sun's rising. I will rest'til", "the morrow, then win again."))),
    'PL01': (155, (("Why waste my time?", "You'll just keep losing!"),
                   ("I'm the strongest puzzle fighter", "in the world!"),
                   ("Sorry! But I don't know how to", "pull punches."),
                   ("I'm too smart to fall for your", "stupid patterns."))),
    'PL02': (228, (("You need more training to stand a", "chance."),
                   ("You've fought well. I was honored.", ""),
                   ("Don't tell me, you only know how", "to play fighting games?"),
                   ("All too easy...You just don't know", "the bliss of the bombs."))),
    'PL03': (228, (("I have proven the difference", "between us: you just suck."),
                   ("You must learn when to defend and", "when to attack!"),
                   ("Not only am I disappointed,", "inside I am laughing at you."),
                   ("It was a beautiful victory,", "if I do say so myself!"))),
    'PL04': (373, (("And again, I won with ease.", ""),
                   ("Hey, it's not time for you to walk", "away! Try again."),
                   ("Why do you hold back? Your", "overconfidence is your weakness!"),
                   ("My revenge begins with you.", ""))),
    'PL05': (321, (("No one can interfere with my", "plans!"),
                   ("I won't rest until this girl is", "finally happy!"),
                   ("I'll put an end to the evil curse", "in my blood at any cost!"),
                   ("I am the one who lives in darkness", "and shatters it!"))),
    'PL06': (154, (("You're about as sharp as a circle!", ""),
                   ("Meow...", "How'd you like them apples?"),
                   ("I won by a tail's length.", "Now go back to my litterbox!"),
                   ("You're stoned! Get it? Ha ha ha...", ""))),
    'PL07': (212, (("Whew, you were good!", "I've got to train harder!"),
                   ("Yes...All part of the plan!", ""),
                   ("You're quick, smart, and cheap!", "No wait...that's me! Ha ha ha."),
                   ("Only my second game, and I am", "already the best!"))),
    'PL08': (262, (("Let the gems hold you as I plan", "for your death!"),
                   ("You've been very bad.", "Your punishment:the death penalty!"),
                   ("What you don't recognize me!?", "Cyberbots is Capcom's #1 game!"),
                   ("I know you want me...but can you", "handle it?"))),
    'PL9A': (235, (("I am Akuma! Also a master puzzler!", ""),
                   ("You're just a pathetic example of", "carbon-based wastage."),
                   ("To beat you is not enough.", "I must destroy you!!"),
                   ("Evil is what I am.", "Death is what I bring."),
                   ("I'll make you cry like I did when", "my daddy died!"),
                   ("Amateur! Go home and practice", "dragon punches!"),
                   ("I thought I taught you well.", "You know nothing! Dummy!"),
                   ("Yeahhh! I'm the strongest there", "is! But don't tell Sagat..."))),
}
# a glyph no SPF2T quote has: the closing double quote (drawn here, after
# the apostrophe)
EXTRA_GLYPHS = {'”': ["........", "13f.13f.", "31f.31f.", "73f.73f.", "39..39..",
                       "f...f..."] + ["........"] * 10}

N_FRAMES = 247              # Dan's file: frames 0-246
ICON_SRC = (96, 20, 196, 120)   # PF select art (mirrored): his face
# (frame 246 is drawn with the character's body palette, as for Dan: see
# xp_zwinpal)

def quote_font(files):
    """files: {'PL00': EMI bytes, ...} (at least PL9A). The glyphs are not
    boxed: take each letter where its neighbours are spaces if possible, so
    no stray pixels come along."""
    import spf_sprites as SP
    font, score = {}, {}
    for name, (first, quotes) in QUOTE_SOURCES.items():
        if name not in files:
            continue
        e = SP.entries(files[name])
        recs = SP.records(e[1])
        for k, lines in enumerate(quotes):
            _, px = SP.frame(e[0], recs[first + k])
            rows = [(0, lines[0]), (16, lines[1])] if lines[1] else [(8, lines[0])]
            for y0, text in rows:
                for i, ch in enumerate(text):
                    if ch == ' ':
                        continue
                    sc = (i > 0 and text[i - 1] != ' ') + (i + 1 < len(text) and text[i + 1] != ' ')
                    if ch not in font or sc < score[ch]:
                        font[ch] = [row[8 * i:8 * i + 8] for row in px[y0:y0 + 16]]
                        score[ch] = sc
    for ch, rows in EXTRA_GLYPHS.items():
        if ch not in font:
            font[ch] = [[int(c, 16) if c != '.' else 0 for c in r] for r in rows]
    return font

def pf_win_quotes(selmes):
    """Zangief's four win quotes from Pocket Fighter's SELMES.MDL"""
    import pf_texts
    q = pf_texts.win_quotes(selmes)[ZG_PF_INDEX * 4:ZG_PF_INDEX * 4 + 4]
    return tuple(tuple(x.split(' / ')) for x in q)

def cells_record(px, x, y, gfx_off):
    """Index image (multiple of 16 in both sizes) -> (record without offset
    word, LZ bytes); cells as in make_record (row-major, present cells only)."""
    h, w = len(px) // 16, len(px[0]) // 16
    cells, mask = [], []
    for cy in range(h):
        for cx in range(w):
            cell = [row[cx * 16:cx * 16 + 16] for row in px[cy * 16:cy * 16 + 16]]
            present = any(any(r) for r in cell)
            mask.append(present)
            if present:
                cells.append(cell)
    if not cells:
        mask = [False] * len(mask)
        cells = [[[0] * 16 for _ in range(16)]]
    units = (len(cells) + 15) // 16 * 16
    rows = [[0] * 256 for _ in range(units)]
    for k, cell in enumerate(cells):
        for yy in range(16):
            rows[(k // 16) * 16 + yy][(k % 16) * 16:(k % 16) * 16 + 16] = cell[yy]
    hw = lzh.from_pixels(rows)
    lz = lz_fast(hw)
    words = [0] * 8
    for i, m in enumerate(mask):
        if m:
            words[i // 32] |= 1 << (31 - i % 32)
    rec = struct.pack('<IhhBBBB', gfx_off, x, y, h, w, units, 0x40) + struct.pack('<8I', *words)
    return rec, lz

def winner_frames(template, cols, selpac, gfx_off, quote_files=None, quotes=None):
    """-> {frame index: record}, LZ bytes (frames 239-242 quotes, 246 icon,
    and the shared empty record, returned under key None)"""
    from PIL import Image
    files = dict(quote_files or {})
    files.setdefault('PL9A', template)
    font = quote_font(files)
    out, gfx = {}, bytearray()
    def add(px, x, y):
        rec, lz = cells_record(px, x, y, gfx_off + len(gfx))
        gfx.extend(lz + bytes(-len(lz) % 4))
        return rec
    out[None] = add([[0] * 16 for _ in range(16)], 0, 0)
    for k, lines in enumerate(quotes or WIN_QUOTES):
        w = max(len(t) for t in lines) * 8
        w = (w + 15) // 16 * 16
        px = [[0] * w for _ in range(32)]
        for j, text in enumerate(lines):
            for i, ch in enumerate(text):
                if ch == ' ':
                    continue
                g = font[ch]                    # KeyError: no SPF2T quote has it
                for yy in range(16):
                    px[16 * j + yy][8 * i:8 * i + 8] = g[yy]
        out[239 + k] = add(px, 0, 0)
    if selpac:
        face = pf_select_art(selpac).crop(ICON_SRC).resize((32, 32), Image.LANCZOS)
        cache = {}
        px = [[(1 + nearest(cols, p[:3], cache)) if p[3] > 128 else 0 for p in
               [face.getpixel((x, y)) for x in range(32)]] for y in range(32)]
        out[246] = add(px, -16, -16)
    return out, bytes(gfx)

def build(pac, mdl, first, template, exe, sheet=None, selpac=None, quote_files=None,
          quotes=None):
    pf = PFFrames(pac)
    anims = build_anims(mdl)
    used = {name: anims[name] for name in set(STATES.values())}
    keys = sorted({e[1] for ents, _ in used.values() for e in ents})
    comps = {k: pf.composite(*k) for k in keys}
    cols = quantise([c[0] for c in comps.values()])
    cache = {}
    index, recs, gfx = {}, [], bytearray()
    if selpac:                      # portrait block first (graphics entry +0)
        blk, pgfx, _ = build_portraits(selpac, PORT_SIZE)
        assert len(blk) == PORT_SIZE
        gfx += blk + pgfx
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
    base = LISTOFF + 4 * (N_STATES + 8)
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
    # HARD finale (xp_zhland): his flex for about two seconds, then still
    finale = base + len(scripts)
    for k in range(FINALE_FLEXES):
        for dur, fr in ((6, 337), (8, 338)):
            scripts += struct.pack('<HHhh', dur, 0, index[(fr, 0)], 0) + bytes([0, 0, 0, 0, 0, 0, 3, 0])
    scripts += struct.pack('<HHhh', 4095, 0x8000, index[(337, 0)], 0) + bytes([0, 0, 0, 0, 0, 0, 3, 0])
    lst = b''.join(struct.pack('<I', per_state[s]) for s in range(N_STATES))
    lst += b''.join(struct.pack('<I', t) for t in tails)
    lst += struct.pack('<II', base, hit_hi)
    lst += struct.pack('<II', hit_hi, calm_hi)          # idle 0 + pinch 1 scripts
    lst += struct.pack('<I', finale)                    # entry 58: HARD finale
    # WINNER screen frames, and a valid (empty) record at every index up to 246
    wf, wgfx = winner_frames(template, cols, selpac, len(gfx), quote_files, quotes)
    gfx += wgfx
    assert len(recs) <= 239, len(recs)
    for n in range(len(recs), N_FRAMES):
        recs.append(wf.get(n, wf[None]))
    assert len(recs) * 44 <= PALOFF
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

# --- name call on the select screen (step 5) ----------------------------------
# Confirming a character plays its name from SELECT.EMI's sound bank (sound id
# from the per-character table 0x8016FED4, Dan = 0x1A). Ids 0x14 and 0x19 are
# never used by the US game; id 0x14 (program 1, tone 4 = tone 20, VAG 13)
# gets Pocket Fighter's "Zangief!" (/SE/SE0D.PAC VAG 4), resampled so it fits
# VAG 13's size (nothing else in the bank moves), see xp_zname.
NAME_ID, NAME_TONE, NAME_VAG = 0x14, 20, 13
PF_NAME = 4                 # SE0D.PAC VAG number
NAME_CENTER = 79            # names play at 11025 Hz with centre 72

def build_select_name(select_emi, se0d):
    import vab
    d = bytearray(select_emi)
    ents = emi_entries(d)
    vh = vab.parse_vh(d, ents[0 + 1][0])
    o2, s2 = ents[2]
    # source: Pocket Fighter sample at its own rate
    pv = vab.parse_vh(se0d, 0x1000)
    off = 0x1000 + ((pv['hdr_end'] + 0x7FF) & ~0x7FF)
    src = vab.decode_vag(vab.vags(pv, se0d[off:])[PF_NAME - 1])
    t = [t for t in pv['tones'] if t['vag'] == PF_NAME][0]
    rate_in = 44100 * 2 ** ((t['min'] - t['center']) / 12)
    rate_out = 11025 * 2 ** ((72 - NAME_CENTER) / 12)
    n = int(len(src) * rate_out / rate_in)
    pcm = []
    for i in range(n):              # linear resampling
        p = i * rate_in / rate_out
        j = int(p); f = p - j
        a = src[j]; b = src[j + 1] if j + 1 < len(src) else 0
        pcm.append(int(a + (b - a) * f))
    # slot: zero block, data (first flagged 4, last 1), silent end block 7
    size = vh['sizes'][NAME_VAG]
    room = (size // 16 - 2) * 28
    assert len(pcm) <= room, (len(pcm), room)
    blocks = bytearray(vab.encode_blocks(pcm))
    blocks += bytes(size - 32 - len(blocks))
    blocks[1] = 4
    blocks[-15] = 1
    vag = bytes(16) + bytes(blocks) + bytes([0, 7]) + bytes(14)
    assert len(vag) == size
    p = o2 + sum(vh['sizes'][1:NAME_VAG])
    d[p:p + size] = vag
    tbase = ents[1][0] + 32 + 128 * 16
    d[tbase + 32 * NAME_TONE + 4] = NAME_CENTER
    return bytes(d)

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
    if a and a[0] == 'ending':    # zangief.py ending OPEN09.PAC HARD_END.EMI OUT.EMI [--png P]
        png = a[a.index('--png') + 1] if '--png' in a else None
        out, n, size = build_end(open(a[1], 'rb').read(), open(a[2], 'rb').read(), preview=png)
        open(a[3], 'wb').write(out)
        print('%s: %d pieces, block 0x%X bytes' % (a[3], n, size)); sys.exit(0)
    if a and a[0] == 'name':      # zangief.py name SELECT.EMI SE0D.PAC OUT.EMI
        out = build_select_name(open(a[1], 'rb').read(), open(a[2], 'rb').read())
        open(a[3], 'wb').write(out); sys.exit(0)
    if len(a) < 6:
        print(__doc__); sys.exit(1)
    sheet = a[a.index('--sheet') + 1] if '--sheet' in a else None
    rd = lambda p: open(p, 'rb').read()
    selpac = rd(a[a.index('--select') + 1]) if '--select' in a else None
    qfiles = {}                     # --quotefont PLxx_OBJ.EMI,... (SPF2T)
    if '--quotefont' in a:
        for f in a[a.index('--quotefont') + 1].split(','):
            qfiles[os.path.basename(f)[:4].upper()] = rd(f)
    quotes = pf_win_quotes(rd(a[a.index('--selmes') + 1])) if '--selmes' in a else None
    out, n, g, e1 = build(rd(a[0]), rd(a[1]), rd(a[2]), rd(a[3]), rd(a[4]), sheet, selpac,
                          qfiles, quotes)
    open(a[5], 'wb').write(out)
    print('%d frames, graphics 0x%X bytes, bank 0x%X bytes' % (n, g, e1))
