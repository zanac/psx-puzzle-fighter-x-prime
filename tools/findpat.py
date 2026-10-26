import sys
d=open(sys.argv[1],'rb').read()
def val(o,w):
    return d[o] if w==1 else d[o]|(d[o+1]<<8)
hits=[]
for w in (1,2,4):
  for rowlen in (6,8):
    stride=rowlen*w
    o=0
    while o+stride*12<=len(d):
        ok=True
        for r in range(12):
            for c in range(rowlen):
                v=val(o+r*stride+c*w,w)
                if c<6:
                    if not 1<=v<=4: ok=False;break
                else:
                    if v!=0: ok=False;break
            if not ok: break
        if ok:
            hits.append((o,w,rowlen)); o+=stride*12
        else: o+=w
for o,w,rl in hits:
    print(hex(o),'w',w,'rowlen',rl)
