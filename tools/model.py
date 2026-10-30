# Python model of the arcade X' damage formula (KScl code_03.patch.s)
TH=[90,120,150,180,210,240,270,2970]
NUM=[10,11,12,13,14,15,16,17]
RECV=[20,20,20,20,20,20,20,20,20,24,22,18,20,20,20,20]   # 11 = Zangief (PSX)
SEND=[20,24,20,20,20,20,20,20,17,20,22,18,20,20,20,20]   # 11 = Zangief (PSX)
LVL=[8,10,13,15,15,15,15,15]
def mf(x,n,d):
    if n==d: return x
    if x<0: return 0
    return (x//d)*n
def xprime(score,time,mychar,oppchar,diamond,level):
    i=0
    while TH[i] < time+15: i+=1
    x=mf(score,NUM[i],10)
    x=mf(x,RECV[oppchar],20)
    x=mf(x,SEND[mychar],20)
    if diamond: x=mf(x,8,10)
    x=mf(x,LVL[level&7],10)
    return mf(x,1,100)
