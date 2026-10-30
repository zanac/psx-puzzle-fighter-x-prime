#!/usr/bin/env python3
"""Sony VAB (VH header + VB sample body) parser, and PSX ADPCM (VAG) decoder.

usage: vab.py VH_FILE[:OFFSET] [VB_FILE[:OFFSET]] [--wav OUTDIR]
"""
import struct, sys, os

def parse_vh(d, off=0):
    assert d[off:off + 4] == b'pBAV', 'no VAB header'
    ver, vid, fsize, _, ps, ts, vs, mvol, pan, a1, a2 = struct.unpack_from('<IIIHHHHBBBB', d, off + 4)
    p = off + 32
    progs = []
    for i in range(128):
        tones, pvol, prior, mode, ppan = struct.unpack_from('<BBBBB', d, p + 16 * i)
        progs.append(dict(tones=tones, vol=pvol, prior=prior, mode=mode, pan=ppan, raw=d[p + 16 * i:p + 16 * i + 16]))
    p += 128 * 16
    tones = []
    np = sum(1 for x in progs if x['tones'])
    # tone attributes: 16 per program, for the ps programs that exist
    for i in range(ps * 16):
        t = d[p + 32 * i:p + 32 * i + 32]
        prior, mode, vol, tpan, center, shift, mn, mx, vibw, vibt, porw, port, pbmin, pbmax, _, _, adsr1, adsr2, prog, vag = struct.unpack_from('<BBBBBBBBBBBBBBBBHHhh', t, 0)
        tones.append(dict(prior=prior, mode=mode, vol=vol, pan=tpan, center=center, shift=shift, min=mn, max=mx,
                          adsr1=adsr1, adsr2=adsr2, prog=prog, vag=vag, raw=t))
    p += ps * 16 * 32
    sizes = [s << 3 for s in struct.unpack_from('<256H', d, p)]
    return dict(ps=ps, ts=ts, vs=vs, mvol=mvol, progs=progs, tones=tones, sizes=sizes, hdr_end=p + 512 - off)

COEF = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)]

def decode_vag(b):
    out, s1, s2 = [], 0, 0
    for i in range(0, len(b) - 15, 16):
        sh, fl = b[i] & 15, b[i + 1]
        f = min(b[i] >> 4, 4)
        k0, k1 = COEF[f]
        for j in range(28):
            byte = b[i + 2 + j // 2]
            n = (byte >> 4) if j & 1 else (byte & 15)
            if n & 8: n -= 16
            v = (n << 12) >> sh
            v += (s1 * k0 + s2 * k1) // 64
            v = max(-32768, min(32767, v))
            out.append(v); s2, s1 = s1, v
        if fl & 1 and i > 0:
            break
    return out

def vags(vh, vb):
    out, p = [], 0
    for i in range(1, vh['vs'] + 1):
        n = vh['sizes'][i]
        out.append(vb[p:p + n]); p += n
    return out

def wav(path, samples, rate):
    import wave
    w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack('<%dh' % len(samples), *samples)); w.close()
