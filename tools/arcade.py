"""Build the arcade set spf2enh.zip (CPS2) from your own MAME sets.

usage: arcade.py spf2t.zip sgemf.zip OUT.zip

spf2t.zip: Super Puzzle Fighter II Turbo (Euro 960529) - parent set, split or merged
sgemf.zip: Super Gem Fighter Mini Mix / Pocket Fighter - Zangief's graphics and sound
Only the program and graphics of the hack come out of this script: every
byte of game data is taken from your sets."""
import sys, os, zipfile, zlib, tempfile, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cps2crypt, cps2patch, cps2gfx, cps2preview, cps2label, cps2icons, cps2names, cps2quotes, cps2castle, pfarc, arcade_zangief, qsconv

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XP = os.path.join(HERE, 'arcade', 'xprime')
SRC = os.path.join(HERE, 'arcade', 'src')

SPF2T = {   # name: crc32 (MAME spf2t)
    'pzfe.03': 0x2af51954, 'pzf.04': 0xb80649e2, 'pzf.14m': 0x2d4881cb, 'pzf.16m': 0x4b0fd1be,
    'pzf.18m': 0xe43aac33, 'pzf.20m': 0x7f536ff1, 'pzf.01': 0x600fb2a3, 'pzf.02': 0x496076e0,
    'pzf.11m': 0x78442743, 'pzf.12m': 0x399d2c7b, 'spf2t.key': 0x4c4dc7e3}
SGEMF = {   # name: crc32 (MAME sgemf); only data is read, nothing is decrypted
    'pcfu.03': 0xac2e8566, 'pcf.04': 0xf4314c96, 'pcf.05': 0x215655f6, 'pcf.06': 0xea6f13ea,
    'pcf.07': 0x5ac6d5ea, 'pcf.13m': 0x22d72ab9, 'pcf.15m': 0x16a4813c, 'pcf.17m': 0x1097e035,
    'pcf.19m': 0xd362d874, 'pcf.14m': 0x0383897c, 'pcf.16m': 0x76f91084, 'pcf.18m': 0x756c3754,
    'pcf.20m': 0x9ec9277d, 'pcf.01': 0x254e5f33, 'pcf.02': 0x6902f4f9, 'pcf.11m': 0xa5dea005,
    'pcf.12m': 0x4ce235fe}

def read_set(path, want):
    """{name: bytes} found by CRC (any folder, any name) or by name"""
    z = zipfile.ZipFile(path); got = {}
    bycrc = {i.CRC: i for i in z.infolist()}
    for name, crc in want.items():
        i = bycrc.get(crc)
        if i is None:
            raise SystemExit('%s: %s (crc %08x) not found' % (path, name, crc))
        got[name] = z.read(i)
    return got

def ips(data, p):
    data = bytearray(data); assert p[:5] == b'PATCH'; i = 5
    while p[i:i + 3] != b'EOF':
        off = int.from_bytes(p[i:i + 3], 'big'); n = int.from_bytes(p[i + 3:i + 5], 'big'); i += 5
        if n == 0:
            rn = int.from_bytes(p[i:i + 2], 'big'); data[off:off + rn] = bytes([p[i + 2]]) * rn; i += 3
        else:
            data[off:off + n] = p[i:i + n]; i += n
    return bytes(data)

def swap(b): return bytes(x for i in range(0, len(b), 2) for x in (b[i + 1], b[i]))

ZNAME = 0x9F000             # ZANGIEF's two HUD name lists (code_zangief.s)
ZICONS = 0x9F100            # select icons: palettes and tile codes (code_select.s)
ZPREV = 0x9F500             # Zangief's Counter Gem block (code_select.s)
ZSELNAME = 0x9F700          # his select screen name: pseudo entry, frame, positions (code_select.s)
ZPORT = 0x9F800             # his select portrait: pseudo entry, palette, positions, frame (code_select.s)
ZWIN = 0x9D000              # his WINNER screen picture, same layout (code_quotes.s)
SONGS = [(7, 24)]           # Pocket Fighter song -> SPF2T song slot: 7 the castle stage's music
# Zangief's voices: Dan's offset (id = 0x250 + offset) -> (Pocket Fighter voice
# id, SPF2T slot s; P2 plays s + 0x200 on channel 11). Dan's arcade offset n is
# his PSX voice slot n + 1 (checked on the waveforms), so the PSX choice
# (docs/ZANGIEF-VOICES.md) carries over; PF voice ids play bank 7 instruments,
# matched to the PSX VAGs on the waveforms too (docs/QSOUND.md).
ZVOICES = {2: (0x1C7, 0x13C),    # PSX slot 3 -> VAG 05 punch (bank 7 #37)
           3: (0x1F2, 0x13D),    # slot 4 -> VAG 28 arms-up move (#7)
           4: (0x1ED, 0x13E),    # slot 5 -> VAG 26 special moves (#23)
           5: (0x1DB, 0x13F),    # slot 6 -> VAG 13 (#33)
           6: (0x1D8, 0x199),    # slot 7 -> VAG 10 has no arcade take: VAG 11 (#0)
           7: (0x1E6, 0x19A),    # slot 8 -> VAG 21 taunt (#20)
           15: (0x1CC, 0x19B),   # slot 16 -> VAG 06 has no arcade take: VAG 07 (#45)
           20: (0x1E8, 0x19C)}   # slot 19 -> VAG 23 Double Lariat (#49)
ZVOICE_TAB = 0x9E300        # 32 words: his P1 id by Dan's offset (code_voice.s)
VOICE_VELOCITY = 0x3F       # as Dan's voices
VELOCITY = 26                # note velocity of the converted songs: as loud as SPF2T's own music
QROM_SIZE = 0x400000        # pzfen.13s, QSound 0x400000- (code banks 0x40-)
ZCRED = 0x9C000             # his staff roll picture (code_quotes.s)
WIN_DX = 36                 # left of the object, where the others' pictures sit (Ryu's)

def picture(base, idx, pal, x0, y0, ztiles):
    """a still picture as a pseudo entry (long: duration/flags, long: frame),
    its palette (16 words), the position list and a type 12 frame; its tiles go
    to ztiles (codes TILE0-)"""
    spr = []
    for ty in range(0, idx.shape[0], 16):
        for tx in range(0, idx.shape[1], 16):
            t = np.full((16, 16), 15, np.uint8); blk = idx[ty:ty + 16, tx:tx + 16]; t[:blk.shape[0], :blk.shape[1]] = blk
            if (t == 15).all(): continue
            spr.append((x0 + tx, y0 + ty, arcade_zangief.TILE0 + len(ztiles))); ztiles.append(t)
    pos = base + 8 + 32
    frame = pos + 4 * len(spr)
    out = struct.pack('>II', 0x0B540000, frame) + struct.pack('>16H', *pal)
    out += b''.join(struct.pack('>hh', x, y) for x, y, c in spr)
    out += struct.pack('>HHHI', 12, len(spr), len(spr) - 1, pos)
    out += b''.join(struct.pack('>HH', c, 0) for x, y, c in spr)
    return out
ZG_PATTERN = [(3, 3, 3, 2, 2, 2), (3, 3, 3, 2, 2, 2), (4, 4, 4, 1, 1, 1), (4, 4, 4, 1, 1, 1)]

def scroll1_art(r, gfx, p03, p04):
    """new scroll1 pictures (gfx list changed in place): Dan's Counter Gem preview
    for his new pattern, ZANGIEF's HUD name; returns pzf.04 with their lists"""
    G = cps2gfx.Gfx(gfx)
    prog = swap(p03) + swap(p04)
    van = swap(r['pzfe.03']) + swap(r['pzf.04'])
    used = lambda img, chars: set(e >> 16 for c in chars for e in cps2preview.entries(img, c))
    # tiles of the previews X' redrew (Morrigan, Ryu, Hsien-Ko, Felicia, Sakura) are free now
    free = sorted(used(van, (0, 2, 4, 6, 7)) - used(prog, range(11)))
    alloc = cps2preview.Scroll1Alloc(G, free)
    model = cps2preview.learn(G, prog, [c for c in range(10) if c != 8])
    dan = 10
    im = cps2preview.draw(G, prog, dan, cps2preview.pattern(prog, dan), model)
    lst = cps2preview.install(alloc, prog, dan, im)
    # Zangief's preview (Siberian Bear), in a copy of Dan's whole block
    zim = cps2preview.draw(G, prog, dan, ZG_PATTERN, model)
    zl = cps2preview.install(alloc, prog, dan, zim)
    blk = cps2preview.PREVIEW + 0x11E * dan     # the 25 preview longs are the last
    lst0 = blk - 6 - 45 * 4                      # 25 of the box list (6 + 70 longs)
    zblock = prog[lst0:blk] + zl
    names, _ = cps2label.Labels(G, prog).build(alloc)
    gfx[:] = G.roms()
    return cps2patch.put(p04, 0x80000, [(cps2preview.PREVIEW + 0x11E * dan, lst),
                                        (ZNAME, names[0]), (ZNAME + 0x80, names[1]), (ZPREV, zblock)])

def srcs(d, kind):
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.s') and f.startswith(kind)) if os.path.isdir(d) else []

def build(spf2t, sgemf, out, verbose=True):
    r = read_set(spf2t, SPF2T)
    key = r['spf2t.key']
    # program: X' (KScl) then X" (arcade/src). code_* blocks are opcodes of the
    # encrypted pzfe.03 (patched decrypted, then encrypted again); data_* blocks
    # are read as data and go in as they are; pzf.04 (0x80000-) is not encrypted.
    groups = {'code': [os.path.join(XP, 'code_03.patch.s')] + srcs(SRC, 'code'),
              'data': [os.path.join(XP, 'data_03.patch.s')] + srcs(SRC, 'data'),
              'xp04': [os.path.join(XP, 'data_04.patch.s')]}   # KScl's pzf.04 file offsets
    patches, syms = cps2patch.assemble(groups)
    # opcodes are encrypted only below 0x80000 (the key's range): code above
    # that, in pzf.04, goes in as it is, like data
    code03 = [p for p in patches['code'] if p[0] < 0x80000]
    patches['data'] += [p for p in patches['code'] if p[0] >= 0x80000]
    dec = cps2crypt.decrypt(r['pzfe.03'], key)
    dec = cps2patch.put(dec, 0, code03)
    p03 = cps2crypt.encrypt(dec, key)
    p03 = cps2patch.put(p03, 0, [p for p in patches['data'] if p[0] < 0x80000])
    p04 = cps2patch.put(r['pzf.04'], 0, patches['xp04'])
    p04 = cps2patch.put(p04, 0x80000, [p for p in patches['data'] if p[0] >= 0x80000])
    gfx = [ips(r['pzf.' + g], open(os.path.join(XP, 'gfx', 'pzf-%s.ips' % g), 'rb').read())
           for g in ('14m', '16m', '18m', '20m')]
    p04 = scroll1_art(r, gfx, p03, p04)
    # Zangief: his animations (blob in pzf.04) and graphics (new ROMs, 0xC00000-)
    s = read_set(sgemf, SGEMF)
    pfprog = swap(b''.join(s[n] for n in ('pcfu.03', 'pcf.04', 'pcf.05', 'pcf.06', 'pcf.07')))
    pfgfx = cps2gfx.Gfx(groups=[(0, [s['pcf.13m'], s['pcf.15m'], s['pcf.17m'], s['pcf.19m']]),
                               (0x1000000, [s['pcf.14m'], s['pcf.16m'], s['pcf.18m'], s['pcf.20m']])])
    zblob, ztiles = arcade_zangief.build(pfprog, pfgfx, verbose)
    # the new select icons: tiles after his, codes and palettes at ZICONS
    zi, zp = cps2icons.zangief(pfgfx, pfprog, cps2gfx.Gfx(gfx))
    pfgfx2 = pfgfx
    di, dp = cps2icons.dan(cps2gfx.Gfx(gfx), swap(p03) + swap(p04))
    codes = []
    for idx in (zi, di):
        for t in cps2icons.tiles_of(idx):
            codes.append(arcade_zangief.TILE0 + len(ztiles)); ztiles.append(t)
    icons = struct.pack('>16H', *zp) + struct.pack('>16H', *dp) + struct.pack('>18H', *codes)
    # ZANGIEF in the select screen's name font: a type 12 frame
    spf = pfarc.PF(swap(p03) + swap(p04), cps2gfx.Gfx(gfx), postable=0x2DB1C)
    nm = cps2names.compose(spf)
    w = nm.shape[1]; x0 = -(w // 2)
    spr = []
    for tx in range(0, w, 16):
        t = np.full((16, 16), 15, np.uint8); blk = nm[:, tx:tx + 16]; t[:, :blk.shape[1]] = blk
        spr.append((x0 + tx, -8, arcade_zangief.TILE0 + len(ztiles))); ztiles.append(t)
    pos = ZSELNAME + 8
    frame = pos + 4 * len(spr)
    selname = struct.pack('>II', 0x0B540000, frame)
    selname += b''.join(struct.pack('>hh', x, y) for x, y, c in spr)
    selname += struct.pack('>HHHI', 12, len(spr), len(spr) - 1, pos)
    selname += b''.join(struct.pack('>HH', c, 0) for x, y, c in spr)
    # his select portrait (Pocket Fighter's), 128x112 like the others, one palette
    pi, pp = cps2icons.zangief_portrait(pfgfx2, pfprog)
    port = picture(ZPORT, pi, pp, -64, -56, ztiles)
    # his WINNER screen picture: the same Pocket Fighter portrait, full body
    wi, wp = cps2icons.zangief_winner(pfgfx2, pfprog)
    win = picture(ZWIN, wi, wp, -(wi.shape[1] // 2) - WIN_DX, -(wi.shape[0] // 2), ztiles)
    # and in the ending's staff roll: centred, as tall as the others' (~180 pixels)
    ci, cp = cps2icons.zangief_winner(pfgfx2, pfprog, cps2icons.CRED_SCALE)
    cred = picture(ZCRED, ci, cp, -(ci.shape[1] // 2), -(ci.shape[0] // 2), ztiles)
    quotes, _ = cps2quotes.build(pfprog)
    # his stage: Pocket Fighter's castle in place of Dan's stage (code_castle.s)
    castle, ctiles, _ = cps2castle.build(swap(p03) + swap(p04), pfprog, pfgfx2,
                                         arcade_zangief.TILE0 + len(ztiles))
    ztiles += ctiles
    vtab = struct.pack('>32H', *[ZVOICES.get(o, ZVOICES[2])[1] for o in range(32)])
    p04 = cps2patch.put(p04, 0x80000, [(ZVOICE_TAB, vtab), (arcade_zangief.ZBLOB, zblob), (ZICONS, icons), (ZSELNAME, selname), (ZPORT, port), (ZWIN, win), (ZCRED, cred),
                                       (cps2quotes.ZQUOTES, quotes)] + castle)
    files = {'pzfen.03': p03, 'pzfen.04': p04}
    for g, data in zip(('13m', '15m', '17m', '19m'), arcade_zangief.gfx_roms(ztiles)):
        files['pzfen.' + g] = data
    for g, data in zip(('14m', '16m', '18m', '20m'), gfx):
        files['pzfen.' + g] = data
    # sound: Pocket Fighter's castle music (and Zangief's voices) converted to
    # SPF2T's driver: a new Z80 program and a new sample ROM
    songs = list(SONGS)
    for off, (pf_id, slot) in ZVOICES.items():
        for ch, sl in ((10, slot), (11, slot + 0x200)):
            songs.append((pf_id, sl, dict(channel=ch, flags=0x10, velocity=VOICE_VELOCITY)))
    z80, q, info = qsconv.convert(s['pcf.01'] + s['pcf.02'], s['pcf.11m'] + s['pcf.12m'],
                                  r['pzf.01'] + r['pzf.02'], r['pzf.11m'] + r['pzf.12m'], songs, VELOCITY)
    if verbose: print('sound:', info)
    files['pzfen.01'], files['pzfen.02'] = z80[:0x20000], z80[0x20000:]
    files['pzfen.13s'] = q + bytes(QROM_SIZE - len(q))
    for n in ('pzf.11m', 'pzf.12m', 'spf2t.key'):
        files[n] = r[n]
    zf = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
    for n in sorted(files):
        zi = zipfile.ZipInfo(n, (1996, 12, 24, 23, 32, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(zi, files[n])
    zf.close()
    if verbose:
        for n in sorted(files): print('%-10s %7x  crc %08x' % (n, len(files[n]), zlib.crc32(files[n])))
    return files

if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    build(*sys.argv[1:])
