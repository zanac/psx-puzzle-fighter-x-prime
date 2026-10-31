"""Build the arcade set spf2enh.zip (CPS2) from your own MAME sets.

usage: arcade.py spf2t.zip sgemf.zip OUT.zip

spf2t.zip: Super Puzzle Fighter II Turbo (Euro 960529) - parent set, split or merged
sgemf.zip: Super Gem Fighter Mini Mix / Pocket Fighter - Zangief's graphics and sound
Only the program and graphics of the hack come out of this script: every
byte of game data is taken from your sets."""
import sys, os, zipfile, zlib, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cps2crypt, cps2patch, cps2gfx, cps2preview, arcade_zangief

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
    'pcf.20m': 0x9ec9277d}

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

def previews(r, gfx, p03, p04):
    """redraw Dan's Counter Gem preview for his new pattern (gfx list changed in place);
    returns pzf.04 with his new tile list"""
    G = cps2gfx.Gfx(gfx)
    prog = swap(p03) + swap(p04)
    van = swap(r['pzfe.03']) + swap(r['pzf.04'])
    used = lambda img, chars: set(e >> 16 for c in chars for e in cps2preview.entries(img, c))
    # tiles of the previews X' redrew (Morrigan, Ryu, Hsien-Ko, Felicia, Sakura) are free now
    free = sorted(used(van, (0, 2, 4, 6, 7)) - used(prog, range(11)))
    model = cps2preview.learn(G, prog, [c for c in range(10) if c != 8])
    dan = 10
    im = cps2preview.draw(G, prog, dan, cps2preview.pattern(prog, dan), model)
    lst = cps2preview.install(G, prog, dan, im, free)
    gfx[:] = G.roms()
    return cps2patch.put(p04, 0x80000, [(cps2preview.PREVIEW + 0x11E * dan, lst)])

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
    p04 = previews(r, gfx, p03, p04)
    # Zangief: his animations (blob in pzf.04) and graphics (new ROMs, 0xC00000-)
    s = read_set(sgemf, SGEMF)
    pfprog = swap(b''.join(s[n] for n in ('pcfu.03', 'pcf.04', 'pcf.05', 'pcf.06', 'pcf.07')))
    pfgfx = cps2gfx.Gfx(groups=[(0, [s['pcf.13m'], s['pcf.15m'], s['pcf.17m'], s['pcf.19m']]),
                               (0x1000000, [s['pcf.14m'], s['pcf.16m'], s['pcf.18m'], s['pcf.20m']])])
    zblob, ztiles = arcade_zangief.build(pfprog, pfgfx, verbose)
    del pfgfx
    p04 = cps2patch.put(p04, 0x80000, [(arcade_zangief.ZBLOB, zblob)])
    files = {'pzfen.03': p03, 'pzfen.04': p04}
    for g, data in zip(('13m', '15m', '17m', '19m'), arcade_zangief.gfx_roms(ztiles)):
        files['pzfen.' + g] = data
    for g, data in zip(('14m', '16m', '18m', '20m'), gfx):
        files['pzfen.' + g] = data
    for n in ('pzf.01', 'pzf.02', 'pzf.11m', 'pzf.12m', 'spf2t.key'):
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
