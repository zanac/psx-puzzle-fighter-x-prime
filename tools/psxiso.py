#!/usr/bin/env python3
"""Minimal ISO9660 reader for raw 2352-byte PSX BIN images.

usage: psxiso.py IMAGE.bin list
       psxiso.py IMAGE.bin extract OUTDIR
"""
import os, struct, sys

class Bin:
    def __init__(self, path):
        self.f = open(path, 'rb')

    def raw(self, lba):
        self.f.seek(lba * 2352)
        return self.f.read(2352)

    def sector(self, lba):
        s = self.raw(lba)
        form2 = s[18] & 0x20
        return s[24:24 + (2324 if form2 else 2048)]

    def read(self, lba, size):
        out = bytearray()
        while len(out) < size:
            out += self.raw(lba)[24:24 + 2048]
            lba += 1
        return bytes(out[:size])

def walk(img, lba, size, path, out):
    data = img.read(lba, size)
    p = 0
    while p < len(data):
        ln = data[p]
        if ln == 0:
            p = (p // 2048 + 1) * 2048
            continue
        rec = data[p:p + ln]
        ext = struct.unpack('<I', rec[2:6])[0]
        sz = struct.unpack('<I', rec[10:14])[0]
        flags = rec[25]
        nl = rec[32]
        name = rec[33:33 + nl]
        p += ln
        if name in (b'\0', b'\1'):
            continue
        name = name.decode('ascii', 'replace').split(';')[0]
        full = path + '/' + name
        if flags & 2:
            walk(img, ext, sz, full, out)
        else:
            out.append((full, ext, sz))

def listing(img):
    pvd = img.read(16, 2048)
    assert pvd[1:6] == b'CD001'
    root = pvd[156:156 + 34]
    ext = struct.unpack('<I', root[2:6])[0]
    sz = struct.unpack('<I', root[10:14])[0]
    out = []
    walk(img, ext, sz, '', out)
    return out

if __name__ == '__main__':
    img = Bin(sys.argv[1])
    files = listing(img)
    if sys.argv[2] == 'list':
        for n, e, s in files:
            print('%-40s lba=%-7d size=%d' % (n, e, s))
    elif sys.argv[2] == 'extract':
        od = sys.argv[3]
        for n, e, s in files:
            dst = os.path.join(od, n.lstrip('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            # STR/XA files are form2: dump raw-ish user data is not needed here
            with open(dst, 'wb') as o:
                o.write(img.read(e, s))
