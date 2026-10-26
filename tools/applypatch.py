#!/usr/bin/env python3
"""Apply the X' patch (JSON, made by mkpatch.py) to an original disc image.

usage: applypatch.py PATCH.json ORIGINAL.(bin|pbp) OUTPUT.(bin|pbp)
Pure Python 3, no dependencies. The output has the input's format.
"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D

def main(patch_path, src, dst):
    patch = json.load(open(patch_path))
    img = D.open_image(src)
    for f in patch['files']:
        lba, size = D.iso_find(img, f['path'])
        data = bytearray(D.iso_read(img, lba, size))
        h = hashlib.sha1(data).hexdigest()
        if h != f['sha1_in']:
            sys.exit('%s does not match the original NTSC-U SLUS-00418 (sha1 %s)' % (f['path'], h))
        for off, hexdata in f['runs']:
            b = bytes.fromhex(hexdata)
            data[off:off + len(b)] = b
        assert hashlib.sha1(data).hexdigest() == f['sha1_out'], f['path']
        D.replace_file(img, f['path'], bytes(data))
    img.save(dst)
    print('done: %s' % dst)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:])
