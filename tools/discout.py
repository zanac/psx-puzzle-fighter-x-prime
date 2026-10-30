#!/usr/bin/env python3
"""Disc image input/output for the X" tools: read a BIN, a CUE (one or more
BIN files, e.g. a Redump set) or a single-disc PBP, and write the result as
BIN + CUE and as PBP.

A PBP built from a BIN/CUE input has no DATA.PSP (the PSP-side loader), so it
is meant for emulators (PCSX ReARMed, DuckStation, Beetle PSX...). A PBP
input keeps its own header and loader, so its patched copy behaves as the
original did.
"""
import hashlib, os, re, struct, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D

SECT = D.SECT
BLOCK = D.BLOCK
SYNC = bytes.fromhex('00ffffffffffffffffffff00')

# Track layout of the full NTSC-U disc (data + 2 CD-DA tracks), in sectors
# from the start of the image: (number, audio, index 00, index 01)
KNOWN_LAYOUT = [(1, False, 0, 0), (2, True, 222654, 222804), (3, True, 241929, 242079)]
TITLE = 'Super Puzzle Fighter II Turbo X"'
DISC_ID = 'SLUS00418'

def bcd(n):
    return (n // 10) << 4 | (n % 10)

def unbcd(b):
    return (b >> 4) * 10 + (b & 0xF)

def msf(lba):
    return (lba // 4500, lba // 75 % 60, lba % 75)

def msf_str(lba):
    return '%02d:%02d:%02d' % msf(lba)

class Disc:
    """img: object with get/put/save (discpatch BinImage or PbpImage);
    tracks: list of (number, audio, index00, index01) in image sectors."""
    def __init__(self, img, tracks, total, pbp):
        self.img, self.tracks, self.total, self.pbp = img, tracks, total, pbp

    def blocks(self):
        """Raw image data in chunks (patched content included)."""
        if self.pbp:
            n = 0
            while self.img._entry(n)[1] != 0:
                yield bytes(self.img._block(n))
                n += 1
        else:
            data = self.img.data
            for i in range(0, len(data), BLOCK):
                yield bytes(data[i:i + BLOCK])

# ---------------- input ----------------
def _data_end(data):
    """First sector (after the ISO) without a Mode 2 sync pattern."""
    n = len(data) // SECT
    lo, hi = 16, n
    if data[(n - 1) * SECT:(n - 1) * SECT + 12] == SYNC:
        return n
    while lo < hi:              # data first, then audio: binary search
        mid = (lo + hi) // 2
        if data[mid * SECT:mid * SECT + 12] == SYNC:
            lo = mid + 1
        else:
            hi = mid
    return lo

def _guess_tracks(data):
    total = len(data) // SECT
    if _data_end(data) >= total:
        return [(1, False, 0, 0)]
    tracks = [t for t in KNOWN_LAYOUT if t[3] < total]
    return tracks

def _parse_cue(path):
    base = os.path.dirname(os.path.abspath(path))
    files, cur = [], None
    for line in open(path, encoding='latin-1'):
        w = line.strip()
        m = re.match(r'FILE\s+"(.*)"\s+(\w+)', w) or re.match(r'FILE\s+(\S+)\s+(\w+)', w)
        if m:
            cur = {'path': os.path.join(base, m.group(1)), 'tracks': []}
            files.append(cur)
            continue
        m = re.match(r'TRACK\s+(\d+)\s+(\S+)', w)
        if m:
            cur['tracks'].append({'no': int(m.group(1)), 'audio': m.group(2).upper() == 'AUDIO', 'idx': {}})
            continue
        m = re.match(r'INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)', w)
        if m:
            mm, ss, ff = int(m.group(2)), int(m.group(3)), int(m.group(4))
            cur['tracks'][-1]['idx'][int(m.group(1))] = (mm * 60 + ss) * 75 + ff
    data = bytearray()
    tracks = []
    for f in files:
        off = len(data) // SECT
        data += open(f['path'], 'rb').read()
        for t in f['tracks']:
            i1 = t['idx'].get(1, 0) + off
            i0 = t['idx'].get(0, t['idx'].get(1, 0)) + off
            tracks.append((t['no'], t['audio'], i0, i1))
    return data, tracks

def load(path):
    low = path.lower()
    if low.endswith('.pbp'):
        img = D.PbpImage(path)
        toc = img.raw[img.psar + 0x800:img.psar + 0x800 + 0x400]
        e = [toc[i:i + 10] for i in range(0, len(toc), 10)]
        ntracks = unbcd(e[1][7])
        tracks = []
        for t in e[3:3 + ntracks]:
            i0 = (unbcd(t[3]) * 60 + unbcd(t[4])) * 75 + unbcd(t[5]) - 150
            i1 = (unbcd(t[7]) * 60 + unbcd(t[8])) * 75 + unbcd(t[9]) - 150
            tracks.append((unbcd(t[2]), t[0] & 0x40 == 0, i0, i1))
        n = total = 0
        while img._entry(n)[1] != 0:
            n += 1
        # all blocks hold 16 sectors except possibly the last one
        last = img._block(n - 1)
        total = (n - 1) * 16 + len(last) // SECT
        return Disc(img, tracks, total, True)
    if low.endswith('.cue'):
        data, tracks = _parse_cue(path)
    else:
        data = bytearray(open(path, 'rb').read())
        cue = os.path.splitext(path)[0] + '.cue'
        tracks = None
        if os.path.exists(cue):
            files = [l for l in open(cue, encoding='latin-1') if l.strip().upper().startswith('FILE')]
            if len(files) == 1:
                tracks = _parse_cue(cue)[1]
        if tracks is None:
            tracks = _guess_tracks(data)
    img = D.BinImage.__new__(D.BinImage)
    img.data = data
    return Disc(img, tracks, len(data) // SECT, False)

def to_raw(disc):
    """A PBP disc as a raw (BIN-like) disc, so its size can change. The PBP
    header, PSP loader and STARTDAT trailer are kept as a template for
    write_pbp."""
    if not disc.pbp:
        return disc
    raw = bytearray()
    for b in disc.blocks():
        raw += b
    pimg = disc.img
    start = pimg.psar + struct.unpack_from('<I', pimg.raw, pimg.psar + 0xC)[0]
    img = D.BinImage.__new__(D.BinImage)
    img.data = raw
    out = Disc(img, list(disc.tracks), len(raw) // SECT, False)
    out.template = (bytes(pimg.raw[:pimg.psar + 0x100000]), bytes(pimg.raw[start:]), pimg.psar)
    return out

# ---------------- output ----------------
def write_bin(disc, base):
    with open(base + '.bin', 'wb') as out:
        for b in disc.blocks():
            out.write(b)
    with open(base + '.cue', 'w') as c:
        c.write('FILE "%s" BINARY\n' % (os.path.basename(base) + '.bin'))
        for no, audio, i0, i1 in disc.tracks:
            c.write('  TRACK %02d %s\n' % (no, 'AUDIO' if audio else 'MODE2/2352'))
            if i0 < i1:
                c.write('    INDEX 00 %s\n' % msf_str(i0))
            c.write('    INDEX 01 %s\n' % msf_str(i1))

def _sfo(entries):
    """PARAM.SFO from [(key, value)]: str -> utf-8, int -> int32."""
    keys = data = b''
    index = b''
    for k, v in entries:
        if isinstance(v, int):
            raw, fmt, ln, mx = struct.pack('<I', v), 0x0404, 4, 4
        else:
            raw = v.encode() + b'\0'
            mx = (len(raw) + 3) // 4 * 4
            raw, fmt, ln = raw + b'\0' * (mx - len(raw)), 0x0204, len(v) + 1
        index += struct.pack('<HHIII', len(keys), fmt, ln, mx, len(data))
        keys += k.encode() + b'\0'
        data += raw
    keys += b'\0' * ((-len(keys)) % 4)
    kstart = 20 + len(index)
    return struct.pack('<4sIIII', b'\0PSF', 0x101, kstart, kstart + len(keys), len(entries)) + index + keys + data

def _toc(disc):
    first, last = disc.tracks[0], disc.tracks[-1]
    def ent(ctrl, point, a, b):
        return bytes([ctrl, 0, point]) + bytes(a) + b'\0' + bytes(b)
    lead = msf(disc.total + 150)
    toc = ent(0x41 if not first[1] else 0x01, 0xA0, (0, 0, 0), (bcd(first[0]), 0x20, 0))
    toc += ent(0x01 if last[1] else 0x41, 0xA1, (0, 0, 0), (bcd(last[0]), 0, 0))
    toc += ent(0x01 if last[1] else 0x41, 0xA2, (0, 0, 0), tuple(bcd(x) for x in lead))
    for no, audio, i0, i1 in disc.tracks:
        toc += ent(0x01 if audio else 0x41, bcd(no),
                   tuple(bcd(x) for x in msf(i0 + 150)), tuple(bcd(x) for x in msf(i1 + 150)))
    return toc

def _write_psar(out, psar, disc):
    """Compressed blocks + index after a header already written up to
    psar + 0x100000. Returns the size of the data area."""
    idx, off = bytearray(), 0
    for b in disc.blocks():
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        blk = c.compress(b) + c.flush()
        if len(blk) >= len(b):
            blk = b
        idx += struct.pack('<IHH', off, len(blk), 0) + hashlib.sha1(blk).digest()[:16] + b'\0' * 8
        out.write(blk)
        off += len(blk)
    pad = (-off) % 16
    out.write(b'\0' * pad)
    assert len(idx) <= 0x100000 - 0x4000, 'image too large for one PSISOIMG'
    end = out.tell()
    out.seek(psar + 0x4000)
    out.write(b'\0' * (0x100000 - 0x4000))
    out.seek(psar + 0x4000)
    out.write(idx)
    out.seek(end)
    return off + pad

def write_pbp(disc, path):
    if disc.pbp:
        disc.img.save(path)
        return
    tpl = getattr(disc, 'template', None)
    if tpl:
        # original header and PSP loader; new TOC, index, data; STARTDAT after
        head, trailer, psar = tpl
        head = bytearray(head)
        toc = _toc(disc)
        head[psar + 0x800:psar + 0xC00] = bytes(0x400)
        head[psar + 0x800:psar + 0x800 + len(toc)] = toc
        with open(path, 'wb') as out:
            out.write(head)
            size = _write_psar(out, psar, disc)
            out.write(trailer)
            out.seek(psar + 0xC)
            out.write(struct.pack('<I', 0x100000 + size))
        return
    sfo = _sfo([('BOOTABLE', 1), ('CATEGORY', 'ME'), ('DISC_ID', DISC_ID), ('DISC_VERSION', '1.00'),
                ('LICENSE', 'Built by the X\' patch tools'), ('PARENTAL_LEVEL', 3),
                ('PSP_SYSTEM_VER', '3.01'), ('REGION', 0x8000), ('TITLE', TITLE)])
    psar = 0x28 + len(sfo)
    psar += (-psar) % 0x10
    hdr = struct.pack('<4sI8I', b'\0PBP', 0x10000, 0x28, *([0x28 + len(sfo)] * 6), psar)
    head = bytearray(0x100000)
    head[0:12] = b'PSISOIMG0000'
    head[0x400:0x400 + 11] = ('_' + DISC_ID[:4] + '_' + DISC_ID[4:]).encode()
    toc = _toc(disc)
    head[0x800:0x800 + len(toc)] = toc
    with open(path, 'wb') as out:
        out.write(hdr + sfo + b'\0' * (psar - 0x28 - len(sfo)))
        out.write(head)
        size = _write_psar(out, psar, disc)
        out.seek(psar + 0xC)
        out.write(struct.pack('<I', 0x100000 + size))

def write_all(disc, base):
    """base.bin + base.cue + base.pbp"""
    write_bin(disc, base)
    write_pbp(disc, base + '.pbp')
    return [base + '.bin', base + '.cue', base + '.pbp']

def output_base(path):
    root, ext = os.path.splitext(path)
    return root if ext.lower() in ('.bin', '.cue', '.pbp') else path

USAGE = '''usage: discout.py IN.(bin|cue|pbp) OUT [ISO_PATH=LOCAL_FILE ...]
Writes OUT.bin + OUT.cue + OUT.pbp (OUT may carry any of those extensions),
replacing the given files inside the ISO first (same rules as discpatch.py).'''

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)
    disc = load(sys.argv[1])
    for spec in sys.argv[3:]:
        isopath, local = spec.split('=', 1)
        D.replace_file(disc.img, isopath, open(local, 'rb').read())
    print('\n'.join(write_all(disc, output_base(sys.argv[2]))))
