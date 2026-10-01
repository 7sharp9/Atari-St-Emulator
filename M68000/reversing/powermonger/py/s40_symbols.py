"""s40_symbols.py - the original developer symbol table hidden in DATA\\SPRITE40.DAT.

`DATA\\SPRITE40.DAT` on the PowerMonger disk is not sprite data: it is a self-extracting GEMDOS
program, the same game build as the loaded image, with its linker symbol table (1639 entries,
names truncated to 8 characters, DRI format). This script unpacks it, finds the load offset by
aligning its text against a loaded RAM image, and writes `powermonger_orig.sym`.

    cd M68000 && python reversing/powermonger/py/s40_symbols.py [disk.st] [ram.snap|ram.ram]

Defaults: scratchpad/powermonger.st, scratchpad/pm123/win/m1_s0.snap. Working files go to
scratchpad/pm133/ (the game's files are commercial). Output: reversing/powermonger/powermonger_orig.sym
(addr<TAB>name; kind T text, D data, B bss as a trailing comment) and, with `--check`, the
alignment statistics only.

The unpacker is a port of the stub at SPRITE40.DAT $1c..$ba (bit-tree depacker, run-length escape
$f100). The stub's own relocation pass is not needed: the inner program is read as a file.
"""
import collections
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))      # M68000/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap  # noqa: E402

OUT_SYM = os.path.join(ROOT, 'reversing', 'powermonger', 'powermonger_orig.sym')
WORK = os.path.join(ROOT, 'scratchpad', 'pm133')


def read_fat12_file(img, want):
    """Return the bytes of `want` (a path like DATA/SPRITE40.DAT) from a FAT12 .ST image."""
    d = open(img, 'rb').read()
    bps = struct.unpack_from('<H', d, 0x0B)[0]
    spc, rsv, nfat = d[0x0D], struct.unpack_from('<H', d, 0x0E)[0], d[0x10]
    nroot, spf = struct.unpack_from('<H', d, 0x11)[0], struct.unpack_from('<H', d, 0x16)[0]
    fat = d[rsv * bps:(rsv + spf) * bps]
    root = (rsv + nfat * spf) * bps
    data0 = root + nroot * 32
    cl = bps * spc

    def nxt(c):
        o = c * 3 // 2
        v = fat[o] | (fat[o + 1] << 8)
        return (v >> 4) if c & 1 else (v & 0xFFF)

    def chain(c, size=None):
        b = bytearray()
        while 2 <= c < 0xFF8:
            o = data0 + (c - 2) * cl
            b += d[o:o + cl]
            c = nxt(c)
        return bytes(b if size is None else b[:size])

    def find(raw, parts):
        for i in range(0, len(raw), 32):
            e = raw[i:i + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] & 0x08 or e[0] == 0x2E:
                continue
            name = e[:8].decode('ascii', 'replace').strip()
            ext = e[8:11].decode('ascii', 'replace').strip()
            fn = name + ('.' + ext if ext else '')
            c, size = struct.unpack_from('<H', e, 26)[0], struct.unpack_from('<I', e, 28)[0]
            if fn.upper() != parts[0]:
                continue
            if len(parts) == 1:
                return chain(c, size)
            return find(chain(c), parts[1:])
        raise FileNotFoundError(want)

    return find(d[root:root + nroot * 32], want.upper().replace('\\', '/').split('/'))


def unpack(f):
    """Depack the program inside SPRITE40.DAT (the stub's bit-tree + $f100 run-length scheme)."""
    t = bytearray(f[28:])                       # the stub addresses are relative to the text start
    L = lambda a: struct.unpack('>I', t[a:a + 4])[0]
    W = lambda a: struct.unpack('>H', t[a:a + 2])[0]
    a3 = 0x13a                                  # lea 308(PC),A0 at $4
    a0 = a3 + W(a3 + 2) + 4
    packed, orig = L(a0), L(a0 + 4)
    a0 += 8
    a2 = a0 + orig + 0x100
    a0 += packed
    t.extend(bytearray(max(0, a2 - len(t) + 8)))
    tree = a3 + 4
    a0 -= 1
    d1, d2, d3, d0 = t[a0], 0, 7, orig
    while True:
        a4 = tree
        while True:                             # walk the tree one bit at a time
            d1 <<= 1
            if d1 & 0x100:
                a4 += 2
            d1 &= 0xff
            if d3 == 0:
                d3 = 7
                a0 -= 1
                d1 = t[a0]
            else:
                d3 -= 1
            d4 = W(a4)
            if d4 & 0x8000:
                break
            a4 += d4
        if d2 & 0x80:                           # run: repeat the last written byte
            d2 = (d2 + d4) & 0xff
            d0 -= d2
            b = t[a2]
            for _ in range(d2 + 1):
                a2 -= 1
                t[a2] = b
            d2 = 0
        elif d4 == 0xf100:                      # escape: next symbol is a run length
            d2 = (d2 - 1) & 0xff
            continue
        else:
            a2 -= 1
            t[a2] = d4 & 0xff
            d2 = 0
        d0 -= 1
        if d0 == 0:
            return bytes(t[a2:a2 + orig])


def symbols(prg):
    magic, tl, dl, bl, sl = struct.unpack('>HIIII', prg[:18])
    assert magic == 0x601a, hex(magic)
    sym = prg[28 + tl + dl:28 + tl + dl + sl]
    out, i = [], 0
    while i + 14 <= len(sym):
        name = sym[i:i + 8].rstrip(b'\0').decode('latin1')
        typ, val = struct.unpack('>HI', sym[i + 8:i + 14])
        i += 14
        out.append((name, typ, val))
    assert i == sl
    return out, tl


def load_offset(txt, ram, w=16):
    """The constant `runtime - text offset`, voted over every unique 16-byte window."""
    idx = collections.defaultdict(list)
    for j in range(0, 0x58000 - w, 2):
        idx[ram[j:j + w]].append(j)
    votes = collections.Counter()
    for i in range(0, len(txt) - w, 2):
        hit = idx.get(txt[i:i + w])
        if hit and len(hit) == 1:
            votes[hit[0] - i] += 1
    (delta, n), = votes.most_common(1)
    return delta, n, sum(votes.values())


def main(argv):
    check = '--check' in argv
    argv = [a for a in argv if a != '--check']
    img = argv[0] if argv else os.path.join(ROOT, 'scratchpad', 'powermonger.st')
    snap = argv[1] if len(argv) > 1 else os.path.join(ROOT, 'scratchpad', 'pm123', 'win', 'm1_s0.snap')
    f = read_fat12_file(img, 'DATA/SPRITE40.DAT')
    prg = unpack(f)
    os.makedirs(WORK, exist_ok=True)
    open(os.path.join(WORK, 'sprite40_inner.prg'), 'wb').write(prg)
    syms, tl = symbols(prg)
    ram = ram_from_snap(snap) if snap.endswith('.snap') else open(snap, 'rb').read()
    txt = prg[28:28 + tl]
    delta, n, tot = load_offset(txt, ram)
    print(f'SPRITE40.DAT {len(f)} bytes -> inner program {len(prg)} bytes, {len(syms)} symbols')
    print(f'load offset ${delta:x}: {n} of {tot} unique 16-byte text windows agree ({100 * n / tot:.1f} %)')
    assert n / tot > 0.99, 'text does not align with the loaded image: wrong snapshot or build'
    if check:
        return
    dl = struct.unpack('>I', prg[6:10])[0]
    base = {0xa200: delta, 0xa400: delta + tl, 0xa100: delta + tl + dl}   # text, data, bss section bases
    seen, rows = set(), []
    for name, typ, val in syms:
        if (name, typ, val) in seen:
            continue
        seen.add((name, typ, val))
        kind = {0xa200: 'T', 0xa100: 'B', 0xa400: 'D'}[typ]
        rows.append((val + base[typ], name, kind))
    rows.sort()
    with open(OUT_SYM, 'w', encoding='utf-8', newline='\n') as o:
        o.write('# PowerMonger original developer symbols, from DATA\\SPRITE40.DAT (py/s40_symbols.py).\n')
        o.write('# addr<TAB>name; runtime addresses (SPRITE40 text offset + $%x). Names are the linker\'s\n' % delta)
        o.write('# 8-character truncations, so two routines can share a name. T = text, D = data, B = bss.\n')
        o.write('# Data and bss symbol values are section-relative: runtime = value + section base.\n')
        for a, name, kind in rows:
            o.write('%06x\t%s\t# %s\n' % (a, name, kind))
    print(f'wrote {OUT_SYM}: {len(rows)} unique symbols')


if __name__ == '__main__':
    main(sys.argv[1:])
