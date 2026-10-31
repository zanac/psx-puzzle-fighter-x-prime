"""Zangief's win quotes on SPF2T's WINNER screen (arcade), from the user's
Pocket Fighter arcade set (sgemf).

SPF2T (English, a5+0x92 set): quote index = winner's character * 4 + random
0-3 (0xBC5A), text = 0x46834 + index * 136: two lines of 34 words, each word
the glyph's sprite code (ASCII | 0x80, '.' = 0x134, 0 = space; bit 15 marks
capitals and is ignored), the line count in a byte table. Zangief gets the
indexes 44-47 (code_quotes.s), with his text and line counts at ZQUOTES.

Pocket Fighter arcade: his four quotes at PF_QUOTES, each line a length word
then the characters as words 0x09xx (ASCII + 0x30), 0x0020 space, 0x0C63 ','
0x0C64 '.'; a 0 word after the second line."""
import struct

ZQUOTES = 0x9E000            # 4 quotes x 136 bytes, then 4 line counts (code_quotes.s)
PF_QUOTES = 0xD1584
LINE = 34
SPECIAL_PF = {0x0020: ' ', 0x0C63: ',', 0x0C64: '.'}
GLYPH = {' ': 0, '.': 0x134}

def pf_quotes(pfprog, addr=PF_QUOTES, n=4):
    W = lambda a: struct.unpack('>H', pfprog[a:a + 2])[0]
    out = []
    for _ in range(n):
        lines = []
        while True:
            ln = W(addr); addr += 2
            if ln == 0: break
            s = ''
            for i in range(ln):
                w = W(addr + 2 * i)
                if w >> 8 == 9: s += chr((w & 0xFF) - 0x30)
                elif w in SPECIAL_PF: s += SPECIAL_PF[w]
                else: raise SystemExit('Pocket Fighter quote: unknown code %04x at %x' % (w, addr + 2 * i))
            lines.append(s); addr += 2 * ln
        out.append(lines)
    return out

def glyph(c):
    if c in GLYPH: return GLYPH[c]
    if c == '"': c = "'"                 # the font has no double quote
    return (0x8000 if c.isupper() else 0) | ord(c) | 0x80

def line(s):
    s = s.strip()
    if len(s) > LINE: raise SystemExit('quote line too long: %r' % s)
    left = (LINE - len(s)) // 2
    s = ' ' * left + s + ' ' * (LINE - len(s) - left)
    return struct.pack('>%dH' % LINE, *[glyph(c) for c in s])

def build(pfprog):
    qs = pf_quotes(pfprog)
    text = b''.join(line(q[0]) + line(q[1] if len(q) > 1 else '') for q in qs)
    counts = bytes(len(q) for q in qs)
    return text + counts, qs
