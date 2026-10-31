"""Select screen icons for the new row (arcade): Zangief and Dan, 48x48 like the
grid's (one scroll2 picture of 4x2 icons, each 3x3 16x16 tiles, one palette each).

- Zangief: Pocket Fighter's select icon (sprite 3x3 at 0x1AA2C, palette 0x198F6),
  without its frame, resized to 48x48.
- Dan: his SPF2T select portrait (sprite frame 0x7FF38, palettes 0xAABC0..),
  face and fist cropped and scaled down.
Like the grid's, the pictures fill only the blue inside of the panel under
them (scroll1 tiles 0x780-0x788, 6x6 8x8 tiles, drawn by code_select.s):
42x42 pixels at (3, 3), transparent where the panel is not blue. One
15-colour palette each."""
import struct
import numpy as np

ZG_ICON = 0x1AA2C           # PF sprite code of the top-left tile (bank included)
ZG_ICON_PAL = 0x198F6
DAN_PORTRAIT = 0x7FF38      # SPF2T frame (P1 select portrait)
DAN_PALS = {0: 0xAABC0, 1: 0xAABE0, 2: 0xAAC00}
DAN_CROP = (20, 0, 100, 80)  # in the portrait (128x112), then to 48x48
PANEL = [[0x780, 0x781, 0x781, 0x781, 0x781, 0x782]] + \
        [[0x783, 0x784, 0x784, 0x784, 0x784, 0x785]] * 4 + \
        [[0x786, 0x787, 0x787, 0x787, 0x787, 0x788]]
PANEL_IN = 5                 # the panel's blue pen
IN0, IN = 3, 42              # the inside: 42x42 from (3, 3)

def rgb_of(words):
    return np.array([[((w >> 8) & 15) * 17, ((w >> 4) & 15) * 17, (w & 15) * 17] for w in words], np.uint8)

def panel_mask(spfgfx):
    """48x48: True where the panel is blue (scroll1 8x8 tile c = right half of
    the 16x16 tile c // 2, rows (c % 2) * 8)"""
    P = np.zeros((48, 48), np.uint8)
    for r, row in enumerate(PANEL):
        for c, code in enumerate(row):
            P[r * 8:r * 8 + 8, c * 8:c * 8 + 8] = spfgfx.tile(code // 2)[(code % 2) * 8:(code % 2) * 8 + 8, 8:16]
    return P == PANEL_IN

def place(rgb42, mask):
    out = np.zeros((48, 48, 3), np.uint8)
    out[IN0:IN0 + IN, IN0:IN0 + IN] = rgb42
    return quantise(out, mask)

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

def zangief(pfgfx, pfprog, spfgfx):
    im = np.zeros((48, 48), np.uint8)
    for by in range(3):
        for bx in range(3):
            im[by * 16:by * 16 + 16, bx * 16:bx * 16 + 16] = pfgfx.tile(ZG_ICON + bx + by * 16)
    pal = rgb_of(struct.unpack('>16H', pfprog[ZG_ICON_PAL:ZG_ICON_PAL + 32]))
    return place(pal[im[3:45, 3:45]], panel_mask(spfgfx))   # PF's inside, 1:1

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
    return place(np.array(Image.fromarray(crop).resize((IN, IN), Image.LANCZOS)), panel_mask(spfgfx))

def tiles_of(idx):
    return [idx[by * 16:by * 16 + 16, bx * 16:bx * 16 + 16].copy() for by in range(3) for bx in range(3)]

# --- select portrait (128x112, as SPF2T's) -------------------------------------
ZG_PORTRAIT = 0x1DF92A      # PF select portrait frame (bank 1: codes + 0x10000)
ZG_PORT_PALS = {0: 0x20D008, 1: 0x20D028, 2: 0x20D048}
PORT_W, PORT_H = 128, 112
PORT_SCALE = 0.62

def pf_portrait_rgba(pfgfx, pfprog):
    """Pocket Fighter's select portrait of Zangief (full body), RGBA, cropped"""
    import pfarc
    P = pfarc.PF(pfprog, pfgfx)
    img, pal = P.render(ZG_PORTRAIT, bank=1, size=600, ox=200, oy=200)
    out = np.zeros((600, 600, 4), np.uint8)
    for p, a in ZG_PORT_PALS.items():
        m = pal == p
        out[m, :3] = rgb_of(struct.unpack('>16H', pfprog[a:a + 32]))[img[m]]
        out[m, 3] = 255
    ys, xs = np.nonzero(pal >= 0)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

# --- WINNER screen picture (full body, about as wide as the others (Ryu ~130 pixels)) -------
WIN_SCALE = 0.72
CRED_SCALE = 0.85            # the ending's staff roll (Ryu's picture is ~190 pixels high)

def zangief_winner(pfgfx, pfprog, scale=WIN_SCALE):
    """index image (15 = transparent) and palette words"""
    from PIL import Image
    im = Image.fromarray(pf_portrait_rgba(pfgfx, pfprog), 'RGBA')
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    a = np.array(im)
    return quantise(a[..., :3], a[..., 3] > 128)

def zangief_portrait(pfgfx, pfprog):
    """index image 128x112 (15 = transparent) and its palette words"""
    import pfarc
    from PIL import Image
    P = pfarc.PF(pfprog, pfgfx)
    img, pal = P.render(ZG_PORTRAIT, bank=1, size=340, ox=120, oy=240)
    out = np.zeros((340, 340, 4), np.uint8)
    for p, a in ZG_PORT_PALS.items():
        m = pal == p
        out[m, :3] = rgb_of(struct.unpack('>16H', pfprog[a:a + 32]))[img[m]]
        out[m, 3] = 255
    ys, xs = np.nonzero(pal >= 0)
    out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray(out, 'RGBA')
    im = im.resize((round(im.width * PORT_SCALE), round(im.height * PORT_SCALE)), Image.LANCZOS)
    a = np.array(im)
    x0 = max(0, (a.shape[1] - PORT_W) // 2)
    a = a[:PORT_H, x0:x0 + PORT_W]
    canvas = np.zeros((PORT_H, PORT_W, 4), np.uint8)
    canvas[:a.shape[0], :a.shape[1]] = a
    mask = canvas[..., 3] > 128
    return quantise(canvas[..., :3], mask)
