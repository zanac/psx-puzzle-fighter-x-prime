import sys,os,random,struct,hashlib,zipfile
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','tools')); import cps2emu, lr
from PIL import Image
ZIP=os.path.abspath(os.environ['ZIP'])          # the built set (file name spf2enh.zip)
def swap(b): return bytes(x for i in range(0,len(b),2) for x in (b[i+1],b[i]))
z=zipfile.ZipFile(ZIP); PROG=swap(z.read('pzfen.03'))+swap(z.read('pzfen.04'))
CPAL=0xB2E00
def rom_pal(stage, castle):
    a = CPAL if castle else 0xA22C0+stage*0x200
    return [w&0xFFF for w in struct.unpack('>16H',PROG[a:a+32])]
def s2cell(e,row,col):
    i=(row&0xf)|((col&0x3f)<<4)|((row&0x30)<<6)
    return e.r16(0x904000+4*i), e.r16(0x904000+4*i+2)
def castle_visible(e):
    # band cells of the match view (map rows 53-58, cols 32-55): new tiles >= 0x8000
    n=sum(1 for r in range(53,59) for c in range(32,56) if s2cell(e,r,c)[0]>=0x8000)
    return n
def shot(e,path):
    d,w,h,p=e.frame
    Image.frombuffer('RGBX',(w,h),d,'raw','BGRX',p,1).convert('RGB').save(path)
def fhash(e):
    d,w,h,p=e.frame; return hashlib.md5(bytes(d)).hexdigest()
def zbit(e,side): return (e.r8(0xFF3010)>>side)&1
def char(e,side): return e.r8(0xFF8382 if side==0 else 0xFF8782)
