#!/usr/bin/env python3
"""Create a game-data-free patch (JSON) from an original and a patched image.

usage: mkpatch.py ORIGINAL.(bin|pbp) PATCHED.(bin|pbp) OUT.json
Only the files changed by build.sh are compared; the patch holds the changed
byte runs plus SHA-1 hashes of each file before and after.
"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D

FILES = ['/SLUS_004.18', '/DATA/FIRST.EMI', '/DATA/FIRSTE.EMI']

def read(img, path):
    lba, size = D.iso_find(img, path)
    return D.iso_read(img, lba, size)

def runs(a, b, gap=16):
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        last = i
        while j < n and j - last <= gap:
            if a[j] != b[j]:
                last = j
            j += 1
        out.append([i, b[i:last + 1].hex()])
        i = last + 1
    return out

def main(src, dst, out):
    a_img, b_img = D.open_image(src), D.open_image(dst)
    patch = {'game': 'Super Puzzle Fighter II Turbo (NTSC-U, SLUS-00418)',
             'name': "Super Puzzle Fighter II Turbo X' (PSX)", 'files': []}
    for path in FILES:
        a, b = read(a_img, path), read(b_img, path)
        assert len(a) == len(b), path
        patch['files'].append({'path': path,
                               'sha1_in': hashlib.sha1(a).hexdigest(),
                               'sha1_out': hashlib.sha1(b).hexdigest(),
                               'runs': runs(a, b)})
    json.dump(patch, open(out, 'w'), indent=1)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:])
