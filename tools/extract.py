#!/usr/bin/env python3
"""Extract one file from a PSX disc image (.bin or .pbp).

usage: extract.py IMAGE ISO_PATH OUT
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discpatch as D

img = D.open_image(sys.argv[1])
lba, size = D.iso_find(img, sys.argv[2])
open(sys.argv[3], 'wb').write(D.iso_read(img, lba, size))
