#!/usr/bin/env python3
"""Create the executable patch (JSON) that lets build.sh run without armips.

usage: mkpatch.py ORIGINAL_EXE PATCHED_EXE FILES_BIN OUT.json
ORIGINAL_EXE is SLUS_004.18 from the original disc, PATCHED_EXE the one
armips assembled, FILES_BIN the file table it was assembled with
(tools/discexpand.py table). The patch holds the changed byte runs, the
SHA-1 of both executables and of the file table. The executable holds only
this project's code and tables: no game data (Zangief's files are built
from the user's Pocket Fighter disc by build.sh, and only their sizes, in
the file table, are part of the executable).
"""
import hashlib, json, sys

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

def main(src, dst, table, out):
    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b)
    patch = {'game': 'Super Puzzle Fighter II Turbo (NTSC-U, SLUS-00418)',
             'name': 'Super Puzzle Fighter II Turbo X" (PSX)',
             'needs': 'Pocket Fighter (NTSC-U, SLUS-00653)',
             'exe': {'path': '/SLUS_004.18',
                     'sha1_in': hashlib.sha1(a).hexdigest(),
                     'sha1_out': hashlib.sha1(b).hexdigest(),
                     'runs': runs(a, b)},
             'files_table_sha1': hashlib.sha1(open(table, 'rb').read()).hexdigest()}
    json.dump(patch, open(out, 'w'), indent=1)

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:])
