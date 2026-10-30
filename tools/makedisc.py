#!/usr/bin/env python3
"""Build the output disc: replace files, add new ones, write BIN+CUE+PBP.

usage: makedisc.py IN.(bin|cue|pbp) OUT [ISO_PATH=LOCAL ...] [+NAME=LOCAL ...]
  ISO_PATH=LOCAL  replace an existing file (same or smaller size)
  +NAME=LOCAL     add a new file to /DATA (tools/discexpand.py); new files
                  must be given in the same order as to `discexpand.py table`
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D
import discout, discexpand

def main(argv):
    src, dst = argv[0], argv[1]
    disc = discout.load(src)
    adds = []
    for spec in argv[2:]:
        name, local = spec.split('=', 1)
        if name.startswith('+'):
            adds.append((name[1:], open(local, 'rb').read()))
        else:
            D.replace_file(disc.img, name, open(local, 'rb').read())
    disc = discout.to_raw(disc)
    if adds:
        lbas, delta = discexpand.expand(disc, adds)
        for n, l in lbas.items():
            print('added %-14s lba %d' % (n, l))
        print('CD-DA moved by %d sectors' % delta)
    for f in discout.write_all(disc, discout.output_base(dst)):
        print('wrote %s' % f)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
