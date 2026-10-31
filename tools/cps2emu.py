"""lr.Emu for the arcade set: mame2003-plus built with src/mame2003/xdbg68k.c
(see arcade/README-debug.md). Memory is the 68000's address space, words big endian."""
import ctypes as C, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lr

class Hit(C.Structure):
    _fields_ = [('kind', C.c_uint32), ('pc', C.c_uint32), ('frame', C.c_uint32), ('addr', C.c_uint32),
                ('value', C.c_uint32), ('size', C.c_uint32), ('d', C.c_uint32 * 8), ('a', C.c_uint32 * 8)]

# CPS2 inputs through the RetroPad (mame2003-plus defaults)
COIN, START = lr.SELECT, lr.START
SHOT1, SHOT2 = lr.B, lr.A

class Emu(lr.Emu):
    OPTS = {'mame2003-plus_brightness': '1.0', 'mame2003-plus_gamma': '1.0',
            'mame2003-plus_skip_disclaimer': 'enabled', 'mame2003-plus_skip_warnings': 'enabled',
            'mame2003-plus_frameskip': '0', 'mame2003-plus_sample_rate': '48000',
            'mame2003-plus_autosave_hiscore': 'disabled', 'mame2003-plus_cpu_clock_scale': 'default'}

    def __init__(self, game, options=None, verbose=False):
        o = dict(self.OPTS); o.update(options or {})
        lr.Emu.__init__(self, game, o, verbose)
        L = self.lib
        L.xdbg_hit.restype = C.POINTER(Hit)
        self.ram_ptr = None

    def r8(self, a): return self.lib.xdbg_r8(C.c_uint32(a))
    def w8(self, a, v): self.lib.xdbg_w8(C.c_uint32(a), C.c_uint32(v & 0xff))
    def r16(self, a): return (self.r8(a) << 8) | self.r8(a + 1)
    def r32(self, a): return (self.r16(a) << 16) | self.r16(a + 2)
    def w16(self, a, v): self.w8(a, v >> 8); self.w8(a + 1, v)
    def w32(self, a, v): self.w16(a, v >> 16); self.w16(a + 2, v)
    def rbytes(self, a, n):
        b = C.create_string_buffer(n); self.lib.xdbg_rbytes(C.c_uint32(a), b, C.c_uint32(n)); return b.raw
    def wbytes(self, a, data):
        for i, x in enumerate(data): self.w8(a + i, x)
    def ram(self): return self.rbytes(0xff0000, 0x10000)
    def bp(self, pc): return self.lib.xdbg_add_bp(C.c_uint32(pc))
    def watch(self, lo, hi, kind=3):
        """kind: 1 reads, 2 writes, 3 both"""
        return self.lib.xdbg_add_watch(C.c_uint32(lo), C.c_uint32(hi), C.c_uint32(kind))
    def dbg(self, on=True): pass
    def dbg_clear(self): self.lib.xdbg_clear()
    def log(self, clear=True):
        out = []
        for i in range(self.lib.xdbg_hits()):
            h = self.lib.xdbg_hit(i)[0]
            out.append(dict(kind=('bp', 'r', 'w')[h.kind], pc=h.pc, frame=h.frame, addr=h.addr, value=h.value,
                            size=h.size, d=list(h.d), a=list(h.a)))
        if clear: self.lib.xdbg_clear_hits()
        return out
