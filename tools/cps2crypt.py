"""CPS2 program ROM encryption, after MAME's cps2crypt.c (Andreas Naive, Nicola Salmoria,
Charles MacDonald). decrypt() gives what the 68000 fetches as opcodes; encrypt() is its
inverse, used to put patched code back. Data reads are never encrypted."""
import struct
from cps2tables import T

FN1A = [10, 4, 6, 7, 2, 13, 15, 14]; FN1B = [0, 1, 3, 5, 8, 9, 11, 12]
FN2A = [6, 0, 2, 13, 1, 4, 14, 7];   FN2B = [3, 5, 9, 10, 8, 15, 12, 11]
bit = lambda v, n: (v >> n) & 1

def _opt(boxes):
    res = []
    for table, inputs, outputs in boxes:
        lk = []
        for i in range(256):
            r = 0
            for j, b in enumerate(inputs):
                if b != -1: r |= bit(i, b) << j
            lk.append(r)
        o = []
        for v in table:
            m = 0
            if v & 1: m |= 1 << outputs[0]
            if v & 2: m |= 1 << outputs[1]
            o.append(m)
        res.append((lk, o))
    return res

S1 = [_opt(T['fn1_r%d_boxes' % r]) for r in range(1, 5)]
S2 = [_opt(T['fn2_r%d_boxes' % r]) for r in range(1, 5)]

def _fn_table(boxes, key):
    """the round function for one key, as a 256-entry table"""
    ks = [(key >> (6 * k)) & 0x3f for k in range(4)]
    return [boxes[0][1][boxes[0][0][x] ^ ks[0]] | boxes[1][1][boxes[1][0][x] ^ ks[1]] |
            boxes[2][1][boxes[2][0][x] ^ ks[2]] | boxes[3][1][boxes[3][0][x] ^ ks[3]] for x in range(256)]

def _fn(boxes, x, key):
    return (boxes[0][1][boxes[0][0][x] ^ (key & 0x3f)] | boxes[1][1][boxes[1][0][x] ^ ((key >> 6) & 0x3f)] |
            boxes[2][1][boxes[2][0][x] ^ ((key >> 12) & 0x3f)] | boxes[3][1][boxes[3][0][x] ^ ((key >> 18) & 0x3f)])

def _split(v, A, B):
    l = sum(bit(v, B[i]) << i for i in range(8)); r = sum(bit(v, A[i]) << i for i in range(8))
    return l, r

def _join(l, r, A, B):
    return sum(bit(l, i) << A[i] for i in range(8)) | sum(bit(r, i) << B[i] for i in range(8))

def _expand(src, bits, n):
    d = [0] * n
    for i, b in enumerate(bits):
        d[i // 24 if n == 4 else i // 32] |= bit(src[b // 32], b % 32) << (i % 24 if n == 4 else i % 32)
    return d

def key_from_file(k):
    dec = [0] * 10
    for b in range(160):
        bt = (317 - b) % 160
        if (k[bt // 8] >> ((bt ^ 7) % 8)) & 1: dec[b // 16] |= 0x8000 >> (b % 16)
    key = [(dec[0] << 16) | dec[1], (dec[2] << 16) | dec[3]]
    if dec[9] == 0xffff: return key, 0xff0000, 0xffffff
    return key, 0, (((~dec[9] & 0x3ff) << 14) | 0x3fff) + 1

def _keys2(master):
    k1 = _expand(master, T['expand_1st_key'], 4)
    k1[0] ^= bit(k1[0], 1) << 4; k1[0] ^= bit(k1[0], 2) << 5; k1[0] ^= bit(k1[0], 8) << 11
    k1[1] ^= bit(k1[1], 0) << 5; k1[1] ^= bit(k1[1], 8) << 11
    k1[2] ^= bit(k1[2], 1) << 5; k1[2] ^= bit(k1[2], 8) << 11
    for i in range(0x10000):
        l, r = _split(i, FN1A, FN1B)
        l ^= _fn(S1[0], r, k1[0]); r ^= _fn(S1[1], l, k1[1]); l ^= _fn(S1[2], r, k1[2]); r ^= _fn(S1[3], l, k1[3])
        seed = _join(l, r, FN1A, FN1B)
        sub = [0, 0]
        for j, b in enumerate(T['expand_subkey']): sub[j // 32] |= bit(seed, b) << (j % 32)
        sub = [sub[0] ^ master[0], sub[1] ^ master[1]]
        k2 = _expand(sub, T['expand_2nd_key'], 4)
        k2[0] ^= bit(k2[0], 0) << 5; k2[0] ^= bit(k2[0], 6) << 11
        k2[1] ^= bit(k2[1], 0) << 5; k2[1] ^= bit(k2[1], 1) << 4
        k2[2] ^= bit(k2[2], 2) << 5; k2[2] ^= bit(k2[2], 3) << 4; k2[2] ^= bit(k2[2], 7) << 11
        k2[3] ^= bit(k2[3], 1) << 5
        yield i, k2

def _crypt(rom, keyfile, decrypt, only=None):
    """rom: bytes of the whole program (CPS2 dumps: little-endian words, address 0 first).
    only: optional set of word addresses to transform (others left as they are)."""
    master, lo, hi = key_from_file(keyfile)
    w = list(struct.unpack('<%dH' % (len(rom) // 2), rom))
    n = len(w)
    for i, k2 in _keys2(master):
        addrs = [a for a in range(i, n, 0x10000) if lo <= a <= hi and (only is None or a in only)]
        if not addrs: continue
        for a in addrs:
            if decrypt:
                l, r = _split(w[a], FN2A, FN2B)
                l ^= _fn(S2[0], r, k2[0]); r ^= _fn(S2[1], l, k2[1]); l ^= _fn(S2[2], r, k2[2]); r ^= _fn(S2[3], l, k2[3])
                w[a] = _join(l, r, FN2A, FN2B)
            else:   # the network leaves l on the A bits and r on the B bits: undo it from there
                l, r = _split(w[a], FN2B, FN2A)
                r ^= _fn(S2[3], l, k2[3]); l ^= _fn(S2[2], r, k2[2]); r ^= _fn(S2[1], l, k2[1]); l ^= _fn(S2[0], r, k2[0])
                w[a] = _join(l, r, FN2B, FN2A)
    return struct.pack('<%dH' % n, *w)

def decrypt(rom, keyfile, only=None): return _crypt(rom, keyfile, True, only)
def encrypt(rom, keyfile, only=None): return _crypt(rom, keyfile, False, only)
