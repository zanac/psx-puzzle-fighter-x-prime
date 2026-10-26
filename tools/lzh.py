#!/usr/bin/env python3
"""Codec for the halfword LZ used by the sprite graphics (decoder at
0x8010D5C0 in SLUS_004.18, mode 0: no address XOR, no nibble swap).

Stream: repeat { u16 flags (MSB first, 16 items) ; items }
  flag 0: literal u16
  flag 1: u16 v; if v & 0xF800: count = v >> 11, dist = v & 0x7FF
                 else:          dist = v, count = next u16
          count == dist == 0 -> end
          dist == 0          -> count zero halfwords
          else               -> copy count halfwords from dist halfwords back
"""
import struct

def decode(data, off=0):
    out = []
    p = off
    while True:
        flags = struct.unpack_from('<H', data, p)[0]
        p += 2
        for bit in range(15, -1, -1):
            if not (flags >> bit) & 1:
                out.append(struct.unpack_from('<H', data, p)[0])
                p += 2
                continue
            v = struct.unpack_from('<H', data, p)[0]
            p += 2
            if v & 0xF800:
                count, dist = v >> 11, v & 0x7FF
            else:
                dist = v
                count = struct.unpack_from('<H', data, p)[0]
                p += 2
            if count == 0 and dist == 0:
                return out, p - off
            if dist == 0:
                out.extend([0] * count)
            else:
                for _ in range(count):
                    out.append(out[-dist])

def encode(hw):
    """Optimal-parse encoder (dynamic programming on the exact bit cost)."""
    n = len(hw)
    INF = float('inf')
    # cost in bits: every item costs its payload plus one flag bit
    best = [INF] * (n + 1)
    choice = [None] * (n + 1)
    best[n] = 0
    for i in range(n - 1, -1, -1):
        c = 17 + best[i + 1]
        ch = (0, [hw[i]], 1)
        # zero runs (dist 0, long form)
        z = 0
        while i + z < n and hw[i + z] == 0 and z < 0xFFFF:
            z += 1
        for l in range(2, z + 1):
            cc = 33 + best[i + l]
            if cc < c:
                c, ch = cc, (1, [0, l], l)
        # back references: longest match per distance, all shorter lengths
        maxlen = {}
        for dist in range(1, min(i, 0x7FF) + 1):
            l = 0
            while i + l < n and l < 0xFFFF and hw[i + l] == hw[i + l - dist]:
                l += 1
            if l >= 2:
                maxlen[dist] = l
        for dist, ml in maxlen.items():
            for l in range(2, ml + 1):
                cc = (17 if l < 32 else 33) + best[i + l]
                if cc < c:
                    c = cc
                    ch = (1, [(l << 11) | dist] if l < 32 else [dist, l], l)
        best[i], choice[i] = c, ch
    items = []
    i = 0
    while i < n:
        ref, words, l = choice[i]
        items.append((ref, words))
        i += l
    return _pack(items)

def encode_greedy(hw):
    """Greedy encoder producing a stream the game decoder accepts."""
    items = []                          # (is_ref, payload halfwords)
    i, n = 0, len(hw)
    while i < n:
        best_len, best_dist = 0, 0
        # zero run
        z = 0
        while i + z < n and hw[i + z] == 0 and z < 0xFFFF:
            z += 1
        if z >= 2:
            best_len, best_dist = z, 0
        # back reference
        for dist in range(1, min(i, 0x7FF) + 1):
            l = 0
            while i + l < n and l < 0xFFFF and hw[i + l] == hw[i + l - dist]:
                l += 1
            if l > best_len:
                best_len, best_dist = l, dist
        if best_len >= 2:
            if best_dist and best_len < 32:
                items.append((1, [(best_len << 11) | best_dist]))
            else:
                items.append((1, [best_dist, best_len]))
            i += best_len
        else:
            items.append((0, [hw[i]]))
            i += 1
    return _pack(items)

def _pack(items):
    items = items + [(1, [0, 0])]       # end marker (dist 0, count 0)
    out = bytearray()
    for k in range(0, len(items), 16):
        group = items[k:k + 16]
        flags = 0
        for j, (ref, _) in enumerate(group):
            if ref:
                flags |= 1 << (15 - j)
        out += struct.pack('<H', flags)
        for _, words in group:
            for w in words:
                out += struct.pack('<H', w)
    return bytes(out)

def to_pixels(hw, width=256, height=16):
    """Halfwords (row-major 4bpp, 4 px per halfword) -> rows of indices."""
    rows = []
    per_row = width // 4
    for y in range(height):
        row = []
        for x in range(per_row):
            w = hw[y * per_row + x] if y * per_row + x < len(hw) else 0
            row += [(w >> (4 * k)) & 15 for k in range(4)]
        rows.append(row)
    return rows

def from_pixels(rows):
    hw = []
    for row in rows:
        for x in range(0, len(row), 4):
            hw.append(row[x] | row[x + 1] << 4 | row[x + 2] << 8 | row[x + 3] << 12)
    return hw
