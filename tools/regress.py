import sys,random,struct,json; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from nav import *
from model import xprime
"""End-to-end regression: title, select (secret cycle), damage fuzz against
model.py, match end + RESULT, Arcade with Devilot, Street Puzzle, demo.

usage: regress.py IMAGE.(pbp|cue) OUTDIR
Writes screenshots, savestates and result.json into OUTDIR."""
import os
img=sys.argv[1]; OUT=sys.argv[2]; os.makedirs(OUT, exist_ok=True)
out=os.path.join(OUT,'result.json')
def P_(n): return os.path.join(OUT,n)
e=lr.Emu(img)
P=[]; R={}
def sh(n): p=P_('rg_%s.png'%n); e.shot(p); P.append(p)
e.run(1200); e.press(lr.START,4,120); sh('title')
e.press(lr.START,4,120); e.save_state(P_('st_menu.state'))
e.press(lr.DOWN,8,30); e.press(lr.DOWN,8,30); e.press(lr.CROSS,6,200); e.press(lr.START,6,100,port=1); e.run(200)
e.save_state(P_('st_sel.state'))
for i in range(5): e.press(lr.DOWN,4,30)              # P1 Ryu->Morrigan->...->Mei-Ling
for i in range(6): e.press(lr.DOWN,4,30,port=1)      # P2 Ken->Felicia->...->Anita
R['sel']=(e.r8(0x801baac4),e.r8(0x801baac8),e.r8(0x801ae4d8),e.r8(0x801ae4d9))
sh('select')
charsel_to_match(e); e.run(30); sh('match')
# damage fuzz
e.dbg(); e.snap(0x801ae500,0x2ac*2); e.snap(0x8019c400,0x20); e.bp(0x80134d80); e.bp(0x80134f58)   # entry; vanilla tail with a3 = damage
random.seed(9); n=ok=0; pend=None
for step in range(30000):
    if step%20==0:
        for p in (0x801ae500,0x801ae7ac):
            e.w16(p+0x1f0, random.choice([0,60,74,75,76,105,135,165,195,225,255,256,600]))
            e.w8(p+0x23f, random.random()<0.4); e.w8(p+0x22a,0)
        e.w8(0x8019c405, random.randrange(4))
    for port in (0,1): e.pad[port]={random.choice([lr.LEFT,lr.RIGHT,lr.CROSS,lr.CIRCLE,lr.DOWN])}
    e.run(3); e.pad=[set(),set()]; e.run(3)
    for x in e.log():
        if x['pc']==0x80134d80:
            s=x['snap']; o=x['gpr'][4]-0x801ae500
            h=lambda off: struct.unpack_from('<h',s,o+off)[0]
            opp=struct.unpack_from('<I',s,o+0x84)[0]-0x801ae500
            pend=xprime(sum(h(0x10c+2*k) for k in range(7)),h(0x1f0),s[o+0x68],s[opp+0x68],s[o+0x23f],s[0x2ac*2+5])
        elif pend is not None:
            n+=1; ok+= x['gpr'][7]==pend; pend=None
    if n>=150: break
e.dbg(False); e.dbg_clear()
R['damage']=(n,ok)
sh('match_late')
for k in range(40):
    for f in range(60): e.w16(0x801ae500+0x22a,250); e.run(1)
    if k%3==2: e.press(lr.CROSS,4,4); e.press(lr.CROSS,4,4,port=1)
    if k==25: sh('match_end')
for k in range(3): e.run(90); e.press(lr.CROSS,4,20)
sh('result')
for k in range(2): e.run(90); e.press(lr.CROSS,4,20)
sh('back_select')
# arcade with Devilot
e.load_state(P_('st_menu.state'))
e.press(lr.CROSS,6,200); e.press(lr.CROSS,6,200)
e.press(lr.DOWN,4,30); e.press(lr.DOWN,4,30); e.press(lr.CROSS,6,30)
for i in range(6): e.run(120); e.press(lr.CROSS,4,4)
sh('arcade'); R['arcade_char']=e.r8(0x801ae568)
for k in range(30):
    for f in range(60): e.w16(0x801ae500+0x22a,250); e.run(1)
    e.press(lr.CROSS,4,4)
    if k==20: sh('arcade_next')
sh('arcade_late')
# street puzzle
e.load_state(P_('st_menu.state'))
e.press(lr.DOWN,8,30); e.press(lr.CROSS,6,250); e.press(lr.CROSS,6,400); e.run(300); sh('street')
# training demo
e.load_state(P_('st_menu.state'))
for i in range(3): e.press(lr.DOWN,8,25)
e.press(lr.CROSS,6,1200); sh('demo')
json.dump({'R':R,'P':P},open(out,'w'))
grid(e,P[:6],P_('grid1.png')); grid(e,P[6:],P_('grid2.png'))
print(R)
