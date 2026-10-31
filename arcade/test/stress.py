"""Stress test of the spf2enh set: random play (scripted at the select
screens) through select, matches, WINNER, CONTINUE, challengers, Arcade runs.
Checked at every match start: the Versus stage selector (fixed stages,
RANDOM never twice, NORMAL = a player's stage), the castle shown exactly when
expected (all 144 band cells, its palettes), the stage music, in a
one-player game the CPU's stage, the round setting; a watchdog for frozen
screens and stuck states. Bugs: line in out/log.txt and out/bugNNN.png.

usage: ZIP=path/spf2enh.zip STATES=dir python3 stress.py START SEED FRAMES OUT
  START: a save state in STATES (START.bin) made from your own build, e.g.
         the Versus select screen or the Arcade select screen, or 'boot'
  env:   ROUNDS=1..3   1P/2P MAX ROUND (1, 3, 5 rounds) set at the start
         NOJOIN=1      player 2 never joins (one-player Arcade)
         WIN=1         the CPU loses each round after a while (whole runs)
         PICK=7,4      player 1's moves at the select screen (RIGHT, UP:
                       Zangief from the Arcade select's start position)
Random play can keep a round alive for a long time: after 30000 frames one
side's drop column is filled so that it ends."""
from stress_common import *
start=sys.argv[1]; seed=int(sys.argv[2]); frames=int(sys.argv[3]); out=sys.argv[4]
os.makedirs(out,exist_ok=True)
random.seed(seed)
e=cps2emu.Emu(ZIP); e.run(2)
if start!='boot': e.load_state(os.path.join(os.environ['STATES'],'%s.bin'%start))
e.w16(0xFF80AE,seed&0xFFFF)
WIN=int(os.environ.get('WIN','0'))  # one-player: the CPU loses each round after a while
NOJOIN=int(os.environ.get('NOJOIN','0'))  # P2 never joins: one-player Arcade
ROUNDS=int(os.environ.get('ROUNDS','0'))     # 1P/2P MAX ROUND setting (1: 1, 2: 3, 3: 5 rounds)
if ROUNDS: e.w8(0xFF80A2,ROUNDS); e.w8(0xFF80A3,ROUNDS)
e.watch(0x618001,0x61800F,2)
log=open(os.path.join(out,'log.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); log.write(s+'\n'); log.flush()
bugs=0; f=0
def BUG(msg):
    global bugs; bugs+=1; P('BUG',f,msg); print('BUG',start,seed,f,msg); shot(e,os.path.join(out,'bug%03d.png'%bugs))
OBJ=(0xFF8B00,0xFF8C00)
prevA8=None; prevshotA4=None; nshots=0; scripts=[None,None]; prevA4=None; newm=False; ids=[]; pending=None; last_random=None
matches=0; stats={}; hashes=[]; last_change=0; prevkey=None
for f in range(frames):
    A4=e.r16(0xFF8004); E0=e.r8(0xFF80E0); AC=e.r8(0xFF80AC)
    for p in (0,1):
        o=OBJ[p]
        choosing = A4==2 and e.r8(o)==1 and e.r8(o+4)==0
        if choosing:
            if scripts[p] is None:
                sc=[]
                if p==0 and E0 and random.random()<0.3: e.w8(0xFF3000,1)   # more NORMAL matches
                elif p==0 and E0 and random.random()<0.7: sc+=[lr.START]*random.randint(1,14)
                sc+=[random.choice([lr.LEFT,lr.RIGHT,lr.UP,lr.DOWN]) for _ in range(random.randint(0,6))]
                if random.random()<0.7: sc+=[lr.UP]*3+[random.choice([lr.LEFT,lr.RIGHT])]*random.randint(0,2)
                if p==0 and os.environ.get('PICK'): sc=[int(x) for x in os.environ['PICK'].split(',')]
                sc+=[lr.B]*3
                scripts[p]=(f,sc)
            t0,sc=scripts[p]; k=(f-t0)//10
            e.pad[p]={sc[k]} if k<len(sc) and (f-t0)%10<4 else set()
        else:
            scripts[p]=None
            if NOJOIN and p==1:
                e.pad[1]=set(); continue
            if f%12==p*6:
                pool=[lr.LEFT,lr.RIGHT,lr.DOWN,lr.DOWN,lr.B,lr.A]
                if random.random()<0.03: pool=[lr.START]
                e.pad[p]=set(random.sample(pool,min(2,len(pool)))) if random.random()<0.85 else set()
    e.run(1)
    fr={}
    for h in e.log(): fr[h['addr']]=h['value']
    if 0x618003 in fr and fr.get(0x61800F,1)==0 and fr.get(0x618001,1)==0: ids.append(fr[0x618003])
    A8=e.r16(0xFF8008)
    if (prevA4==2 and A4==4) or (A4==4 and A8==2 and prevA8!=2): newm=True; ids=[]
    prevA8=A8
    prevA4=A4
    if newm and e.r16(0xFF8004)==4 and e.r16(0xFF8008)==4 and e.r16(0xFF800C)==2 and e.r8(0xFF810D)==1 and e.r8(0xFF8B04)==2 and e.r8(0xFF8C04)==2:
        newm=False; matches+=1
        stage=e.r16(0xFF8100); xc=e.r8(0xFF3005); setting=e.r8(0xFF3000)
        c=[char(e,0),char(e,1)]; zb=[zbit(e,0),zbit(e,1)]; cpu=[e.r8(0xFF839E),e.r8(0xFF879E)]
        castle=False
        if stage==20:
            if AC==3: castle=bool(xc)
            else:
                s=0 if cpu[0] else (1 if cpu[1] else None)
                castle = s is not None and c[s]==10 and zb[s]==1
        vis=castle_visible(e)
        why=''
        if AC==3 and E0:      # VS HUMAN: the selector
            if setting==1:
                owners=[s for s in (0,1) if 2*c[s]==stage]
                if not owners: why+=' NORMAL: stage of no player'
                elif stage==20:
                    if castle and not any(zb[s] for s in owners): why+=' castle without Zangief'
                    if not castle and all(zb[s] for s in owners): why+=' Zangief stage not castle'
            elif 2<=setting<=11:
                if stage!=2*(setting-2) or castle: why+=' fixed stage wrong'
            elif setting==12:
                if not castle: why+=' ZANGIEF setting not castle'
            elif setting==0:
                key='C' if castle else stage
                if key==last_random: why+=' RANDOM repeated'
                if stage==20 and not castle: why+=' RANDOM gave Dan stage'
                last_random=key
            else: why+=' setting %d'%setting
        else:
            owners=[s for s in (0,1) if 2*c[s]==stage]
        if AC!=3 and (cpu[0] or cpu[1]):
            cc=c[0] if cpu[0] else c[1]
            if stage!=2*cc and stage!=18: why+=' 1P: stage %d, CPU %d'%(stage,cc)
        if castle and vis<144: why+=' castle not visible (%d)'%vis
        if not castle and vis>0: why+=' castle cells (%d)'%vis
        pal=[e.r16(0x90C800+2*i)&0xFFF for i in range(16)]
        same=sum(a==b for a,b in zip(pal,rom_pal(stage,castle)))
        if (castle and same<16) or same<11:
            why+=' palette 0'
            base=CPAL if castle else 0xA22C0+stage*0x200
            diff=[p for p in range(32) if [e.r16(0x90C800+p*32+2*i)&0xFFF for i in range(16)]!=[w&0xFFF for w in struct.unpack('>16H',PROG[base+p*32:base+p*32+32])]]
            P('pal diff', diff, [hex(x) for x in pal], [hex(x) for x in rom_pal(stage,castle)], 'bright', hex(e.r16(0x90C800)))
        key=('VS' if AC==3 and E0 else ('2P' if AC==3 else '1P'), 'C' if castle else stage, tuple(zb))
        stats[key[:2]]=stats.get(key[:2],0)+1
        P('match',matches,'f',f,'mode',key[0],'set',setting,'chars',c,'z',zb,'cpu',cpu,'stage',stage,'xc',xc,'castle',int(castle),'vis',vis)
        pending=(f,castle,stage)
        if ROUNDS and (e.r8(0xFF80A2)!=ROUNDS or e.r8(0xFF80A3)!=ROUNDS): why+=' round setting changed'
        if ROUNDS and e.r8(0xFF8121)!=ROUNDS: why+=' match rounds %d'%e.r8(0xFF8121)
        if why: BUG(why)
        if castle and stats[key[:2]]<=3: shot(e,os.path.join(out,'castle_%03d.png'%matches))
    if pending and f-pending[0]==240:
        expect=0x18 if pending[1] else pending[2]//2+1
        if expect not in ids: BUG('music %s expected %x'%([hex(x) for x in ids],expect))
        pending=None
    k=(A4,e.r16(0xFF8008),e.r16(0xFF800C))
    if k!=prevkey: prevkey=k; last_change=f
    if WIN and k==(4,4,2) and f-last_change>900 and f%300==0 and AC!=3:
        b=0xFFAD10 if e.r8(0xFF879E) else 0xFFAB10
        for r in range(13): e.w16(b+r*16+8, 1+(r&1))
    if (A4,A8)!=prevshotA4:
        prevshotA4=(A4,A8)
        if WIN and nshots<400: shot(e,os.path.join(out,'s%04d_%d_%d.png'%(nshots,A4,A8))); nshots+=1
    if k==(4,4,2) and f-last_change>30000 and f%3000==0:
        # a round random play keeps alive: one side's drop column filled (it loses)
        b=random.choice((0xFFAB10,0xFFAD10))
        for r in range(13): e.w16(b+r*16+8, 1+(r&1))
        P('round broken', f)
    if f-last_change>60*400 and k!=(4,4,2): BUG('state %s for 400 s'%(k,)); last_change=f
    if f-last_change>120000: BUG('round never ends (%s)'%(k,)); last_change=f
    if f%600==0:
        hashes.append(fhash(e)); hashes=hashes[-10:]
        if len(hashes)==10 and len(set(hashes))==1: BUG('screen frozen 6000 frames'); hashes=[]
P('done',frames,'matches',matches,'bugs',bugs,'stats',stats)
print('done',start,seed,'matches',matches,'bugs',bugs,stats)
