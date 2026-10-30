#!/usr/bin/env python3
"""Add new files to the SPF2T disc: grow the data track, move the CD-DA
tracks after it, and list the files in an ISO directory.

The new files go right after the last file of the data track, each in its
own run of Mode 2 Form 1 sectors (EDC/ECC computed). The data track keeps a
150-sector postgap before the audio, as on the original disc. Everything
after the data track (the two CD-DA tracks) is moved by the same amount,
and the volume space size in the PVD grows by it.

The game does not read the ISO directory (it loads by LBA from its own
table, see src/files.asm), but the entries are added anyway so the disc
stays a valid ISO.

usage (library): expand(disc, [(name, data), ...], directory='/DATA')
  -> {name: lba}, delta (sectors the audio moved)
       disc: a raw discout.Disc (discout.to_raw for a PBP input)
usage (CLI):    discexpand.py IN OUT NAME=FILE ...   (writes OUT.bin/.cue/.pbp)
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D
import discout

SECT = D.SECT
POSTGAP = 150

def bcd(n):
    return (n // 10) << 4 | (n % 10)

def make_sector(lba, payload, submode):
    s = bytearray(SECT)
    s[0:12] = discout.SYNC
    m, sec, f = discout.msf(lba + 150)
    s[12:16] = bytes([bcd(m), bcd(sec), bcd(f), 2])
    sub = bytes([0, 0, submode, 0])
    s[16:24] = sub + sub
    s[24:24 + len(payload)] = payload
    return D.fix_sector(s)

def _dir_records(data):
    recs, p = [], 0
    while p < len(data):
        ln = data[p]
        if ln == 0:
            p = (p // 2048 + 1) * 2048
            continue
        recs.append(bytes(data[p:p + ln]))
        p += ln
    return recs

def _iso_extents(img, lba, size, out):
    for r in _dir_records(D.iso_read(img, lba, size)):
        nm = r[33:33 + r[32]]
        if nm in (b'\0', b'\1'):
            continue
        e, s = struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0]
        out.append((e, s))
        if r[25] & 2:
            _iso_extents(img, e, s, out)

def _both16(v):
    return struct.pack('<H', v) + struct.pack('>H', v)

def _both32(v):
    return struct.pack('<I', v) + struct.pack('>I', v)

def _new_record(template, name, lba, size):
    """A directory record like `template` (date, XA system use) for name."""
    ident = (name.upper() + ';1').encode()
    su = template[33 + template[32] + (1 - template[32] % 2):]    # system use (XA)
    body = bytearray(33)
    body[1] = 0
    body[2:10] = _both32(lba)
    body[10:18] = _both32(size)
    body[18:25] = template[18:25]
    body[25] = 0
    body[28:32] = _both16(1)
    body[32] = len(ident)
    rec = body + ident + (b'\0' if len(ident) % 2 == 0 else b'') + su
    rec[0] = len(rec)
    return bytes(rec)

def layout(disc, sizes):
    """Where the new files go, without touching the disc.
    sizes: [(name, size)] -> ({name: lba}, delta, first free lba, data end)"""
    img = disc.img
    audio = [t for t in disc.tracks if t[1]]
    data_end = audio[0][2] if audio else disc.total      # first audio sector (pregap)
    ext = []
    pvd = D.iso_read(img, 16, 2048)
    root = pvd[156:190]
    ext.append((struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]))
    _iso_extents(img, ext[0][0], ext[0][1], ext)
    last = max(e + (s + 2047) // 2048 for e, s in ext)
    lbas, pos = {}, last
    for name, size in sizes:
        lbas[name] = pos
        pos += max(1, (size + 2047) // 2048)
    new_end = max(data_end, pos + POSTGAP)
    return lbas, new_end - data_end, last, data_end, pos, new_end

def expand(disc, files, directory='/DATA'):
    assert not disc.pbp, 'use discout.to_raw first'
    img = disc.img
    lbas, delta, last, data_end, pos, new_end = layout(disc, [(n, len(d)) for n, d in files])
    raw = img.data
    tail = bytes(raw[data_end * SECT:])                 # the CD-DA tracks
    body = bytearray(raw[:last * SECT])
    for name, data in files:
        n = max(1, (len(data) + 2047) // 2048)
        for i in range(n):
            chunk = data[i * 2048:(i + 1) * 2048]
            body += make_sector(lbas[name] + i, chunk, 0x89 if i == n - 1 else 0x08)
    for lba in range(pos, new_end):                     # postgap / padding
        body += make_sector(lba, b'', 0)
    img.data = body + tail
    # tracks: audio moves by delta
    disc.tracks = [(no, au, i0 + delta, i1 + delta) if au else (no, au, i0, i1)
                   for no, au, i0, i1 in disc.tracks]
    disc.total = len(img.data) // SECT
    # PVD volume space size
    s = img.get(16)
    vs = struct.unpack_from('<I', s, 24 + 80)[0]
    s[24 + 80:24 + 88] = _both32(vs + delta)
    img.put(16, D.fix_sector(s))
    # directory entries, kept sorted by name
    dlba, dsize = D.iso_find(img, directory)
    recs = _dir_records(D.iso_read(img, dlba, dsize))
    dots, others = recs[:2], recs[2:]
    tmpl = others[-1]
    names = {r[33:33 + r[32]].split(b';')[0].decode() for r in others}
    for name, data in files:
        assert name.upper() not in names, name
        others.append(_new_record(tmpl, name, lbas[name], len(data)))
    others.sort(key=lambda r: r[33:33 + r[32]])
    out = bytearray()
    for r in dots + others:
        if len(out) // 2048 != (len(out) + len(r) - 1) // 2048:
            out += b'\0' * ((-len(out)) % 2048)          # records do not cross sectors
        out += r
    assert len(out) <= dsize, 'directory full (%d > %d)' % (len(out), dsize)
    out += b'\0' * (dsize - len(out))
    for i in range(dsize // 2048):
        sec = img.get(dlba + i)
        sec[24:24 + 2048] = out[i * 2048:(i + 1) * 2048]
        img.put(dlba + i, D.fix_sector(sec))
    return lbas, delta

# ---------------- the game's file table ----------------
TABLE = 0x80165CC0          # u32 LBA per file id; ids 0x54/0x55 are the CD-DA tracks
N_FILES = 0x54
CDDA = (0x54, 0x55)

def exe_table(exe, lbas, delta):
    """New file table (see src/files.asm): the original ids, the CD-DA LBAs
    moved by delta, then the new files in order (ids 0x56, 0x57, ...)."""
    off = TABLE - 0x80100000 + 0x800
    words = list(struct.unpack_from('<%dI' % (N_FILES + 2), exe, off))
    for i in CDDA:
        words[i] += delta
    words += list(lbas.values())
    return struct.pack('<%dI' % len(words), *words)

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'table':
    # discexpand.py table DISC EXE OUT.bin NAME=FILE ...  (layout only)
    disc = discout.load(sys.argv[2])     # layout only: a PBP needs no conversion
    sizes = []
    for spec in sys.argv[5:]:
        n, f = spec.split('=', 1)
        sizes.append((n, os.path.getsize(f)))
    lbas, delta = layout(disc, sizes)[:2]
    open(sys.argv[4], 'wb').write(exe_table(open(sys.argv[3], 'rb').read(), lbas, delta))
    for i, (n, l) in enumerate(lbas.items()):
        print('id 0x%02X %-14s lba %d' % (N_FILES + 2 + i, n, l))
    print('audio moved by %d sectors' % delta)
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    disc = discout.to_raw(discout.load(sys.argv[1]))
    files = []
    for spec in sys.argv[3:]:
        n, f = spec.split('=', 1)
        files.append((n, open(f, 'rb').read()))
    lbas, delta = expand(disc, files)
    for n, l in lbas.items():
        print('%-16s lba %d' % (n, l))
    print('audio moved by %d sectors' % delta)
    print('\n'.join(discout.write_all(disc, discout.output_base(sys.argv[2]))))
