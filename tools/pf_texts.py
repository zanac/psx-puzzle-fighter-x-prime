#!/usr/bin/env python3
"""Pocket Fighter (SLUS-00653) texts, decoded from your own disc: win quotes,
the rival dialogues of Arcade mode and each character's Arcade story
(opening and ending), as Markdown.

Formats (see docs/NEW-CHARACTER-RESEARCH.md, "Pocket Fighter texts"):
- the text is not ASCII: each byte is a glyph index into a 16x16 4bpp glyph
  strip (128 bytes per glyph; 0 = space, 1-2 = prompt icons). GLYPHS below
  lists, for each strip, the letter of every index (read off the glyphs; no
  glyph data is stored here).
- win quotes: MDL/SELMES.MDL from offset 4, lines of (0x80 | length, glyphs)
  (bytes below 0x80 between them are skipped),
  two lines per quote, 4 quotes per character in character order, then
  the gameplay tips; strip: STAGE/SELECT.PAC, first entry.
- rival dialogue: MDL/PLxxA.MDL, messages of (length, glyphs), length a
  multiple of 38 (38 characters per line); strip PLAYER/BMESxx.PAC.
- story: MDL/ENDING.MDL, the same messages for all characters in order
  (opening, then ending); strip STAGE/OPENxx.PAC type 269 (= ENDxx 270).
Character order: Ryu, Ken, Chun-Li, Sakura, Morrigan, Hsien-Ko, Felicia,
Tessa, Ibuki, Zangief, Dan, Akuma (xx = 00..0B).

usage: pf_texts.py PF_IMAGE OUT.md
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

NAMES = ['Ryu', 'Ken', 'Chun-Li', 'Sakura', 'Morrigan', 'Hsien-Ko', 'Felicia',
         'Tessa', 'Ibuki', 'Zangief', 'Dan', 'Akuma']
STORY = [0xEBBC, 0x10BD8, 0x11024, 0x114B8, 0x11974, 0x11D6C, 0x12204,
         0x126B8, 0x12AD0, 0x12F5C, 0x133F4, 0x13950, 0x13E50]   # ENDING.MDL
GLYPHS = {
    'OPEN00': " ~~Ryucontieshqbmarw.N,ldTHgjSkfvIYWL”zA'p!?G(B)O",
    'BMES00': " ~~AreyouTsa?Iwntlmhgfi.vbcY'RpqS,dkWV!",
    'OPEN01': " ~~KencotiushragAm.BywElzd'vbfI,kpMC!?JOLx(S)WjTH:q",
    'BMES01': " ~~HeythrMoigan!Isdvcupfwm?WB,b'lkST.",
    'OPEN02': " ~~Thepolicwman,Cu-Lsvrybf.Hxt”S!kdgW?AzI'qjRNPOF",
    'BMES02': " ~~Thatmusbenilrwyfoz.Wg?Ycvp'Lk,dP!S",
    'OPEN03': " ~~HeySakur!mvctionswWhgd?Ip'lfMbYD,LNjR.AB()",
    'BMES03': " ~~Ryu!I'vefinalodLtsghHSkrbw.D?,mpcO()",
    'OPEN04': " ~~IsthiefamouCn-L?!S'blwdr,Mgkpczv.A”yYNFRW—BHq",
    'BMES04': " ~~HowilIevrfndthaCu-L.c,'ksm!NgMSGpy?AbUOYWP",
    'OPEN05': " ~~HsienkoadLrchftDl.Buby,mTwgp-j!I?W'”3O2vZNzC1SRP",
    'BMES05': ' ~~Soyuarethnfigkljb?HmO,cp-.Dw3sd!BIv',
    'OPEN06': " ~~ThemusicaltFprfodnbg!SI'kvw.,yAjKYNGMPBOC?WH”D",
    'BMES06': " ~~Heryoua,Kn!Clditcmshv?I'kpA.wbfg",
    'OPEN07': " ~~Tesaidvotunfmgc.y,hrwbkH?”IlS'p!AjLBWR30C",
    'BMES07': " ~~I'vefinalyoud!Gmthsckrw,b.gA?W",
    'OPEN08': " ~~EatingcermHjuksodlf!IwhvTy.b,'pANUSBGCY;OxW?",
    'BMES08': " ~~Excusem!DoyknwhrIafidtpHj?WYbNlOg'.B",
    'OPEN09': " ~~ZangiefsthmroRuwld.Apv,kFcYyb!LBxI-O'GCTjNPzH",
    'BMES09': " ~~YoumstbeFlica.Ihvkyprfnd!',MW?Owjg",
    'OPEN0A': " ~~Upondecighwastrl'f,DSky.Imub!YjAWvN?MTGLO”B",
    'BMES0A': " ~~Ohapyd!I'vecosnutbfirmSklg,?MwW.",
    'OPEN0B': " ~~AkumatrinsedlyghofG.U,cvxM!TbIpwjOD'?WCHzq",
    'BMES0B': " ~~Areyouthnsacigfwd?Ikblp.m!LvO,'YTHV;",
    'SELECT': " ~~Awariohkepsfgtndmvluy.~Ic!b?SBY'TO,EqjNDMLCHWx”zRP+K-~~~G",
}

def disc_file(img, path):
    import discpatch as D
    lba, size = D.iso_find(img, path)
    return D.iso_read(img, lba, size)

def decode(b, glyphs):
    return ''.join(glyphs[x] if x < len(glyphs) else '~' for x in b)

def lines38(t):
    rows = [t[i:i + 38].rstrip() for i in range(0, len(t), 38)]
    return ' / '.join(r for r in rows if r)

def messages(d, start, end):
    """(length, glyphs) messages, length a multiple of 38"""
    p, out = start, []
    while p < min(end, len(d)):
        n = d[p]
        if n and n % 38 == 0 and n <= 190 and p + 1 + n <= len(d) and \
                all(x < 64 for x in d[p + 1:p + 1 + n]):
            out.append(d[p + 1:p + 1 + n])
            p += 1 + n
        else:
            p += 1
    return out

def win_quotes(selmes):
    p, lines = 4, []
    while p < len(selmes) and len(lines) < 96:
        if selmes[p] < 0x80:                # (padding between lines)
            p += 1
            continue
        n = selmes[p] & 0x7F
        lines.append(decode(selmes[p + 1:p + 1 + n], GLYPHS['SELECT']).strip())
        p += 1 + n
    return [lines[i] + ' / ' + lines[i + 1] for i in range(0, 96, 2)]

def main(image, out):
    import discout
    img = discout.load(image).img
    md = ['# Pocket Fighter texts', '',
          'Decoded from the disc by `tools/pf_texts.py` (not stored in the repository).', '']
    quotes = win_quotes(disc_file(img, '/MDL/SELMES.MDL'))
    ending = disc_file(img, '/MDL/ENDING.MDL')
    for c, name in enumerate(NAMES):
        md += ['## %s' % name, '', '### Win quotes', '']
        md += ['%d. %s' % (i + 1, q) for i, q in enumerate(quotes[c * 4:c * 4 + 4])]
        mdl = disc_file(img, '/MDL/PL%02XA.MDL' % c)
        rival = [m for m in messages(mdl, 0, len(mdl))
                 if '~' not in decode(m, GLYPHS['BMES%02X' % c])[:4]]
        md += ['', '### Arcade: rival dialogue', '']
        md += ['- %s' % lines38(decode(m, GLYPHS['BMES%02X' % c])) for m in rival[-4:]]
        md += ['', '### Arcade: story (opening, then ending)', '']
        story = messages(ending, STORY[c], STORY[c + 1])
        md += ['- %s' % lines38(decode(m, GLYPHS['OPEN%02X' % c])) for m in story]
        md.append('')
    open(out, 'w').write('\n'.join(md) + '\n')
    print('%s: %d characters' % (out, len(NAMES)))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
