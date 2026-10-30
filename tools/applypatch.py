#!/usr/bin/env python3
"""Apply the X" executable patch (JSON, made by mkpatch.py): used by
build.sh when no armips is given.

usage: applypatch.py PATCH.json SLUS_004.18 FILES_BIN OUT_EXE
FILES_BIN is the file table build.sh computed for this disc (with
Zangief's new files): it must be the one the patch was assembled with,
or the patched executable would point at the wrong sectors.
Pure Python 3, no dependencies.
"""
import hashlib, json, sys

def main(patch_path, exe, table, out):
    patch = json.load(open(patch_path))
    f = patch['exe']
    data = bytearray(open(exe, 'rb').read())
    h = hashlib.sha1(data).hexdigest()
    if h != f['sha1_in']:
        sys.exit('SLUS_004.18 does not match the original NTSC-U SLUS-00418 (sha1 %s)' % h)
    t = hashlib.sha1(open(table, 'rb').read()).hexdigest()
    if t != patch['files_table_sha1']:
        sys.exit('the new files built from your Pocket Fighter disc do not have the '
                 'expected sizes (file table sha1 %s); build with armips instead '
                 '(./build.sh ... path/to/armips)' % t)
    for off, hexdata in f['runs']:
        b = bytes.fromhex(hexdata)
        data[off:off + len(b)] = b
    if hashlib.sha1(data).hexdigest() != f['sha1_out']:
        sys.exit('patched executable sha1 mismatch')
    open(out, 'wb').write(data)

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:])
