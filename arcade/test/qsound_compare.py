"""usage: qsound_compare.py A.npy B.npy: level, and envelope correlation and lag per 3 s window"""
import numpy as np,sys
a=np.load(sys.argv[1]).mean(1); b=np.load(sys.argv[2]).mean(1)
print('rms',int(np.sqrt((a**2).mean())),int(np.sqrt((b**2).mean())),'peak',int(abs(a).max()),int(abs(b).max()))
def env(x): 
    x=np.abs(x[:len(x)//480*480]).reshape(-1,480).mean(1); return (x-x.mean())/(x.std()+1e-9)
ea,eb=env(a),env(b)
for s in range(0,min(len(ea),len(eb))-300,300):
    best=max(range(-50,50),key=lambda k: np.corrcoef(ea[s:s+300],eb[s+k:s+k+300])[0,1] if 0<=s+k and s+k+300<=len(eb) else -9)
    print(s/100,'s lag',best*10,'ms', round(np.corrcoef(ea[s:s+300],eb[s+best:s+best+300])[0,1],2), 'rms', int(np.sqrt((a[s*480:(s+300)*480]**2).mean())), int(np.sqrt((b[s*480:(s+300)*480]**2).mean())))
