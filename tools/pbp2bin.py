#!/usr/bin/env python3
"""Convert a single-disc PSX PBP (PSISOIMG0000) to BIN/CUE (2352-byte sectors)."""
import struct, sys, zlib

def bcd(b):
    return (b >> 4) * 10 + (b & 0xF)

def main(src, out_base):
    f = open(src, 'rb')
    hdr = f.read(0x28)
    assert hdr[:4] == b'\0PBP', 'not a PBP'
    offs = struct.unpack('<8I', hdr[8:0x28])
    psar = offs[7]
    f.seek(psar)
    magic = f.read(12)
    assert magic == b'PSISOIMG0000', magic
    f.seek(psar + 0x400)
    disc_id = f.read(16).split(b'\0')[0].decode(errors='replace')
    # TOC: 10-byte entries starting at psar+0x800
    f.seek(psar + 0x800)
    toc = f.read(0x3C0)
    entries = [toc[i:i + 10] for i in range(0, len(toc), 10)]
    tracks = []
    last_track = None
    lead_out = None
    for e in entries:
        ctrl, tno, point = e[0], e[1], e[2]
        if ctrl == 0 and point == 0:
            break
        if point == 0xA1:
            last_track = bcd(e[7])
        elif point == 0xA2:
            lead_out = (bcd(e[7]), bcd(e[8]), bcd(e[9]))
        elif point < 0xA0:
            tracks.append((bcd(point), ctrl, (bcd(e[7]), bcd(e[8]), bcd(e[9]))))
    print('disc id', disc_id, 'tracks', len(tracks), 'lead-out', lead_out)

    f.seek(psar + 0x4000)
    out = open(out_base + '.bin', 'wb')
    base = psar + 0x100000
    total = 0
    while True:
        ent = f.read(32)
        off, ln = struct.unpack('<IH', ent[:6])
        if ln == 0:
            break
        pos = f.tell()
        f.seek(base + off)
        blk = f.read(ln)
        if ln == 0x9300:
            data = blk
        else:
            data = zlib.decompress(blk, -15)
        out.write(data)
        total += len(data)
        f.seek(pos)
    out.close()
    print('wrote', total, 'bytes', total // 2352, 'sectors')

    name = out_base.split('/')[-1] + '.bin'
    with open(out_base + '.cue', 'w') as c:
        c.write('FILE "%s" BINARY\n' % name)
        for tno, ctrl, (m, s, fr) in tracks:
            lba = (m * 60 + s) * 75 + fr - 150
            typ = 'MODE2/2352' if (ctrl & 0x40) else 'AUDIO'
            c.write('  TRACK %02d %s\n' % (tno, typ))
            if tno > 1 and typ == 'AUDIO':
                pre = max(lba - 150, 0)
                c.write('    INDEX 00 %02d:%02d:%02d\n' % (pre // 4500, pre // 75 % 60, pre % 75))
            c.write('    INDEX 01 %02d:%02d:%02d\n' % (lba // 4500, lba // 75 % 60, lba % 75))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
