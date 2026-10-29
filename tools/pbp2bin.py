#!/usr/bin/env python3
"""Convert a single-disc PSX PBP (PSISOIMG0000) to BIN/CUE (2352-byte sectors).

usage: pbp2bin.py GAME.pbp OUTBASE      (writes OUTBASE.bin + OUTBASE.cue)
The track list comes from the PBP TOC (as many tracks as its A1 entry says).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discout

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    disc = discout.load(sys.argv[1])
    discout.write_bin(disc, discout.output_base(sys.argv[2]))
    print('tracks %d, %d sectors' % (len(disc.tracks), disc.total))
