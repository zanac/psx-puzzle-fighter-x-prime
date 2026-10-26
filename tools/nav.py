"""Menu navigation helpers for the emulator tests (tools/regress.py).

The core path comes from LR_CORE (default emu/pcsx_rearmed/...), the BIOS /
save directory from LR_SYS (see lr.py).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lr

def emu(image, state=None):
    e = lr.Emu(image)
    if state:
        e.load_state(state)
    return e

def boot_to_charsel(e):
    """Boot -> title -> main menu -> Versus -> both players on the select screen."""
    e.run(1200)
    e.press(lr.START, 4, 120); e.press(lr.START, 4, 120)
    e.press(lr.DOWN, 8, 30); e.press(lr.DOWN, 8, 30)
    e.press(lr.CROSS, 6, 200)
    e.press(lr.START, 6, 100, port=1); e.run(200)

def charsel_to_match(e, button=lr.CROSS):
    e.press(button, 6, 30, port=0); e.press(button, 6, 30, port=1)
    for _ in range(6):
        e.run(120); e.press(button, 6, 10, port=0); e.press(button, 6, 10, port=1)

def grid(e, paths, out):
    from PIL import Image
    ims = [Image.open(p) for p in paths]
    n = len(ims); cols = min(4, n); rows = (n + cols - 1) // cols
    W = Image.new('RGB', (320 * cols, 240 * rows))
    for i, im in enumerate(ims):
        W.paste(im.resize((320, 240)), ((i % cols) * 320, (i // cols) * 240))
    W.save(out)
