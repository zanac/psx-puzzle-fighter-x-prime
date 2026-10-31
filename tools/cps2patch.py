"""Assemble 68000 patches in KScl's format and put them into a CPS2 ROM image.

A source file is a list of blocks, each one introduced by
    | !!! INSERT AT: <hex address>
    | !!! LENGTH: 0x<hex length>
and followed by GNU as (m68k) code or data. Each block is linked at its own
address, so absolute references (jsr label, lea label.l) work, also across
blocks and files: the labels of every block are visible to every other.
A block shorter than its LENGTH is padded with NOPs; a longer one is an error.

Needs binutils for m68k (m68k-linux-gnu-as/ld/objcopy/nm; the prefix can be
changed with the M68K_PREFIX environment variable)."""
import os, re, subprocess, tempfile, sys

PREFIX = os.environ.get('M68K_PREFIX', 'm68k-linux-gnu-')
STA = re.compile(r'^\s*\|\s*!!!\s*INSERT AT:\s*\$?(?:0x)?([0-9A-Fa-f]+)')
LEN = re.compile(r'^\s*\|\s*!!!\s*LENGTH:\s*\$?(?:0x)?([0-9A-Fa-f]+)')

def blocks(path):
    """[(address, length, text, origin)] of one source file"""
    out, cur = [], None
    for n, line in enumerate(open(path), 1):
        m = STA.match(line)
        if m:
            cur = [int(m.group(1), 16), None, [], '%s:%d' % (path, n)]; out.append(cur); continue
        m = LEN.match(line)
        if m and cur is not None and cur[1] is None:
            cur[1] = int(m.group(1), 16); continue
        if cur is not None:
            cur[2].append(line)
        elif line.strip() and not line.strip().startswith('|'):
            raise SystemExit('%s:%d: code before the first INSERT AT' % (path, n))
    for b in out:
        if b[1] is None: raise SystemExit('%s: block without LENGTH' % b[3])
    return [(a, l, ''.join(t), o) for a, l, t, o in out]

def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit('%s\n%s%s' % (' '.join(cmd), r.stdout, r.stderr))
    return r.stdout

def assemble(groups, include=()):
    """groups: {name: [source files]} -> {name: [(address, bytes big-endian)]}, symbols"""
    tmp = tempfile.mkdtemp(prefix='cps2patch')
    allb = []
    for g, files in groups.items():
        for f in files:
            for b in blocks(f): allb.append((g,) + b)
    objs = []
    for i, (g, a, l, text, o) in enumerate(allb):
        s = os.path.join(tmp, 'b%d.s' % i); ob = os.path.join(tmp, 'b%d.o' % i)
        open(s, 'w').write('.text\n.globl _start\n_start:\n' + text + '\n__blk_end:\n')
        cmd = [PREFIX + 'as', '-m68000', '-o', ob, s]
        for d in include: cmd += ['-I', d]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: raise SystemExit('%s:\n%s' % (o, r.stderr))
        _run([PREFIX + 'objcopy', '--set-section-alignment', '.text=2', ob])   # blocks start on any word
        objs.append(ob)
    # pass 1: link alone, collect every label's final address
    syms = {}
    for i, (g, a, l, text, o) in enumerate(allb):
        el = objs[i][:-2] + '.p1'
        _run([PREFIX + 'ld', '-Ttext=0x%x' % a, '--unresolved-symbols=ignore-all', '-o', el, objs[i]])
        own = set(n.split()[-1] for n in _run([PREFIX + 'nm', objs[i]]).splitlines() if n.split()[-2] in 'tT')
        for line in _run([PREFIX + 'nm', el]).splitlines():
            v, t, name = line.split()
            if name in own and name not in ('_start', '__blk_end') and not name.startswith('.'):
                if name in syms and syms[name][0] != int(v, 16):
                    raise SystemExit('label %s defined twice (%s)' % (name, o))
                syms[name] = (int(v, 16), o)
    # pass 2: link with the others' labels
    res = {g: [] for g in groups}
    for i, (g, a, l, text, o) in enumerate(allb):
        el = objs[i][:-2] + '.elf'; bn = objs[i][:-2] + '.bin'
        mine = set(n.split()[-1] for n in _run([PREFIX + 'nm', objs[i]]).splitlines() if n.split()[-2] in 'tT')
        cmd = [PREFIX + 'ld', '-Ttext=0x%x' % a, '-o', el, objs[i]]
        for n, (v, _) in syms.items():
            if n not in mine: cmd.append('--defsym=%s=0x%x' % (n, v))
        _run(cmd)
        _run([PREFIX + 'objcopy', '-O', 'binary', '-j', '.text', el, bn])
        data = open(bn, 'rb').read() if os.path.exists(bn) else b''
        nm = {x.split()[-1]: int(x.split()[0], 16) for x in _run([PREFIX + 'nm', el]).splitlines()}
        if nm['_start'] != a: raise SystemExit('%s: linked at %x, not %x' % (o, nm['_start'], a))
        data = data[:nm['__blk_end'] - a]
        if len(data) > l: raise SystemExit('%s: %d bytes, LENGTH is %d' % (o, len(data), l))
        if len(data) & 1: data += b'\x00'
        while len(data) < l: data += b'\x4e\x71'
        res[g].append((a, data[:l]))
    return res, {n: v for n, (v, _) in syms.items()}

def put(image, base, patches, swap=True):
    """write big-endian patch bytes into a ROM image that starts at `base`
    (swap=True: the image keeps little-endian words, as CPS2 program dumps do)"""
    image = bytearray(image)
    for a, d in patches:
        if swap: d = bytes(b for i in range(0, len(d), 2) for b in (d[i + 1], d[i]))
        o = a - base
        assert 0 <= o and o + len(d) <= len(image), hex(a)
        image[o:o + len(d)] = d
    return bytes(image)
