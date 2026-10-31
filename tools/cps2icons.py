"""Select screen icons for the new row (arcade): Zangief and Dan, 48x48 like the
grid's (one scroll2 picture of 4x2 icons, each 3x3 16x16 tiles, one palette each).

- Zangief: Pocket Fighter's select icon (sprite 3x3 at 0x1AA2C, palette 0x198F6),
  without its frame, resized to 48x48.
- Dan: his SPF2T select portrait (sprite frame 0x7FF38, palettes 0xAABC0..),
  face and fist cropped and scaled down.
Both get the grid icons' rounded corners and one 15-colour palette."""
import struct
import numpy as np

ZG_ICON = 0x1AA2C           # PF sprite code of the top-left tile (bank included)
ZG_ICON_PAL = 0x198F6
DAN_PORTRAIT = 0x7FF38      # SPF2T frame (P1 select portrait)
DAN_PALS = {0: 0xAABC0, 1: 0xAABE0, 2: 0xAAC00}
DAN_CROP = (20, 0, 100, 80)  # in the portrait (128x112), then to 48x48
CORNER = 5                   # radius of the rounded corners

def rgb_of(words):
    return np.array([[((w >> 8) & 15) * 17, ((w >> 4) & 15) * 17, (w & 15) * 17] for w in words], np.uint8)

def corner_mask():
    m = np.ones((48, 48), bool)
    r = CORNER
    for y in range(r):
        for x in range(r):
            if (r - x - 0.5) ** 2 + (r - y - 0.5) ** 2 > r * r:
                for yy, xx in ((y, x), (y, 47 - x), (47 - y, x), (47 - y, 47 - x)):
                    m[yy, xx] = False
    return m

def quantise(rgb, mask):
    from PIL import Image
    px = rgb[mask]
    q = Image.fromarray(px.reshape(1, -1, 3), 'RGB').quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[:45], np.int32).reshape(-1, 3)
    if len(pal) < 15: pal = np.concatenate([pal, np.zeros((15 - len(pal), 3), np.int32)])
    idx = np.full(mask.shape, 15, np.uint8)
    c = rgb[mask].astype(np.int32)
    idx[mask] = ((c[:, None, :] - pal[None]) ** 2).sum(-1).argmin(1)
    words = [0xF000 | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4) for r, g, b in pal.tolist()] + [0xF000]
    return idx, words

def zangief(pfgfx, pfprog):
    from PIL import Image
    im = np.zeros((48, 48), np.uint8)
    for by in range(3):
        for bx in range(3):
            im[by * 16:by * 16 + 16, bx * 16:bx * 16 + 16] = pfgfx.tile(ZG_ICON + bx + by * 16)
    pal = rgb_of(struct.unpack('>16H', pfprog[ZG_ICON_PAL:ZG_ICON_PAL + 32]))
    inner = pal[im[3:45, 3:45]]                          # without PF's frame
    big = np.array(Image.fromarray(inner).resize((48, 48), Image.LANCZOS))
    return quantise(big, corner_mask())

def dan(spfgfx, spfprog):
    import pfarc
    from PIL import Image
    P = pfarc.PF(spfprog, spfgfx, postable=0x2DB1C)
    img, pal = P.render(DAN_PORTRAIT, size=300, ox=100, oy=100)
    ys, xs = np.nonzero(pal >= 0)
    x0, y0 = xs.min(), ys.min()
    out = np.zeros((300, 300, 3), np.uint8)
    for p, a in DAN_PALS.items():
        m = pal == p
        out[m] = rgb_of(struct.unpack('>16H', spfprog[a:a + 32]))[img[m]]
    a, b, c, d = DAN_CROP
    crop = out[y0 + b:y0 + d, x0 + a:x0 + c]
    big = np.array(Image.fromarray(crop).resize((48, 48), Image.LANCZOS))
    return quantise(big, corner_mask())

def tiles_of(idx):
    return [idx[by * 16:by * 16 + 16, bx * 16:bx * 16 + 16].copy() for by in range(3) for bx in range(3)]
