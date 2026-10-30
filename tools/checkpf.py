#!/usr/bin/env python3
"""Refuse anything but Pocket Fighter NTSC-U (SLUS-00653).

usage: checkpf.py <Pocket Fighter image (.bin|.cue|.pbp)>
Zangief's graphics, voices, stage, music and ending picture are built from
this disc (tools/zangief.py, tools/pf_stage.py); their sizes are part of
the patched executable's file table, so the disc must be this exact version.
"""
import hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discout, discpatch as D

EXE = '/SLUS_006.53'
EXPECTED = 'adaa2e34af6212bc52195befe943bd7d73136c49'

def main(path):
    img = discout.load(path).img
    try:
        lba, size = D.iso_find(img, EXE)
    except Exception:
        sys.exit('%s: no %s, this is not Pocket Fighter NTSC-U (SLUS-00653)' % (path, EXE))
    h = hashlib.sha1(D.iso_read(img, lba, size)).hexdigest()
    if h != EXPECTED:
        sys.exit('%s: %s sha1 %s does not match Pocket Fighter NTSC-U (%s)' % (path, EXE, h, EXPECTED))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
