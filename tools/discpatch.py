#!/usr/bin/env python3
"""Replace files inside a PSX disc image (raw 2352 BIN or single-disc PBP).

Sectors are Mode 2 Form 1; EDC/ECC are recomputed for every rewritten sector.
A replacement file must not be larger than the original (it is written in
place, padded with zeros to whole sectors; the directory size is unchanged).

usage:
  discpatch.py IN OUT ISO_PATH=LOCAL_FILE [ISO_PATH=LOCAL_FILE ...]
IN/OUT may be .bin or .pbp (OUT gets the same format as IN).
"""
import hashlib, os, struct, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SECT = 2352
BLOCK = 0x9300  # PBP block: 16 sectors

# ---------------- EDC / ECC ----------------
ECC_F = [0] * 256
ECC_B = [0] * 256
EDC_LUT = [0] * 256
for i in range(256):
    j = ((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF
    ECC_F[i] = j
    ECC_B[i ^ j] = i
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    EDC_LUT[i] = e

def edc(data):
    e = 0
    for b in data:
        e = (e >> 8) ^ EDC_LUT[(e ^ b) & 0xFF]
    return e

def _ecc_block(src, major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    out = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = src[index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t
            b ^= t
            a = ECC_F[a]
        a = ECC_B[ECC_F[a] ^ b]
        out[major] = a
        out[major + major_count] = a ^ b
    return out

def fix_sector(s):
    """Recompute EDC+ECC of a Mode 2 Form 1 sector (bytearray of 2352)."""
    assert s[15] == 2, 'not mode 2'
    if s[18] & 0x20:
        # form 2: EDC over subheader + 2324 bytes (optional, keep if zero)
        if s[2348:2352] != b'\0\0\0\0':
            s[2348:2352] = struct.pack('<I', edc(s[16:16 + 8 + 2324]))
        return s
    s[0x818:0x81C] = struct.pack('<I', edc(s[0x10:0x818]))
    addr = s[12:16]
    s[12:16] = b'\0\0\0\0'
    p = _ecc_block(s[0xC:], 86, 24, 2, 86)
    s[0x81C:0x81C + 172] = p
    q = _ecc_block(s[0xC:], 52, 43, 86, 88)
    s[0x8C8:0x8C8 + 104] = q
    s[12:16] = addr
    return s

# ---------------- image access ----------------
class BinImage:
    def __init__(self, path):
        self.data = bytearray(open(path, 'rb').read())

    def get(self, lba):
        return bytearray(self.data[lba * SECT:(lba + 1) * SECT])

    def put(self, lba, s):
        self.data[lba * SECT:(lba + 1) * SECT] = s

    def save(self, path):
        open(path, 'wb').write(self.data)

class PbpImage:
    def __init__(self, path):
        self.raw = bytearray(open(path, 'rb').read())
        offs = struct.unpack_from('<8I', self.raw, 8)
        self.psar = offs[7]
        assert self.raw[self.psar:self.psar + 12] == b'PSISOIMG0000', 'only single-disc PBP supported'
        self.base = self.psar + 0x100000
        self.idx = self.psar + 0x4000
        self.cache = {}
        self.dirty = set()

    def _entry(self, n):
        return struct.unpack_from('<IH', self.raw, self.idx + n * 32)

    def _block(self, n):
        if n not in self.cache:
            off, ln = self._entry(n)
            blk = bytes(self.raw[self.base + off:self.base + off + ln])
            self.cache[n] = bytearray(blk if ln == BLOCK else zlib.decompress(blk, -15))
        return self.cache[n]

    def get(self, lba):
        b = self._block(lba // 16)
        o = (lba % 16) * SECT
        return bytearray(b[o:o + SECT])

    def put(self, lba, s):
        b = self._block(lba // 16)
        o = (lba % 16) * SECT
        b[o:o + SECT] = s
        self.dirty.add(lba // 16)

    def save(self, path):
        # Readers (e.g. pcsx_rearmed) derive a block's size from the next
        # block's offset, so blocks must stay contiguous and in order: the
        # whole data area is rebuilt and the STARTDAT trailer moved after it.
        nblocks = 0
        while self._entry(nblocks)[1] != 0:
            nblocks += 1
        startdat = self.psar + struct.unpack_from('<I', self.raw, self.psar + 0xC)[0]
        trailer = bytes(self.raw[startdat:])
        data = bytearray()
        for n in range(nblocks):
            off, ln = self._entry(n)
            if n in self.dirty:
                c = zlib.compressobj(9, zlib.DEFLATED, -15)
                blk = c.compress(bytes(self.cache[n])) + c.flush()
                if len(blk) >= BLOCK:
                    blk = bytes(self.cache[n])
            else:
                blk = bytes(self.raw[self.base + off:self.base + off + ln])
            struct.pack_into('<IH', self.raw, self.idx + n * 32, len(data), len(blk))
            data += blk
        data += b'\0' * ((-len(data)) % 16)
        out = bytearray(self.raw[:self.base]) + data
        struct.pack_into('<I', out, self.psar + 0xC, len(out) - self.psar)
        out += trailer
        open(path, 'wb').write(out)

def open_image(path):
    return PbpImage(path) if path.lower().endswith('.pbp') else BinImage(path)

# ---------------- ISO9660 ----------------
def iso_read(img, lba, size):
    out = bytearray()
    while len(out) < size:
        out += img.get(lba)[24:24 + 2048]
        lba += 1
    return bytes(out[:size])

def iso_find(img, isopath):
    pvd = iso_read(img, 16, 2048)
    assert pvd[1:6] == b'CD001'
    root = pvd[156:156 + 34]
    ext, size = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
    parts = [p for p in isopath.strip('/').upper().split('/') if p]
    for i, part in enumerate(parts):
        data = iso_read(img, ext, size)
        p = 0
        found = None
        while p < len(data):
            ln = data[p]
            if ln == 0:
                p = (p // 2048 + 1) * 2048
                continue
            rec = data[p:p + ln]
            nm = rec[33:33 + rec[32]].decode('ascii', 'replace').split(';')[0].upper()
            if nm == part:
                found = (struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0])
                break
            p += ln
        if not found:
            raise FileNotFoundError(isopath)
        ext, size = found
    return ext, size

def replace_file(img, isopath, content):
    lba, size = iso_find(img, isopath)
    if len(content) > size:
        raise ValueError('%s: new file %d > original %d' % (isopath, len(content), size))
    content = content + b'\0' * ((-len(content)) % 2048)
    for i in range(0, len(content), 2048):
        s = img.get(lba + i // 2048)
        new = content[i:i + 2048]
        if s[24:24 + 2048] == new:
            continue
        s[24:24 + 2048] = new
        img.put(lba + i // 2048, fix_sector(s))

def main(argv):
    src, dst = argv[0], argv[1]
    img = open_image(src)
    for spec in argv[2:]:
        isopath, local = spec.split('=', 1)
        replace_file(img, isopath, open(local, 'rb').read())
    img.save(dst)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
