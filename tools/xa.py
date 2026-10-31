"""CD-XA ADPCM (Level B: 37.8 kHz, 4 bits, stereo), encoder and decoder.

A sector's audio is 18 sound groups of 128 bytes (+ 20 unused bytes):
  bytes 0-15   the 8 sound units' parameters (filter << 4 | range): units
               0-3 at 4-7 and 4-7 at 8-11; 0-3 and 12-15 are copies of them
  bytes 16-127 28 words of 4 bytes: byte j of word i holds sample i of unit
               2j (low nibble) and of unit 2j + 1 (high nibble)
Stereo: even units are left, odd units right; a group is 4 x 28 = 112
samples per channel, a sector 2016.
Decoding: s = (nibble << 12, sign-extended) >> range,
          out = s + (prev1 * K0[f] + prev2 * K1[f] + 32) / 64."""
import numpy as np

K0 = (0, 60, 115, 98)
K1 = (0, 0, -52, -55)
SAMPLES_PER_SECTOR = 2016          # per channel
GROUPS = 18

_F = np.repeat(np.arange(4), 13)
_R = np.tile(np.arange(13), 4)
_K0 = np.array(K0)[_F]
_K1 = np.array(K1)[_F]
_SC = (1 << _R) / 4096.0

def _unit(x, p1, p2):
    """best (error, filter, range, nibbles, p1, p2) for 28 samples; all
    52 filter/range pairs at once"""
    q1 = np.full(52, p1, np.int64); q2 = np.full(52, p2, np.int64)
    err = np.zeros(52); nib = np.empty((28, 52), np.int64)
    for i in range(28):
        pred = (q1 * _K0 + q2 * _K1 + 32) >> 6
        n = np.clip(np.rint((int(x[i]) - pred) * _SC), -8, 7).astype(np.int64)
        s = np.clip(((n << 12) >> _R) + pred, -32768, 32767)
        err += (s - int(x[i])) ** 2.0
        nib[i] = n & 15
        q2, q1 = q1, s
    k = int(np.argmin(err))
    return err[k], int(_F[k]), int(_R[k]), nib[:, k], int(q1[k]), int(q2[k])

def encode(pcm):
    """pcm: int16 array (N, 2) at 37800 Hz -> list of 2304-byte sector bodies"""
    pcm = np.asarray(pcm, np.int64)
    n = -(-len(pcm) // SAMPLES_PER_SECTOR) * SAMPLES_PER_SECTOR
    if n > len(pcm):
        pcm = np.concatenate([pcm, np.zeros((n - len(pcm), 2), np.int64)])
    prev = [[0, 0], [0, 0]]
    out = []
    for s0 in range(0, n, SAMPLES_PER_SECTOR):
        sec = bytearray()
        for g in range(GROUPS):
            base = s0 + g * 112
            params = [0] * 8; nibs = [None] * 8
            for u in range(8):
                ch = u & 1
                x = pcm[base + (u >> 1) * 28: base + (u >> 1) * 28 + 28, ch]
                err, f, r, nb, q1, q2 = _unit(x, prev[ch][0], prev[ch][1])
                prev[ch] = [q1, q2]
                params[u] = f << 4 | r; nibs[u] = nb
            grp = bytearray(128)
            grp[0:4] = bytes(params[0:4]); grp[4:8] = bytes(params[0:4])
            grp[8:12] = bytes(params[4:8]); grp[12:16] = bytes(params[4:8])
            for i in range(28):
                for j in range(4):
                    grp[16 + 4 * i + j] = int(nibs[2 * j][i]) | int(nibs[2 * j + 1][i]) << 4
            sec += grp
        out.append(bytes(sec))
    return out

def decode(sectors):
    """inverse of encode (for checks): list of sector bodies -> int16 (N, 2)"""
    prev = [[0, 0], [0, 0]]
    out = []
    for sec in sectors:
        for g in range(GROUPS):
            grp = sec[128 * g:128 * g + 128]
            params = list(grp[4:12])
            buf = np.zeros((112, 2), np.int64)
            for u in range(8):
                f, r = params[u] >> 4, params[u] & 15
                ch = u & 1; q1, q2 = prev[ch]
                for i in range(28):
                    b = grp[16 + 4 * i + (u >> 1)]
                    n = (b >> 4) if u & 1 else (b & 15)
                    if n >= 8: n -= 16
                    s = ((n << 12) >> r) + ((q1 * K0[f] + q2 * K1[f] + 32) >> 6)
                    s = max(-32768, min(32767, s))
                    buf[(u >> 1) * 28 + i, ch] = s
                    q2, q1 = q1, s
                prev[ch] = [q1, q2]
            out.append(buf)
    return np.concatenate(out).astype(np.int16)
