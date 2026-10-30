import sys, os, subprocess, json, ctypes as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nav import *
"""Memory card round trip of the Versus RESULT counters (Dan and Zangief).

A: on a blank card, Zangief (P1, his icon) beats Dan (P2, his icon) in
   Versus; RESULT; END; BACKUP -> SAVE DATA -> slot 1 -> YES. The card is
   written to OUTDIR/card.bin.
B: a new emulator boots with that card (the game loads it by itself),
   checks that Zangief's win and Dan's loss came back, plays the same
   match again and expects 2 / 2 on RESULT.
The emulator runs the card as pcsx_rearmed's libretro card (lr.py has no
card unless asked). One emulator per process, so B is a second process.

usage: cardtest.py IMAGE.(pbp|cue) OUTDIR      -> OUTDIR/card.json, card_*.png"""
CARD = {'pcsx_rearmed_memcard1': 'libretro', 'pcsx_rearmed_memcard2': 'none'}
ZST = 0x80117E8C          # Zangief's counters (src/result.asm XP_ZST)
STATS = 0x801D2678        # 4 x 11 words; Dan = index 10
img, OUT = sys.argv[1], sys.argv[2]
phase = sys.argv[3] if len(sys.argv) > 3 else 'A'
os.makedirs(OUT, exist_ok=True)
e = lr.Emu(img, options=CARD)
mem = e.lib.retro_get_memory_data(0)
if phase == 'B':
    C.memmove(mem, open(os.path.join(OUT, 'card.bin'), 'rb').read(), 131072)
zst = lambda: [e.r32(ZST + 4 * i) for i in range(4)]
dan = lambda: [e.r32(STATS + o + 40) for o in (0, 0x2C, 0x58, 0x84)]

def boot():                 # with a saved card the game loads it first: longer
    e.run(1200 if phase == 'A' else 1600); e.press(lr.START, 4, 120); e.press(lr.START, 4, 120); e.run(120)

def match():
    e.press(lr.DOWN, 8, 30); e.press(lr.DOWN, 8, 30); e.press(lr.CROSS, 6, 200)
    e.press(lr.START, 6, 100, port=1); e.run(200)
    e.press(lr.RIGHT, 4, 30); e.press(lr.UP, 4, 30)                  # Zangief
    e.press(lr.LEFT, 4, 30, port=1); e.press(lr.UP, 4, 30, port=1)   # Dan
    charsel_to_match(e, lr.CIRCLE)
    e.dbg(True); e.bp(0x80138864); e.log()                           # RESULT
    for k in range(200):
        for f in range(30): e.w16(0x801ae500 + 0x22a, 250); e.run(1)
        if e.log(): break
        if k % 3 == 2: e.press(lr.CROSS, 4, 4); e.press(lr.CROSS, 4, 4, port=1)
    e.dbg(False); e.run(90)

boot()
R = {}
if phase == 'A':
    match(); e.shot(os.path.join(OUT, 'card_result1.png'))
    R['A_after_match'] = (zst(), dan())
    e.press(lr.DOWN, 6, 30); e.press(lr.CROSS, 6, 300)               # END
    for i in range(2): e.press(lr.START, 6, 150)
    e.run(120)
    for i in range(5): e.press(lr.DOWN, 8, 30)                       # BACKUP
    e.press(lr.CROSS, 6, 150); e.press(lr.CROSS, 6, 150)             # SAVE DATA, slot 1
    e.press(lr.CROSS, 6, 150); e.press(lr.UP, 6, 40)                 # SAVE OK? -> YES
    e.press(lr.CROSS, 6, 300); e.shot(os.path.join(OUT, 'card_saved.png')); e.run(300)
    open(os.path.join(OUT, 'card.bin'), 'wb').write(C.string_at(mem, 131072))
    json.dump(R, open(os.path.join(OUT, 'card_A.json'), 'w'))
    del e
    subprocess.run([sys.executable, __file__, img, OUT, 'B'], check=True)
else:
    R = json.load(open(os.path.join(OUT, 'card_A.json')))
    R['B_after_boot'] = (zst(), dan())
    match(); e.shot(os.path.join(OUT, 'card_result2.png'))
    R['B_after_match'] = (zst(), dan())
    R['card_ok'] = (R['A_after_match'] == [[1, 0, 0, 0], [0, 0, 0, 1]] and
                    R['B_after_boot'] == ([1, 0, 0, 0], [0, 0, 0, 1]) and
                    R['B_after_match'] == ([2, 0, 0, 0], [0, 0, 0, 2]))
    json.dump(R, open(os.path.join(OUT, 'card.json'), 'w'))
    print(R)
