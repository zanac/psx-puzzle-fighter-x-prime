#!/usr/bin/env python3
"""A rock/metal remix of Pocket Fighter's castle theme (Zangief's stage music),
rendered from the user's own arcade set at build time.

The notes come from Pocket Fighter's arcade sound program (sgemf pcf.01/02,
song 7, QSound driver 1.30, read with tools/qsconv.py); the drums, the bass
and the pad are Pocket Fighter's own QSound samples (pcf.11m/12m); the
guitars are synthesised (Karplus-Strong strings through an overdrive and a
cabinet filter). Nothing of this is in the repository: everything is made
from the user's files when the PSX image is built.

The theme: 20 bars of 4/4 (48 ticks a beat, the loop from tick 108), A minor:
  bars 0-7    i-VI-VII riff (A, F, G) under the melody (track 2)
  bars 8-11   A minor / B flat, no melody
  bars 12-15  the low melody (track 0)
  bars 16-19  a 16th-note run over a chromatic descent
The remix (120 bars at ~160 BPM, 180.05 s: exactly the 3376 XA sectors of the
original, so that it loops the same way):
  intro 4 | theme 20 | theme with harmony and double bass 20 |
  breakdown 12 (bars 8-11 x 3, half time) | solo 20 | theme 20 |
  theme a tone higher 20 | outro 4

usage: remix.py sgemf.zip OUT.wav [--style dance|metal]   (37.8 kHz stereo,
       for tools/xa.py)
Needs numpy and scipy."""
import os, struct, sys, zipfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qsconv as Q

SR = 37800
QS_RATE = 24038                    # QSound's sample rate
TOTAL = 3376 * 2016 / SR           # 180.05 s
BARS = 120
BEAT = TOTAL / (BARS * 4)
LOOP0, TPB = 108, 48               # the theme's first tick, ticks a beat
PF_SONG = 7

# ---------------------------------------------------------------------------
# Pocket Fighter: notes and samples
class PF:
    def __init__(self, z):
        self.z80 = z.read('pcf.01') + z.read('pcf.02')
        q = np.frombuffer(z.read('pcf.11m') + z.read('pcf.12m'), np.int8)
        self.q = q.reshape(-1, 2)[:, ::-1].reshape(-1)          # word swapped
    def u16(self, a): return struct.unpack('<H', self.z80[a:a + 2])[0]
    def track(self, n):
        a = Q.pf_song(self.z80, PF_SONG)
        off = struct.unpack('>H', self.z80[a + 1 + 2 * n:a + 3 + 2 * n])[0]
        ev, end, loop = Q.v1_track(self.z80, a + off)
        return [((t - LOOP0) / TPB, k, l / TPB) for t, k, l in Q.notes_of(ev)
                if LOOP0 <= t < LOOP0 + 80 * TPB]
    def instrument(self, bank, prog):
        a = self.u16(Q.PF_INS + 2 * bank) + 4 * prog
        si, fine = self.u16(a), struct.unpack('b', self.z80[a + 2:a + 3])[0]
        e = self.z80[Q.PF_SAMP + 8 * si:Q.PF_SAMP + 8 * si + 8]
        b = e[0] << 16
        start, loop, end = (struct.unpack('<H', e[i:i + 2])[0] for i in (1, 3, 5))
        data = self.q[b + start:b + end].astype(np.float64) / 128
        looped = loop - start < len(data) - 16
        return dict(data=data, loop=loop - start if looped else None, unity=e[7], fine=fine)

def play_sample(ins, key, dur, gain=1.0, release=0.08):
    """one note of a QSound instrument at SR"""
    step = 2 ** ((key - ins['unity'] + ins['fine'] / 256) / 12) * QS_RATE / SR
    d = ins['data']
    n = int((dur + release) * SR) if ins['loop'] is not None else int(len(d) / step) + 1
    pos = np.arange(n) * step
    if ins['loop'] is not None:
        L = ins['loop']; span = len(d) - L
        over = pos >= len(d) - 1
        pos[over] = L + np.mod(pos[over] - L, span - 1)
    else:
        pos = pos[pos < len(d) - 1]
    i = pos.astype(np.int64); f = pos - i
    out = d[i] * (1 - f) + d[i + 1] * f
    env = np.ones(len(out))
    r = int(release * SR); k = int(dur * SR)
    if ins['loop'] is not None and k < len(out):
        env[k:] = np.linspace(1, 0, len(out) - k)
    a = min(len(out), int(0.002 * SR)); env[:a] *= np.linspace(0, 1, a)
    return out * env * gain

# ---------------------------------------------------------------------------
# synthesised guitar strings (Karplus-Strong), rendered at OS * SR
def ks_note(freq, dur, rng, mute=False, bright=0.5, os_=2, sustain=0.996):
    from scipy.signal import lfilter, resample_poly
    sr = SR * os_
    N = max(2, int(round(sr / freq)))
    n = int((dur + (0.03 if mute else 0.12)) * sr)
    x = np.zeros(n)
    burst = rng.uniform(-1, 1, N)
    # brightness: smooth the pick noise
    k = max(1, int((1 - bright) * 6))
    burst = np.convolve(burst, np.ones(k) / k, 'same')
    x[:N] = burst
    g = (0.90 if mute else sustain)
    y = lfilter([1.0], np.r_[1.0, np.zeros(N - 1), -g / 2, -g / 2], x)
    k = int(dur * sr)
    if k < n:
        y[k:] *= np.linspace(1, 0, n - k)
    return resample_poly(y, 1, os_)

def drive(x, gain, tone_hz=4200):
    from scipy.signal import butter, sosfilt
    hp = butter(2, 120, 'highpass', fs=SR, output='sos')
    y = np.tanh(gain * sosfilt(hp, x))
    y = np.tanh(1.8 * y) / np.tanh(1.8)
    cab = butter(4, tone_hz, 'lowpass', fs=SR, output='sos')
    lo = butter(2, 70, 'highpass', fs=SR, output='sos')
    return sosfilt(lo, sosfilt(cab, y))

# ---------------------------------------------------------------------------
class Bus:
    def __init__(self):
        self.x = np.zeros(int(TOTAL * SR) + SR * 4)
    def add(self, t, sig, gain=1.0):
        i = int(round(t * SR))
        if i >= len(self.x): return
        sig = sig[:len(self.x) - i]
        self.x[i:i + len(sig)] += sig * gain

def pan(x, p):
    """p -1 (left) .. 1 (right), constant power"""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)

# ---------------------------------------------------------------------------
NOTE_PC = {'A': 9, 'A#': 10, 'B': 11, 'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7}
SCALE_A = [9, 11, 0, 2, 4, 5, 7]          # A natural minor

def third_below(k):
    pc = k % 12
    if pc in SCALE_A:
        i = SCALE_A.index(pc); t = SCALE_A[(i - 2) % 7]
        d = (pc - t) % 12
        return k - d
    return k - 3

def roots_of(bass, bars):
    """chord root (pitch class) per beat of the theme, from the bass line"""
    roots = [None] * (bars * 4)
    for b, k, l in bass:
        i = int(b + 1e-6)
        if roots[i] is None: roots[i] = k % 12
    last = 9
    for i in range(len(roots)):
        if roots[i] is None: roots[i] = last
        last = roots[i]
    for bar in (8, 10):
        for j in range(4): roots[bar * 4 + j] = 9
    for bar in (9, 11):
        for j in range(4): roots[bar * 4 + j] = 10
    return roots

def low(pc, lo=40):
    k = lo + ((pc - lo) % 12)
    return k

def hz(k): return 440.0 * 2 ** ((k - 69) / 12)

def build_metal(sgemf, stems=None):
    z = zipfile.ZipFile(sgemf)
    pf = PF(z)
    rng = np.random.default_rng(1997)
    mel = [n for n in pf.track(2)]                 # bars 0-5, 16-19
    lowmel = [n for n in pf.track(0) if 48 <= n[0] < 64]
    bass = pf.track(1)
    pad = pf.track(4)
    roots = roots_of(bass, 20)
    kit = {name: pf.instrument(0, p) for name, p in
           dict(kick=0, kick2=10, snare=1, hat=2, ohat=3, crash=4, ride=5, tomh=7, tomm=8, toml=9).items()}
    ins_bass = pf.instrument(0, 32)
    ins_pad = pf.instrument(0, 62)
    ins_str = pf.instrument(0, 41)

    buses = {n: Bus() for n in ('rhyL', 'rhyR', 'lead', 'harm', 'bass', 'drums', 'pad')}
    # sections: (first bar, kind, bars of the theme, transpose)
    plan = [('intro', 0, 4, 0)]
    bar = 4
    for kind, n, tr in (('theme', 20, 0), ('theme2', 20, 0), ('break', 12, 0), ('solo', 20, 0),
                        ('theme2', 20, 0), ('final', 20, 2), ('outro', 4, 0)):
        plan.append((kind, bar, n, tr)); bar += n
    assert bar == BARS, bar
    T = lambda gbar, beat: (gbar * 4 + beat) * BEAT

    def hit(name, gbar, beat, gain=1.0, key=None):
        ins = kit[name]
        buses['drums'].add(T(gbar, beat), play_sample(ins, key or ins['unity'], 0.5) * gain)

    def chord(side, gbar, beat, root_pc, length, mute, tr, gain=1.0):
        k = low((root_pc + tr) % 12)
        sig = 0
        for j, iv in enumerate((0, 7, 12)):
            s = ks_note(hz(k + iv) * (1 + rng.uniform(-0.002, 0.002)), length * BEAT, rng, mute=mute,
                        bright=0.7 if not mute else 0.35)
            sig = s if j == 0 else (sig[:len(s)] + s[:len(sig)])
        jitter = rng.uniform(0, 0.006)
        buses[side].add(T(gbar, beat) + jitter, sig * gain * (0.55 if mute else 1.0))

    def lead_note(busname, t, k, length, gain=1.0):
        s = ks_note(hz(k), length * BEAT, rng, bright=0.9, os_=4, sustain=0.9995)
        # vibrato-free but sustained: a soft attack reshaping
        buses[busname].add(t, s * gain)

    def drum_bar(gbar, style, bar_in_theme, fill):
        if style == 'gallop':
            for b in range(4):
                hit('kick', gbar, b); hit('kick', gbar, b + 0.5, 0.8)
                hit('hat', gbar, b, 0.5); hit('hat', gbar, b + 0.5, 0.35)
            hit('snare', gbar, 1); hit('snare', gbar, 3)
        elif style == 'double':
            for s in range(16):
                hit('kick', gbar, s / 4, 0.75)
            for b in range(4): hit('ride', gbar, b, 0.35); hit('ride', gbar, b + 0.5, 0.25)
            hit('snare', gbar, 1); hit('snare', gbar, 3)
        elif style == 'half':
            hit('kick2', gbar, 0, 1.1); hit('kick', gbar, 1.5); hit('kick', gbar, 2.75)
            hit('snare', gbar, 2, 1.1)
            for b in range(8): hit('ride', gbar, b / 2, 0.3)
        elif style == 'synco':
            for b in (0, 0.75, 1.5, 2, 2.75):
                hit('kick', gbar, b)
            hit('snare', gbar, 1); hit('snare', gbar, 3)
            for b in range(8): hit('hat', gbar, b / 2, 0.45 if b % 2 == 0 else 0.3)
        elif style == 'blast':
            for s in range(16):
                hit('kick', gbar, s / 4, 0.7)
            for b in range(8): hit('snare', gbar, b / 2, 0.55 if b % 2 else 0.8)
            hit('crash', gbar, 0, 0.7)
        if bar_in_theme % 4 == 0:
            hit('crash', gbar, 0, 0.8)
        if fill:
            for i, (d, b) in enumerate((('snare', 3), ('snare', 3.25), ('tomh', 3.5), ('toml', 3.75))):
                hit(d, gbar, b, 0.8)

    def theme_bar(gbar, tb, kind, tr):
        """one bar of the theme (tb = 0-19) in a section"""
        heavy = kind in ('theme2', 'final', 'solo')
        r = [(roots[tb * 4 + j] + 0) for j in range(4)]
        # drums
        if tb < 8: style = 'double' if heavy else 'gallop'
        elif tb < 12: style = 'half'
        elif tb < 16: style = 'synco'
        else: style = 'blast' if heavy else 'synco'
        drum_bar(gbar, style, tb, tb % 4 == 3)
        # rhythm guitars
        for side in ('rhyL', 'rhyR'):
            for j in range(4):
                if tb < 8:
                    chord(side, gbar, j, r[j], 1.0 if j == 0 else 0.45, j != 0, tr)
                    if j: chord(side, gbar, j + 0.5, r[j], 0.22, True, tr); chord(side, gbar, j + 0.75, r[j], 0.22, True, tr)
                    else: chord(side, gbar, j + 0.75, r[j], 0.22, True, tr)
                elif tb < 12:
                    if j in (0, 2): chord(side, gbar, j, r[j], 2.0 if j == 0 else 1.5, False, tr)
                    if j == 3: chord(side, gbar, 3.5, r[j], 0.22, True, tr); chord(side, gbar, 3.75, r[j], 0.22, True, tr)
                elif tb < 16:
                    for h in (0, 0.5):
                        accent = h == 0 and (j == 0 or r[j] != r[j - 1])
                        chord(side, gbar, j + h, r[j], 0.45 if accent else 0.4, not accent, tr)
                else:
                    for s in range(4):
                        chord(side, gbar, j + s / 4, r[j], 0.24, not (s == 0 and j in (0, 2)), tr)
        # bass: the theme's bass line, doubled an octave down where it is high
        for b, k, l in bass:
            if tb * 4 <= b < tb * 4 + 4:
                kk = k + tr
                while kk > 52: kk -= 12
                buses['bass'].add(T(gbar, b - tb * 4), play_sample(ins_bass, kk, l * BEAT))
        if 8 <= tb < 12:
            for j in (0, 2):
                buses['bass'].add(T(gbar, j), play_sample(ins_bass, low(r[j] + tr, 33), 1.9 * BEAT))
        # lead
        if kind == 'solo':
            line = [(b, k + 12, l) for b, k, l in mel if tb * 4 <= b < tb * 4 + 4]
            if not line and tb < 16 or 6 <= tb < 12:
                # an arpeggio sweep over the chord, 16ths
                line = []
                for j in range(4):
                    pc = r[j]; minor = pc in (9, 2, 4)
                    tones = [0, 3 if minor else 4, 7, 12, 15 if minor else 16, 19, 24]
                    base = 57 + ((pc - 57) % 12)
                    seq = tones[:4] + tones[4:0:-1][:0] if j % 2 == 0 else tones[3:7]
                    for s in range(4):
                        line.append((tb * 4 + j + s / 4, base + seq[s % len(seq)], 0.26))
            if 12 <= tb < 16:
                line = [(b, k + 12, l) for b, k, l in lowmel if tb * 4 <= b < tb * 4 + 4]
        else:
            line = [(b, k, l) for b, k, l in mel if tb * 4 <= b < tb * 4 + 4]
            if 12 <= tb < 16:
                line = [(b, k, l) for b, k, l in lowmel if tb * 4 <= b < tb * 4 + 4]
        for b, k, l in line:
            t = T(gbar, b - tb * 4)
            lead_note('lead', t, k + tr - 12 if kind not in ('solo',) else k + tr - 12, max(0.2, l))
            if kind in ('theme2', 'final'):
                lead_note('harm', t, third_below(k) + tr - 12, max(0.2, l), 0.8)
        # pad in the quiet half-time bars
        if 8 <= tb < 12:
            for b, k, l in pad:
                if tb * 4 <= b < tb * 4 + 4:
                    buses['pad'].add(T(gbar, b - tb * 4), play_sample(ins_pad, k + tr, l * BEAT, release=0.4))

    for kind, first, n, tr in plan:
        for i in range(n):
            g = first + i
            if kind == 'intro':
                # ringing A5, toms building, a crash into the theme
                if i == 0:
                    for side in ('rhyL', 'rhyR'):
                        chord(side, g, 0, 9, 7.5, False, 0)
                    hit('crash', g, 0)
                if i >= 2:
                    for s in range(8 if i == 2 else 16):
                        hit('toml' if s < 4 else 'tomm' if s < 8 else 'tomh' if s < 12 else 'snare',
                            g, s / (2 if i == 2 else 4), 0.5 + 0.03 * s)
                if i == 3:
                    for side in ('rhyL', 'rhyR'):
                        for s in range(8):
                            chord(side, g, 2 + s / 4, 9, 0.22, True, 0)
            elif kind == 'break':
                theme_bar(g, 8 + (i % 4), 'break', tr)
            elif kind == 'outro':
                if i == 0:
                    for side in ('rhyL', 'rhyR'):
                        chord(side, g, 0, 9, 7.0, False, 0)
                    hit('crash', g, 0); hit('kick2', g, 0, 1.2)
                if i == 2:
                    hit('crash', g, 0, 0.6)
            else:
                theme_bar(g, i, kind, tr)

    # mix
    n = int(TOTAL * SR)
    gtr = 0.38 * drive(buses["rhyL"].x, 9.0)
    gtrR = 0.38 * drive(buses["rhyR"].x, 9.0)
    lead = 0.75 * drive(buses['lead'].x, 14.0, 5200)
    harm = 0.5 * drive(buses['harm'].x, 14.0, 5200)
    if stems is not None:
        stems.update(gtrL=gtr, gtrR=gtrR, lead=lead, harm=harm, bass=buses['bass'].x, drums=buses['drums'].x,
                     pad=buses['pad'].x, rawL=buses['rhyL'].x, rawlead=buses['lead'].x)
    mix = (pan(gtr, -0.8) + pan(gtrR, 0.8) + pan(lead, 0.05) + pan(harm, -0.25)
           + pan(0.9 * buses['bass'].x, 0) + pan(1.0 * buses['drums'].x, 0)
           + pan(0.5 * buses['pad'].x, 0.3) + pan(0.5 * buses['pad'].x, -0.3))
    # a short room on the lead, the drums and the pad
    from scipy.signal import fftconvolve
    ir_n = int(1.1 * SR)
    ir = np.exp(-np.arange(ir_n) / (0.25 * SR)) * rng.normal(0, 1, (2, ir_n))
    ir /= np.sqrt((ir ** 2).sum(1, keepdims=True))
    send = 0.25 * lead + 0.15 * buses['drums'].x + 0.4 * buses['pad'].x
    wet = np.stack([fftconvolve(send, ir[c])[:len(send)] for c in range(2)], 1)
    mix = mix + 0.35 * wet
    # the song loops: what rings past the end goes back to the start
    tail = mix[n:]
    mix = mix[:n].copy()
    mix[:len(tail)] += tail[:n]
    # master: soft limiter, then -1 dBFS
    peak = np.percentile(np.abs(mix), 99.95)
    mix = np.tanh(mix / peak * 1.2) / np.tanh(1.2)
    mix *= 0.89 / np.abs(mix).max()
    return (mix * 32767).astype(np.int16)

# ---------------------------------------------------------------------------
# second style: eurobeat / dance, with Pocket Fighter's own instruments only
TRIAD = {9: (0, 3, 7), 2: (0, 3, 7), 4: (0, 4, 7), 5: (0, 4, 7), 7: (0, 4, 7), 0: (0, 4, 7),
         10: (0, 4, 7), 11: (0, 3, 6), 8: (0, 3, 6)}

def master(mix, rng, sends):
    from scipy.signal import fftconvolve
    n = int(TOTAL * SR)
    ir_n = int(1.6 * SR)
    ir = np.exp(-np.arange(ir_n) / (0.35 * SR)) * rng.normal(0, 1, (2, ir_n))
    ir /= np.sqrt((ir ** 2).sum(1, keepdims=True))
    wet = np.stack([fftconvolve(sends, ir[c])[:len(sends)] for c in range(2)], 1)
    mix = mix + 0.3 * wet
    tail = mix[n:]
    mix = mix[:n].copy()
    mix[:len(tail)] += tail[:n]
    peak = np.percentile(np.abs(mix), 99.97)
    mix = np.tanh(mix / peak * 1.1) / np.tanh(1.1)
    mix *= 0.89 / np.abs(mix).max()
    return (mix * 32767).astype(np.int16)

def dance_kick():
    """a synthesised four-on-the-floor kick (909 style): a sine falling from
    170 to 48 Hz with a short click"""
    n = int(0.42 * SR); t = np.arange(n) / SR
    f = 48 + 122 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.22)
    click = np.exp(-t / 0.003) * np.random.default_rng(7).uniform(-1, 1, n) * 0.25
    x = np.tanh(1.6 * (body + click))
    x[:int(0.001 * SR)] *= np.linspace(0, 1, int(0.001 * SR))
    return x / np.abs(x).max()

def build_dance(sgemf, stems=None):
    z = zipfile.ZipFile(sgemf)
    pf = PF(z)
    rng = np.random.default_rng(1997)
    mel = pf.track(2)
    lowmel = [n for n in pf.track(0) if 48 <= n[0] < 64]
    bass = pf.track(1)
    pad = pf.track(4)
    roots = roots_of(bass, 20)
    kit = {name: pf.instrument(0, p) for name, p in
           dict(kick=0, kick2=10, snare=1, hat=2, ohat=3, crash=4, clap=14, tomh=7, toml=9).items()}
    I = {n: pf.instrument(0, p) for n, p in dict(bass=32, lead=33, lead2=34, brass=41, stab=55, pad=62).items()}
    buses = {n: Bus() for n in ('kick', 'drums', 'bass', 'stab', 'arp', 'lead', 'harm', 'pad')}
    T = lambda gbar, beat: (gbar * 4 + beat) * BEAT

    KICK = dance_kick()
    def hit(name, gbar, beat, gain=1.0, bus='drums'):
        if name == 'kick4':
            buses['kick'].add(T(gbar, beat), KICK * gain)
            return
        ins = kit[name]
        buses[bus].add(T(gbar, beat), play_sample(ins, ins['unity'], 0.5) * gain)

    def note(bus, ins, gbar, beat, key, length, gain=1.0, release=0.06):
        buses[bus].add(T(gbar, beat), play_sample(I[ins], key, length * BEAT, gain, release))

    def triad(pc, tr, base=60):
        r = (pc + tr) % 12
        k = base + ((r - base) % 12)
        return [k + iv for iv in TRIAD.get(pc, (0, 3, 7))]

    plan = [('intro', 0, 4, 0)]
    bar = 4
    for kind, n, tr in (('theme', 20, 0), ('theme2', 20, 0), ('break', 12, 0), ('arp', 20, 0),
                        ('theme2', 20, 0), ('final', 20, 2), ('outro', 4, 0)):
        plan.append((kind, bar, n, tr)); bar += n
    assert bar == BARS

    def drums(g, tb, kind, i_in_section, n_section):
        if kind == 'break':
            # no kick: a snare roll building over the last 4 bars
            if i_in_section >= n_section - 4:
                k = i_in_section - (n_section - 4)
                step = (1, 2, 4, 8)[k]
                for s in range(4 * step):
                    hit('snare', g, s / step, 0.3 + 0.15 * k)
            for b in range(4): hit('hat', g, b + 0.5, 0.25)
            return
        for b in range(4):
            hit('kick4', g, b, 1.0); hit('kick', g, b, 0.3, 'kick')
            hit('ohat', g, b + 0.5, 0.45)
            for s in (0.25, 0.75): hit('hat', g, b + s, 0.25)
        hit('clap', g, 1, 0.8); hit('clap', g, 3, 0.8)
        hit('snare', g, 1, 0.5); hit('snare', g, 3, 0.5)
        if tb % 4 == 0: hit('crash', g, 0, 0.7)
        if tb % 8 == 7:
            for s in range(4): hit('snare', g, 3 + s / 4, 0.35 + 0.1 * s)

    def theme_bar(g, tb, kind, tr, i_in_section, n_section):
        r = [roots[tb * 4 + j] for j in range(4)]
        drums(g, tb, kind, i_in_section, n_section)
        # octave bass in 8ths (eurobeat), the root of each beat
        for j in range(4):
            k = 33 + ((r[j] + tr - 33) % 12)
            if kind == 'break':
                if j == 0: note('bass', 'bass', g, 0, k, 3.8, 0.9, 0.3)
                continue
            note('bass', 'bass', g, j, k, 0.45, 0.95)
            note('bass', 'bass', g, j + 0.5, k + 12, 0.45, 0.8)
        # off-beat stabs
        if kind != 'break':
            for j in range(4):
                for k in triad(r[j], tr):
                    note('stab', 'stab', g, j + 0.5, k, 0.3, 0.32)
        # 16th arpeggio (arp section, and quietly in theme2/final)
        if kind in ('arp', 'theme2', 'final'):
            for j in range(4):
                tri = triad(r[j], tr, 72)
                seq = [tri[0], tri[1], tri[2], tri[1] + 12 if kind == 'arp' else tri[1]]
                for s in range(4):
                    note('arp', 'lead2', g, j + s / 4, seq[s], 0.22, 0.5 if kind == 'arp' else 0.28)
        # pad: the original pad line, and held chords in the breakdown
        if kind == 'break' or 8 <= tb < 12:
            for k in triad(r[0], tr, 57):
                note('pad', 'pad', g, 0, k, 4.0, 0.35, 0.5)
        # lead
        line = [n for n in mel if tb * 4 <= n[0] < tb * 4 + 4]
        if 12 <= tb < 16:
            line = [n for n in lowmel if tb * 4 <= n[0] < tb * 4 + 4]
            line = [(b, k + 12, l) for b, k, l in line]
        if kind == 'break':
            line = [(b, k - 12, l) for b, k, l in mel if (tb - 8) * 4 <= b - 0 < (tb - 7) * 4] if False else []
        if kind == 'arp':
            line = [(b, k + 12, l) for b, k, l in line if 16 <= tb]
        for b, k, l in line:
            note('lead', 'lead', g, b - tb * 4, k + tr, max(0.25, l), 0.9, 0.15)
            if kind in ('theme2', 'final'):
                note('harm', 'brass', g, b - tb * 4, third_below(k) + tr, max(0.25, l), 0.6, 0.15)

    for kind, first, n, tr in plan:
        for i in range(n):
            g = first + i
            if kind == 'intro':
                # pad and a filtered beat coming in, the riff's chord
                for k in triad(9, 0, 57):
                    note('pad', 'pad', g, 0, k, 4.0, 0.35, 0.5)
                if i >= 1:
                    for b in range(4): hit('kick4', g, b, 0.3 + 0.2 * i)
                if i >= 2:
                    for b in range(4): hit('ohat', g, b + 0.5, 0.3)
                if i == 3:
                    for s in range(8): hit('snare', g, 2 + s / 4, 0.3 + 0.08 * s)
            elif kind == 'break':
                theme_bar(g, 8 + (i % 4), 'break', tr, i, n)
            elif kind == 'outro':
                if i == 0:
                    hit('crash', g, 0); hit('kick4', g, 0, 1.0)
                    for k in triad(9, 0, 57): note('pad', 'pad', g, 0, k, 8.0, 0.4, 1.0)
                    note('bass', 'bass', g, 0, 33, 4.0, 0.9, 0.5)
            else:
                theme_bar(g, i, kind, tr, i, n)

    # mix: everything but the drums ducks under the kick (side-chain pump)
    n = len(buses['kick'].x)
    env = np.ones(n)
    beat_n = int(BEAT * SR)
    duck = 1 - 0.55 * np.exp(-np.arange(beat_n) / (0.06 * SR))
    for b in range(BARS * 4):
        i = int(b * BEAT * SR)
        if i + beat_n <= n: env[i:i + beat_n] = np.minimum(env[i:i + beat_n], duck)
    x = buses
    mix = (pan(1.25 * x['kick'].x, 0) + pan(0.75 * x['drums'].x, 0.1)
           + pan(0.8 * x['bass'].x * env, 0)
           + pan(0.55 * x['stab'].x * env, -0.35) + pan(0.55 * x['stab'].x * env, 0.35) * 0.0
           + pan(0.45 * x['arp'].x * env, 0.45)
           + pan(0.9 * x['lead'].x, 0) + pan(0.55 * x['harm'].x, -0.3)
           + pan(0.5 * x['pad'].x * env, -0.5) + pan(0.5 * x['pad'].x * env, 0.5))
    if stems is not None:
        stems.update({k: v.x for k, v in buses.items()})
    sends = 0.3 * x['lead'].x + 0.2 * x['harm'].x + 0.3 * x['pad'].x + 0.15 * x['stab'].x + 0.2 * x['arp'].x
    return master(mix, rng, sends)

STYLES = {'metal': build_metal, 'dance': build_dance}

def build(sgemf, style='dance', stems=None):
    return STYLES[style](sgemf, stems)

def main(a):
    style = 'dance'
    if len(a) == 4 and a[2] == '--style': style = a[3]; a = a[:2]
    if len(a) != 2:
        print(__doc__); sys.exit(1)
    pcm = build(a[0], style)
    import wave
    w = wave.open(a[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes()); w.close()
    print('%s: %.2f s' % (a[1], len(pcm) / SR))

if __name__ == '__main__':
    main(sys.argv[1:])
