#!/usr/bin/env python3
"""Tiny headless libretro frontend for scripted PSX experiments.

Uses the instrumented pcsx_rearmed core (xdbg_* exports) for
watchpoints / breakpoints / coverage.
"""
import ctypes as C
import os, struct

CORE = os.environ.get('LR_CORE', os.path.join(os.path.dirname(__file__), '..', 'emu', 'pcsx_rearmed', 'pcsx_rearmed_libretro.so'))
SYSDIR = os.environ.get('LR_SYS', os.path.join(os.path.dirname(__file__), '..', 'work', 'system'))

# joypad ids
B, Y, SELECT, START, UP, DOWN, LEFT, RIGHT, A, X, L, R, L2, R2, L3, R3 = range(16)
# PSX names
CROSS, CIRCLE, SQUARE, TRIANGLE = B, A, Y, X

ENV_GET_VARIABLE = 15
ENV_SET_PIXEL_FORMAT = 10
ENV_GET_SYSTEM_DIRECTORY = 9
ENV_GET_SAVE_DIRECTORY = 31
ENV_GET_VARIABLE_UPDATE = 17
ENV_GET_LOG_INTERFACE = 27
ENV_GET_CAN_DUPE = 3

class retro_game_info(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]

class retro_variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]

class retro_system_av_info(C.Structure):
    _fields_ = [('base_width', C.c_uint), ('base_height', C.c_uint), ('max_width', C.c_uint),
                ('max_height', C.c_uint), ('aspect', C.c_float), ('fps', C.c_double), ('rate', C.c_double)]

class xdbg_entry(C.Structure):
    _fields_ = [('kind', C.c_uint32), ('pc', C.c_uint32), ('ra', C.c_uint32), ('addr', C.c_uint32),
                ('value', C.c_uint32), ('size', C.c_uint32), ('frame', C.c_uint32),
                ('gpr', C.c_uint32 * 32)]

ENV_CB = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO_CB = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIOB_CB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL_CB = C.CFUNCTYPE(None)
STATE_CB = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
LOG_CB = C.CFUNCTYPE(None, C.c_int, C.c_char_p)

REGN = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
        's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']

class Emu:
    def __init__(self, game, options=None, verbose=False):
        os.makedirs(SYSDIR, exist_ok=True)
        self.lib = C.CDLL(CORE)
        self.opts = {
            'pcsx_rearmed_drc': 'disabled',
            'pcsx_rearmed_bios': 'HLE',
            'pcsx_rearmed_show_bios_bootlogo': 'disabled',
            'pcsx_rearmed_frameskip_type': 'disabled',
            'pcsx_rearmed_spu_thread': 'disabled',
            'pcsx_rearmed_gpu_thread_rendering': 'disabled',
        }
        if options:
            self.opts.update(options)
        self._keep = []
        self.verbose = verbose
        self.pad = [set(), set()]
        self.frame = None
        self.fmt = 0  # 0 = 0RGB1555, 1 = XRGB8888, 2 = RGB565
        self.frames = 0
        self._sysdir = C.c_char_p(SYSDIR.encode())

        self._env = ENV_CB(self._env_cb)
        self._video = VIDEO_CB(self._video_cb)
        self._audio = AUDIO_CB(lambda l, r: None)
        self.audio = bytearray()
        self.capture_audio = False
        self._audiob = AUDIOB_CB(self._audio_cb)
        self._poll = POLL_CB(lambda: None)
        self._state = STATE_CB(self._state_cb)
        self._logf = LOG_CB(lambda lvl, fmt: print('[core]', fmt.decode(errors='replace').rstrip()) if (verbose or lvl >= 2) else None)
        L = self.lib
        L.retro_set_environment(self._env)
        L.retro_set_video_refresh(self._video)
        L.retro_set_audio_sample(self._audio)
        L.retro_set_audio_sample_batch(self._audiob)
        L.retro_set_input_poll(self._poll)
        L.retro_set_input_state(self._state)
        L.retro_init()
        info = retro_game_info(game.encode(), None, 0, None)
        if not L.retro_load_game(C.byref(info)):
            raise RuntimeError('load_game failed')
        L.retro_serialize_size.restype = C.c_size_t
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_size.restype = C.c_size_t
        L.xdbg_log.restype = C.POINTER(xdbg_entry)
        L.xdbg_log_count.restype = C.c_uint32
        L.xdbg_cov_enable.restype = C.POINTER(C.c_uint32)
        L.xdbg_regs.restype = C.POINTER(C.c_uint32)
        L.xdbg_pc.restype = C.c_uint32
        L.xdbg_snap.restype = C.POINTER(C.c_uint8)
        self._snaplen = 0
        self.ram_ptr = L.retro_get_memory_data(2)
        self.ram_size = L.retro_get_memory_size(2)

    # ---- callbacks ----
    def _env_cb(self, cmd, data):
        cmd &= 0xffff
        if cmd == ENV_GET_VARIABLE:
            v = C.cast(data, C.POINTER(retro_variable)).contents
            key = v.key.decode()
            if key in self.opts:
                s = C.c_char_p(self.opts[key].encode())
                self._keep.append(s)
                v.value = s
                return True
            return False
        if cmd == ENV_SET_PIXEL_FORMAT:
            self.fmt = C.cast(data, C.POINTER(C.c_int)).contents.value
            return True
        if cmd in (ENV_GET_SYSTEM_DIRECTORY, ENV_GET_SAVE_DIRECTORY):
            C.cast(data, C.POINTER(C.c_char_p))[0] = self._sysdir.value
            return True
        if cmd == ENV_GET_VARIABLE_UPDATE:
            C.cast(data, C.POINTER(C.c_bool))[0] = False
            return True
        if cmd == ENV_GET_LOG_INTERFACE:
            C.cast(data, C.POINTER(C.c_void_p))[0] = C.cast(self._logf, C.c_void_p).value
            return True
        if cmd == ENV_GET_CAN_DUPE:
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        return False

    def _audio_cb(self, data, frames):
        if self.capture_audio and data:
            self.audio += C.string_at(data, frames * 4)   # stereo int16
        return frames

    def _video_cb(self, data, w, h, pitch):
        if data:
            self.frame = (C.string_at(data, pitch * h), w, h, pitch)

    def _state_cb(self, port, device, index, id):
        if port < 2 and device == 1:
            return 1 if id in self.pad[port] else 0
        return 0

    # ---- control ----
    def run(self, n=1):
        for _ in range(n):
            self.lib.xdbg_set_frame(self.frames)
            self.lib.retro_run()
            self.frames += 1

    def press(self, buttons, hold=3, release=3, port=0):
        if isinstance(buttons, int):
            buttons = [buttons]
        self.pad[port] = set(buttons)
        self.run(hold)
        self.pad[port] = set()
        self.run(release)

    def hold(self, buttons, port=0):
        self.pad[port] = set([buttons] if isinstance(buttons, int) else buttons)

    def release(self, port=0):
        self.pad[port] = set()

    # ---- memory ----
    def ram(self):
        return C.string_at(self.ram_ptr, self.ram_size)

    def _a(self, addr):
        return addr & 0x1fffff

    def r8(self, a):
        return C.cast(self.ram_ptr + self._a(a), C.POINTER(C.c_uint8))[0]

    def r16(self, a):
        return C.cast(self.ram_ptr + self._a(a), C.POINTER(C.c_uint16))[0]

    def r32(self, a):
        return C.cast(self.ram_ptr + self._a(a), C.POINTER(C.c_uint32))[0]

    def w8(self, a, v):
        C.cast(self.ram_ptr + self._a(a), C.POINTER(C.c_uint8))[0] = v

    def w16(self, a, v):
        C.cast(self.ram_ptr + self._a(a), C.POINTER(C.c_uint16))[0] = v

    def w32(self, a, v):
        C.cast(self.ram_ptr + self._a(a), C.POINTER(C.c_uint32))[0] = v

    def wbytes(self, a, b):
        C.memmove(self.ram_ptr + self._a(a), b, len(b))

    def rbytes(self, a, n):
        return C.string_at(self.ram_ptr + self._a(a), n)

    def vram(self):
        """Raw VRAM, 1024x512 halfwords (needs the patched core's xdbg_vram)."""
        self.lib.xdbg_vram.restype = C.c_void_p
        return C.string_at(self.lib.xdbg_vram(), 1024 * 512 * 2)

    # ---- states ----
    def save_state(self, path=None):
        n = self.lib.retro_serialize_size()
        buf = C.create_string_buffer(n)
        assert self.lib.retro_serialize(buf, C.c_size_t(n))
        if path:
            open(path, 'wb').write(buf.raw)
        return buf.raw

    def load_state(self, src):
        data = open(src, 'rb').read() if isinstance(src, str) else src
        buf = C.create_string_buffer(data, len(data))
        assert self.lib.retro_unserialize(buf, C.c_size_t(len(data)))

    # ---- screenshot ----
    def shot(self, path):
        from PIL import Image
        data, w, h, pitch = self.frame
        if self.fmt == 1:
            img = Image.frombuffer('RGBX', (w, h), data, 'raw', 'BGRX', pitch, 1).convert('RGB')
        else:
            img = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGR;16', pitch, 1)
        img.save(path)
        return path

    # ---- debug ----
    def dbg(self, on=True):
        self.lib.xdbg_set_active(1 if on else 0)

    def watch(self, lo, hi, kind=1):
        return self.lib.xdbg_add_watch(C.c_uint32(lo), C.c_uint32(hi), C.c_uint32(kind))

    def snap(self, addr, n):
        """Capture n bytes at addr whenever a breakpoint hits (max 4 ranges, 4 KiB)."""
        self._snaplen += n
        return self.lib.xdbg_add_snap(C.c_uint32(addr), C.c_uint32(n))

    def bp(self, pc):
        return self.lib.xdbg_add_bp(C.c_uint32(pc))

    def dbg_clear(self):
        self._snaplen = 0
        self.lib.xdbg_clear()

    def log(self, clear=True):
        n = self.lib.xdbg_log_count()
        p = self.lib.xdbg_log()
        out = []
        for i in range(n):
            e = p[i]
            ent = dict(kind=e.kind, pc=e.pc, ra=e.ra, addr=e.addr, value=e.value,
                       size=e.size, frame=e.frame, gpr=list(e.gpr))
            if e.kind == 3 and self._snaplen:
                ent['snap'] = C.string_at(self.lib.xdbg_snap(e.size), self._snaplen)
            out.append(ent)
        if clear:
            self.lib.xdbg_clear_log()
        return out

    def cov_start(self, lo=0x80100000, hi=0x8018e000):
        self._cov = (lo, hi, self.lib.xdbg_cov_enable(C.c_uint32(lo), C.c_uint32(hi)))

    def cov_read(self):
        lo, hi, p = self._cov
        n = (hi - lo) // 4
        arr = (C.c_uint32 * n).from_address(C.addressof(p.contents))
        return {lo + i * 4: arr[i] for i in range(n) if arr[i]}

    def cov_stop(self):
        self.lib.xdbg_cov_disable()

def fmt_regs(g):
    return ' '.join('%s=%x' % (REGN[i], g[i]) for i in range(1, 32) if i not in (26, 27))
