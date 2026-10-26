#!/usr/bin/env python3
"""Refuse to patch anything but the original NTSC-U SLUS_004.18."""
import hashlib, sys

EXPECTED = 'f34910945e42a0e56f5cebe51cf123d6112965f9'
h = hashlib.sha1(open(sys.argv[1], 'rb').read()).hexdigest()
if h != EXPECTED:
    sys.exit('SLUS_004.18 sha1 %s does not match the original NTSC-U executable (%s)' % (h, EXPECTED))
