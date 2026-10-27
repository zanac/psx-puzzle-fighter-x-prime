#!/usr/bin/env python3
"""Apply the X' patch (JSON, made by mkpatch.py) to an original disc image.

usage: applypatch.py PATCH.json ORIGINAL.(bin|cue|pbp) OUTPUT
Writes OUTPUT.bin + OUTPUT.cue + OUTPUT.pbp, whatever the input format
(OUTPUT may carry one of those extensions). Pure Python 3, no dependencies.
"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D
import discout

def main(patch_path, src, dst):
    patch = json.load(open(patch_path))
    disc = discout.load(src)
    img = disc.img
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
    for f in discout.write_all(disc, discout.output_base(dst)):
        print('wrote %s' % f)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:])
