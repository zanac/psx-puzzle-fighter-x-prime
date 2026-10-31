"""Pocket Fighter (QSound driver 1.30) songs and sounds -> Super Puzzle Fighter
II Turbo (driver 2.01B), for the arcade set.

Both drivers are Capcom's QSound Z80 driver: the same sample table entries,
the same envelope and volume tables; the sequences and instruments differ.

PF (sgemf, pcf.01/02):  song table 0x9005 (4-byte BE linear pointers),
  instrument banks 0x3B04 (16 LE pointers, 4-byte instruments: sample (LE),
  fine tune, articulation index), articulations 0x8000 (8 bytes: AR DR SL SR
  RR ...), sample table 0x5000 (8 bytes: bank, start, loop, end (LE), unity).
  Tracks V1: a state machine (durations from tables x gate, octave, ties).
SPF2T (spf2t, pzf.01/02): song table 0x6004, instrument bank pointers 0x3FE4
  (14), 8-byte instruments (sample (LE), fine tune, AR DR SL SR RR), sample
  table 0x4F78 (443 entries). Tracks V2: rests (7-bit groups), notes
  (0x80|velocity, key, duration as a MIDI varlen), commands 0xC1-0xFF.

What this writes into SPF2T's Z80 program:
- the bank pointer table moved to 0x3E88 (the 4 references patched) with a new
  bank 14 after it: the converted instruments;
- new sample table entries after SPF2T's 443;
- the converted songs in the free banked space (0x24B00-) and free slots of
  the song table;
and a new QSound sample ROM (banks 0x40-): PF's 64 KB banks that hold the
samples used, copied whole, so the addresses inside a bank stay valid.

Command mapping (V1 -> V2), from the two drivers' code (V2's dispatcher at
0x10F9 indexes its table from C0, a no-op):
  05 tempo (word)               -> C1 (same unit)
  07 volume (curve PF 0x34F1)   -> C6 (the same curve, SPF 0x3685)
  18 pan 0-0x20 (QSound 0x110+) -> C7 pan*4 (the driver writes 0x110 + v/4)
  08 program / 1F bank          -> C4 / C2 (one bank for everything converted)
  0C detune: added to the pitch in 1/256 semitones, as the instrument's fine
     tune is (V2's C3 is 24 times coarser) -> an instrument copy with the
     detune in its fine tune
  0D portamento (x2)            -> C9 (x2, the same)
  1B vibrato, 1C tremolo, 1D LFO rate (tables PF 0x38F1, 0x39F1, 0x37F1)
                                -> C5, E2, E1 (identical tables in SPF)
  1E LFO reset                  -> E0
  0A / 0B transpose             -> folded into the notes
  ties (state 0x40)             -> merged into longer notes
  counted loops                 -> unrolled; 16 (loop forever) -> D0 .. D4 00
"""
import struct

# --- Pocket Fighter (V1.30) --------------------------------------------------
PF_SEQ, PF_INS, PF_NBANKS, PF_SAMP, PF_ARTIC = 0x9005, 0x3B04, 16, 0x5000, 0x8000
# --- SPF2T (V2.01B) ------------------------------------------------------------
SPF_SEQ, SPF_NSEQ = 0x6004, 907
SPF_INS, SPF_NBANKS = 0x3FE4, 14
SPF_INS_REFS = (0x037D, 0x0404, 0x0C9C, 0x1182)   # operand addresses of the 4 references
SPF_SAMP, SPF_NSAMP = 0x4F78, 443
NEW_INS_PTRS = 0x3E88          # free (0x3E87-0x3FDF): pointer table, then bank 14
NEW_BANK = SPF_NBANKS          # 14
NEW_SEQ_SPACE = (0x24B00, 0x40000)
NEW_QBANK0 = 0x40              # first QSound bank of the new sample ROM

DELTA = [[2, 4, 8, 0x10, 0x20, 0x40, 0x80], [3, 6, 0xC, 0x18, 0x30, 0x60, 0xC0], [0, 9, 0x12, 0x24, 0x48, 0x90, 0]]
OCT = [0x00, 0x0C, 0x18, 0x24, 0x30, 0x3C, 0x48, 0x54, 0x18, 0x24, 0x30, 0x3C, 0x48, 0x54, 0x60, 0x6C]
V1_CTL = {0x07: 'vol', 0x08: 'prog', 0x0C: 'bend', 0x0D: 'porta', 0x18: 'pan', 0x19: 'qeff', 0x1A: 'mvol',
          0x1B: 'vib', 0x1C: 'trem', 0x1D: 'lfo', 0x1E: 'lforeset', 0x1F: 'bank'}

def u16(d, a): return struct.unpack('<H', d[a:a + 2])[0]
def b16(d, a): return struct.unpack('>H', d[a:a + 2])[0]
def b32(d, a): return struct.unpack('>I', d[a:a + 4])[0]

def pf_song(z80, k):
    return b32(z80, PF_SEQ + 4 * k) & 0xFFFFF

def v1_track(d, off):
    """run a V1 track: (events, end time, loop time or None); loops unrolled.
    events: ('note', t, key, gate, delta, tie) / ('ctl', t, name, value)"""
    ev = []; t = 0; state = 0; dur = 0xFF; trans = 0
    loop = [0] * 4; loopoff = [0] * 4; pos = off; seen = {}
    for _ in range(400000):
        seen.setdefault(pos, t)
        b = d[pos]; pos += 1
        if b >= 0x20:
            if (state & 0x30) == 0: tbl = 1
            elif (state & 0x10) == 0: tbl = 0
            else: state &= ~0x10; tbl = 2
            delta = DELTA[tbl][((b >> 5) & 7) - 1]
            if b & 0x1F:
                key = (b & 0x1F) + OCT[state & 0x0F] - 1 + trans
                ev.append(('note', t, key, (delta * dur) >> 8, delta, bool(state & 0x40)))
            t += delta
            continue
        if b == 0x00: state ^= 0x20
        elif b == 0x01: state ^= 0x40
        elif b == 0x02: state |= 0x10
        elif b == 0x03: state ^= 8
        elif b == 0x04: state = (state & 0x97) | d[pos]; pos += 1
        elif b == 0x05: ev.append(('ctl', t, 'tempo', b16(d, pos))); pos += 2
        elif b == 0x06: dur = d[pos]; pos += 1
        elif b == 0x09: state = (state & 0xF8) | d[pos]; pos += 1
        elif b in (0x0A, 0x0B): trans = struct.unpack('b', d[pos:pos + 1])[0]; pos += 1
        elif b in V1_CTL: ev.append(('ctl', t, V1_CTL[b], d[pos])); pos += 1
        elif 0x0E <= b <= 0x11:
            n = b - 0x0E; here = pos
            if loop[n] == 0 and loopoff[n] == 0:
                loopoff[n] = here; loop[n] = d[pos]; pos += 1
            elif loopoff[n] != here:
                raise ValueError('nested loop at %x' % here)
            else:
                loop[n] -= 1; pos += 1
            if d[pos] & 0x80 == 0:
                jump = pos + 1 - d[pos]; pos += 1
            else:
                jump = pos + 2 + struct.unpack('>h', d[pos:pos + 2])[0]; pos += 2
            if loop[n] == 0: loopoff[n] = 0
            else: pos = jump
        elif 0x12 <= b <= 0x15:
            n = b - 0x12
            if loop[n] - 1 == 0:
                loop[n] = 0; loopoff[n] = 0
                state = (state & 0x97) | d[pos]
                pos += 3 + struct.unpack('>h', d[pos + 1:pos + 3])[0]
            else:
                pos += 3
        elif b == 0x16:
            jump = pos + 2 + struct.unpack('>h', d[pos:pos + 2])[0]
            if jump not in seen: raise ValueError('loop target %x not reached' % jump)
            return ev, t, seen[jump]
        elif b == 0x17:
            return ev, t, None
        else:
            raise ValueError('V1 opcode %02x at %x' % (b, pos - 1))
    raise ValueError('track too long')

# --- V2 writer --------------------------------------------------------------------
def varlen(v):
    out = [v & 0x7F]; v >>= 7
    while v: out.append(0x80 | (v & 0x7F)); v >>= 7
    return bytes(reversed(out))

def rest(v):
    out = []
    while True:
        out.append(v & 0x7F); v >>= 7
        if not v: break
    return bytes(reversed(out))

class Song:
    """the instruments a song needs, in the order met: (bank, prog) -> new index"""
    def __init__(self): self.ins = {}

def notes_of(ev):
    """V1 notes -> sounding notes (t, key, length): ties merged"""
    out = []; cur = None     # [t, key, end]
    for e in ev:
        if e[0] != 'note': continue
        _, t, key, gate, delta, tie = e
        if cur is not None:
            if key == cur[1]:
                cur[2] = t + (delta if tie else gate)
                if not tie: out.append(tuple(cur)); cur = None
                continue
            cur[2] = t; out.append(tuple(cur)); cur = None
        if tie: cur = [t, key, t + delta]
        else: out.append((t, key, t + gate))
    if cur is not None: out.append(tuple(cur))
    return [(t, k, max(1, e - t)) for t, k, e in out]

def v2_track(ev, end, loop_t, ins_map, velocity, bank):
    """V2 bytes for one track"""
    items = []      # (t, order, bytes)
    prog_bank = 0; detune = 0; cur_prog = None
    for e in ev:
        if e[0] != 'ctl': continue
        _, t, name, v = e
        if name == 'tempo': items.append((t, 0, bytes([0xC1]) + struct.pack('>H', v)))
        elif name == 'bank': prog_bank = v
        elif name == 'prog':
            items.append((t, 1, bytes([0xC2, bank, 0xC4, ins_map[(prog_bank, v & 0x7F, detune)]])))
            cur_prog = (prog_bank, v & 0x7F)
        elif name == 'bend':
            detune = struct.unpack('b', bytes([v]))[0]
            if cur_prog is not None:
                items.append((t, 1, bytes([0xC2, bank, 0xC4, ins_map[cur_prog + (detune,)]])))
        elif name == 'vol':
            if v & 0x80: continue          # +0x40 of the channel: not used by the songs converted so far
            items.append((t, 2, bytes([0xC6, v])))
        elif name == 'pan': items.append((t, 2, bytes([0xC7, 0x7F if v >= 0x20 else v * 4])))
        elif name == 'porta': items.append((t, 2, bytes([0xC9, v])))
        elif name == 'vib': items.append((t, 2, bytes([0xC5, v])))
        elif name == 'trem': items.append((t, 2, bytes([0xE2, v])))
        elif name == 'lfo': items.append((t, 2, bytes([0xE1, v])))
        elif name == 'lforeset': items.append((t, 2, bytes([0xE0, v])))
    for t, key, ln in notes_of(ev):
        items.append((t, 3, bytes([0x80 | velocity, key & 0x7F]) + varlen(ln)))
    if loop_t is not None:
        items.append((loop_t, -1, bytes([0xD0])))
    items.sort(key=lambda x: (x[0], x[1]))
    out = bytearray(); now = 0
    for t, _, b in items:
        if t > now: out += rest(t - now); now = t
        out += b
    if end > now: out += rest(end - now)
    out += bytes([0xD4, 0x00]) if loop_t is not None else bytes([0xFF])
    return bytes(out)

def convert(pf_z80, pf_q, spf_z80, spf_q, songs, velocity=0x3F):
    """songs: [(pf song number, spf slot)] -> (new spf_z80, extra QSound ROM)"""
    z = bytearray(spf_z80)
    used_ins = {}          # (pf bank, prog) -> new instrument index
    tracks_of = {}
    for k, slot in songs:
        p = pf_song(pf_z80, k)
        trs = []
        for i in range(16):
            o = b16(pf_z80, p + 1 + 2 * i)
            if not o: trs.append(None); continue
            ev, end, loop_t = v1_track(pf_z80, p + o)
            bank = 0; detune = 0; prog = None
            for e in ev:
                if e[0] != 'ctl': continue
                if e[2] == 'bank': bank = e[3]
                if e[2] == 'bend': detune = struct.unpack('b', bytes([e[3]]))[0]
                if e[2] == 'prog': prog = (bank, e[3] & 0x7F)
                if e[2] in ('prog', 'bend') and prog is not None:
                    used_ins.setdefault(prog + (detune,), len(used_ins))
            trs.append((ev, end, loop_t))
        tracks_of[(k, slot)] = (pf_z80[p], trs)
    # samples: PF banks copied whole into new QSound banks
    qbank = {}; new_samp = []
    ins_bytes = bytearray()
    samp_idx = {}
    for (bank, prog, detune), idx in sorted(used_ins.items(), key=lambda x: x[1]):
        a = u16(pf_z80, PF_INS + 2 * bank) + 4 * prog
        si, fine, art = u16(pf_z80, a), pf_z80[a + 2], pf_z80[a + 3]
        if si not in samp_idx:
            s = bytearray(pf_z80[PF_SAMP + 8 * si:PF_SAMP + 8 * si + 8])
            qbank.setdefault(s[0], NEW_QBANK0 + len(qbank))
            s[0] = qbank[s[0]]
            samp_idx[si] = SPF_NSAMP + len(new_samp)
            new_samp.append(bytes(s))
        fine = max(-128, min(127, struct.unpack('b', bytes([fine]))[0] + detune))
        adsr = pf_z80[PF_ARTIC + 8 * art:PF_ARTIC + 8 * art + 5]
        ins_bytes += struct.pack('<Hb', samp_idx[si], fine) + adsr
    # instrument bank pointer table moved, bank 14 = the converted instruments
    ptrs = [u16(z, SPF_INS + 2 * i) for i in range(SPF_NBANKS)]
    bank_at = NEW_INS_PTRS + 2 * (SPF_NBANKS + 2)
    if bank_at + len(ins_bytes) > 0x3FE0: raise ValueError('too many instruments: %d' % len(used_ins))
    if any(z[NEW_INS_PTRS:bank_at + len(ins_bytes)]): raise ValueError('instrument space not free')
    struct.pack_into('<%dH' % (SPF_NBANKS + 2), z, NEW_INS_PTRS, *(ptrs + [bank_at, 0]))
    z[bank_at:bank_at + len(ins_bytes)] = ins_bytes
    for r in SPF_INS_REFS:
        if u16(z, r) != SPF_INS: raise ValueError('instrument table reference at %x' % r)
        struct.pack_into('<H', z, r, NEW_INS_PTRS)
    # sample table entries
    sa = SPF_SAMP + 8 * SPF_NSAMP
    if any(z[sa:sa + 8 * len(new_samp)]): raise ValueError('sample table space not free')
    for i, s in enumerate(new_samp): z[sa + 8 * i:sa + 8 * i + 8] = s
    # songs
    at = NEW_SEQ_SPACE[0]
    for (k, slot), (flags, trs) in tracks_of.items():
        if b32(z, SPF_SEQ + 4 * slot): raise ValueError('song slot %d is used' % slot)
        body = []; offs = []; o = 1 + 32
        for tr in trs:
            if tr is None: offs.append(0); continue
            b = v2_track(*tr, used_ins, velocity, NEW_BANK)
            offs.append(o); body.append(b); o += len(b)
        seq = bytes([flags]) + struct.pack('>16H', *offs) + b''.join(body)
        if at + len(seq) > NEW_SEQ_SPACE[1]: raise ValueError('no room for the songs')
        if any(z[at:at + len(seq)]): raise ValueError('song space not free at %x' % at)
        z[at:at + len(seq)] = seq
        struct.pack_into('>I', z, SPF_SEQ + 4 * slot, at)
        at += len(seq) + 1
    # the new sample ROM
    q = bytearray(0x10000 * len(qbank))
    for old, new in qbank.items():
        q[(new - NEW_QBANK0) << 16:(new - NEW_QBANK0 + 1) << 16] = pf_q[old << 16:(old + 1) << 16]
    return bytes(z), bytes(q), dict(used_ins=len(used_ins), banks=len(qbank), song_bytes=at - NEW_SEQ_SPACE[0])
