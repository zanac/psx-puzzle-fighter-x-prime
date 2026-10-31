"""Record a song from PF (sgemf) or SPF2T X" (spf2enh) in the debug core, for
docs/QSOUND.md's comparison. Run from a folder holding sgemf.zip and
spf2enh.zip, with LR_CORE etc. set (arcade/debug/README.md).

usage: qsound_record.py pf|spf TRACK OUT.npy [FRAMES]   (TRACK -1 = all tracks;
       otherwise track 0 + TRACK only). The match states and song numbers below
       are this project's (PF song 7 -> SPF2T song 24)."""
import sys,os,zipfile,struct,wave,io; sys.path.insert(0,'/home/claude/psx-puzzle-fighter-x-prime/tools'); import cps2emu, lr
import numpy as np
PF_SEQ=0x1100e; SPF_SEQ=0x24B00
def mkzip(src,dst,names,hdr,keep):
    zi=zipfile.ZipFile(src); zo=zipfile.ZipFile(dst,'w')
    z80=bytearray(zi.read(names[0])+zi.read(names[1]))
    for j in range(16):
        if j!=keep: struct.pack_into('>H',z80,hdr+1+2*j,0)
    for i in zi.infolist():
        b=zi.read(i.filename)
        if i.filename==names[0]: b=bytes(z80[:0x20000])
        if i.filename==names[1]: b=bytes(z80[0x20000:])
        zo.writestr(i.filename,b)
    zo.close()
def rec(zipf,state,qbase,qidx,song,frames):
    e=cps2emu.Emu(os.path.abspath(zipf))
    e.run(2); e.load_state(state); e.run(2)
    def send(d1,d2=0):
        i=e.r16(qidx); a=qbase+i; e.w32(a,d1); e.w32(a+4,d2); e.w32(a+8,0); e.w16(qidx,(i+16)&0xff0)
    send(0xff05); e.run(30); send(song,0x1000); e.run(4)
    e.capture_audio=True
    for _ in range(frames):
        e.w16(qidx, e.r16(qidx+2))          # the game's own commands are dropped
        e.run(1)
    e.capture_audio=False
    a=np.frombuffer(bytes(e.audio),np.int16).reshape(-1,2).astype(float)
    e.close() if hasattr(e,'close') else None
    return a
if __name__=='__main__':
    which,track,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
    frames=int(sys.argv[4]) if len(sys.argv)>4 else 900
    if which=='pf':
        z='/tmp/solo/sgemf.zip'; mkzip('sgemf.zip',z,('pcf.01','pcf.02'),PF_SEQ,track) if track>=0 else None
        a=rec(z if track>=0 else 'sgemf.zip','/home/claude/work/arc/st_pfmatch.bin',0xffe230,0xfff230,7,frames)
    else:
        z='/tmp/solo/spf2enh.zip'; mkzip('spf2enh.zip',z,('pzfen.01','pzfen.02'),SPF_SEQ,track) if track>=0 else None
        a=rec(z if track>=0 else 'spf2enh.zip','/home/claude/work/arc/st_zdmatch2.bin',0xffc7a0,0xffd7a0,24,frames)
    np.save(out,a)
