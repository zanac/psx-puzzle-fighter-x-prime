"""ZANGIEF in the select screen's big name font (sprites, 16 pixels high), from
the other names' letters plus a Z drawn in the same style. The names are frames
of a table at 0x7DB20 (one long each, char + 1: frame; types 0 and 2)."""
import struct
import numpy as np

NAME_TABLE = 0x7DB20
CHAR = {'MORRIGAN': 0, 'KEN': 3, 'FELICIA': 6, 'DAN': 10}
# letter: (name, first column, end column) in the name's picture
GLYPHS = {'A': ('DAN', 16, 32), 'N': ('DAN', 32, 48), 'G': ('MORRIGAN', 59, 71),
          'I': ('FELICIA', 45, 52), 'E': ('KEN', 16, 32), 'F': ('FELICIA', 0, 15)}
Z = ["................",
     ".eeeeeeeeeeeeee.",
     "e02222222222221e",
     "e1222222222222e.",
     ".eeeeeee03331e..",
     "......e04441e...",
     ".....e05551e....",
     "....e06661e.....",
     "...e16666e......",
     "..e36666e.......",
     ".e7777eeeeeeee..",
     "e88888888888881e",
     "e9999999999999be",
     "eaaaaaaaaaaaaace",
     "ecaaaaaaaaaaaace",
     ".eeeeeeeeeeeeee."]
CLEAR = 15                      # transparent pen

def picture(P, ch):
    fr = struct.unpack('>I', P.d[NAME_TABLE + 4 * (ch + 1):NAME_TABLE + 4 * (ch + 2)])[0]
    img, pal = P.render(fr, size=160, ox=80, oy=24)
    ys, xs = np.nonzero(pal >= 0)
    out = np.where(pal >= 0, img, CLEAR).astype(np.uint8)
    return out[16:32, xs.min():xs.max() + 1]

def compose(P, text='ZANGIEF'):
    cols = []
    for ch in text:
        if ch == 'Z':
            g = np.array([[CLEAR if c == '.' else int(c, 16) for c in row] for row in Z], np.uint8)
        else:
            n, a, b = GLYPHS[ch]
            g = picture(P, CHAR[n])[:, a:b]
        if cols:                 # letters share their outline column
            last = cols[-1][:, -1]
            first = g[:, 0]
            m = (last == CLEAR)
            cols[-1][:, -1] = np.where(m, first, last)
            g = g[:, 1:]
        cols.append(g.copy())
    return np.concatenate(cols, 1)
