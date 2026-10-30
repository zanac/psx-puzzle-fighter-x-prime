import sys,random,struct,json; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from nav import *
from model import xprime
"""End-to-end regression: title, select (secret cycle), damage fuzz against
model.py, match end + RESULT, Arcade with Devilot (P1 wins every match: it
must reach 4 different opponents, arcade_ok), Arcade as Zangief on HARD
(Felicia 8th, then Dan and the bosses: arcade_z_ok; his staff roll figure:
staff_z_ok; he joins the HARD finale: hard_z_ok), Street
Puzzle, demo.

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
# Arcade progress: P1 wins every match (garbage forced on P2); the run must
# get through several opponents (catches hangs between Arcade matches)
opp=[]
for k in range(200):
    for f in range(60): e.w16(0x801ae500+0x22a,250); e.run(1)
    e.press(lr.CROSS,4,4)
    if k==20: sh('arcade_next')
    c=e.r8(0x801ae814)
    if e.r8(0x8019c40f)==1 and (not opp or opp[-1]!=c): opp.append(c)
    if len(opp)>=4: break
sh('arcade_late')
R['arcade_opponents']=opp
R['arcade_ok']=len(opp)>=4
# Arcade as Zangief (Down x7 from Ryu: ... Anita, Zangief): a whole run.
# Felicia must be Zangief's 8th opponent, before
# Dan (10) and the bosses; the run must reach the ending (staff roll).
e.load_state(P_('st_menu.state'))
e.press(lr.CROSS,6,200); e.press(lr.RIGHT,4,30); e.press(lr.CROSS,6,200)   # level HARD
R['arcade_z_level']=e.r8(0x801baacf)
for i in range(7): e.press(lr.DOWN,4,20)
R['arcade_z_sel']=e.r8(0x801baac4)
e.press(lr.CROSS,6,30)
opp=[]; zp1=False
for k in range(260):
    for f in range(60): e.w16(0x801ae500+0x22a,250); e.run(1)
    e.press(lr.CROSS,4,4)
    c=e.r8(0x801ae814)
    if e.r8(0x8019c40f)==1:
        zp1 = zp1 or e.r8(0x801ae568)==10
        if not opp or opp[-1]!=c: opp.append(c)
    if 9 in opp and len(opp)>=10: break
sh('arcade_zangief')
R['arcade_z_opponents']=opp
R['arcade_z_ok']=zp1 and len(opp)>=10 and opp[7]==6 and opp[8]==10
# then his ending: the staff roll figure from his block (children with
# graphics at 0x800A1000, records at +0x300), and on HARD the finale's 13th
# object (index 12) drawn from his own file (graphics 0x80070000)
staff=fin=False
for k in range(240):
    for f in range(60): e.w16(0x801ae500+0x22a,250); e.run(1)
    if k%4==0: e.press(lr.CROSS,4,4)
    for i in range(33):
        a=0x801b5c64+i*0x1c
        if e.r8(a) and e.r32(a+0x10)==0x800a1000 and e.r32(a+0x14)==0x800a1300:
            if not staff: sh('staff_zangief')
            staff=True
    for i in range(20):
        a=0x801be068+i*0x70
        if e.r8(a) and e.r8(a+2)==0x41 and e.r8(a+3)==12 and e.r32(a+0x4c)==0x80070000:
            if not fin:
                e.run(660); sh('hard_finale')   # he comes last, after ~5 s
            fin=True
    if fin: break
R['staff_z_ok']=staff; R['hard_z_ok']=fin
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
