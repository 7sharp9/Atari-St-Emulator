"""Whole-RAM census of the decoded instructions that write (or, with --all, also read) a field given
as `N(An)` (e.g. "2518(A5)") or as an absolute address ("$6c2a"), to find its writers directly instead
of tracing call chains by hand (worked examples: 2455(A5) and 2518(A5) in
M68000/reversing/cadaver/mechanics.md).

It decodes with tools/disassemble.py and matches operands, not text:
  - an operand matches when the bytes it accesses overlap the field, so `move.l D0,2516(A5)` is a writer
    of byte 2518(A5), and `2518(A5)` no longer matches `12518(A5)`;
  - the access width comes from the size suffix (.b/.w/.l; Scc, TAS, NBCD and bit ops on memory are
    bytes, MOVEM is 2 or 4 bytes per register in its mask);
  - the destination is the last operand; CMP/TST/BTST/CHK/LEA/PEA never write;
  - hits are split by instruction boundary: a linear sweep from --start that steps by each instruction's
    decoded length (and by 2 over undecodable words) gives the instruction starts. A hit at any other
    even address is listed separately: it is a decode of data or of the middle of an instruction.

What it cannot see (so a clean result here is not "nothing writes X" by itself; CLAUDE.md "Evidence rules"):
  - writes through a pointer: `lea 2400(A5),A0` then a `clr.l (A0)+` loop or `movem.l D0-D7,(A0)` (block
    clears and copies from a lower base). The "address taken" list shows every LEA/PEA/MOVEA of an
    address in the same An frame within --near bytes below the field, as candidates to read by hand;
  - indexed operands N(An,Xn): the index is a run-time value. Listed as "indexed, may cover";
  - code outside the image (ROM, overlays loaded later), self-modifying code, longword jump tables a linear
    sweep desynchronises on (a hit in the off-boundary list may be real code there), and FDC DMA;
  - absolute fields: only $xxxx.w / $xxxxxx.l operands, not a pointer that happens to hold the address.
Confirm a negative with the emulator: `watch <addr> <len>` reports any write covering the range, DMA included.

Usage: python find_field_writers.py <snap> "<field>" [--width N] [--all] [--start HEX] [--end HEX] [--near N]
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disassemble import Disassembler, ram_from_snap  # noqa: E402

NOWRITE = ('cmp', 'tst', 'btst', 'chk', 'lea', 'pea', 'bra', 'bsr', 'jmp', 'jsr', 'db')
BYTE_OPS = ('s', 'tas', 'nbcd', 'bset', 'bclr', 'bchg', 'btst')
SCC = {'st', 'sf', 'shi', 'sls', 'scc', 'scs', 'sne', 'seq', 'svc', 'svs', 'spl', 'smi', 'sge', 'slt', 'sgt', 'sle'}


def split_ops(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur:
        out.append(cur)
    return [o.strip() for o in out]


def width_of(mn, ops):
    base = mn.split('.')[0]
    if mn.startswith('movem'):
        m = re.search(r'#\$([0-9a-f]+)', ' '.join(ops))
        n = bin(int(m.group(1), 16)).count('1') if m else 16
        return n * (4 if mn.endswith('.l') else 2)
    if base in SCC or base in BYTE_OPS:
        return 1
    if mn.endswith('.b'):
        return 1
    if mn.endswith('.w'):
        return 2
    if mn.endswith('.l'):
        return 4
    return 2


def parse_field(f):
    m = re.fullmatch(r'\s*(-?\d+)\((A\d)\)\s*', f, re.I)
    if m:
        return ('disp', m.group(2).upper(), int(m.group(1)))
    m = re.fullmatch(r'\s*\$?([0-9a-fA-F]+)\s*', f)
    if m:
        return ('abs', None, int(m.group(1), 16) & 0xffffff)
    sys.exit(f'field must be N(An) or $hex, got {f!r}')


def classify_operand(op, kind, reg):
    """-> ('exact', start) | ('indexed', disp8) | None for an operand in the field's addressing frame"""
    if kind == 'disp':
        m = re.fullmatch(r'(-?\d+)\((A\d)\)', op)
        if m and m.group(2) == reg:
            return ('exact', int(m.group(1)))
        if op == f'({reg})' or op == f'({reg})+' or op == f'-({reg})':
            return ('exact', 0) if op == f'({reg})' else None
        m = re.fullmatch(r'(-?\d+)\((A\d),[AD]\d\.[wl]\)', op)
        if m and m.group(2) == reg:
            return ('indexed', int(m.group(1)))
        return None
    m = re.fullmatch(r'\$([0-9a-f]+)\.([wl])', op)
    if m:
        v = int(m.group(1), 16)
        if m.group(2) == 'w' and v & 0x8000:
            v |= 0xff0000
        return ('exact', v & 0xffffff)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('snap')
    ap.add_argument('field')
    ap.add_argument('--width', type=int, default=1, help='field width in bytes (default 1)')
    ap.add_argument('--all', action='store_true', help='also list reads')
    ap.add_argument('--start', type=lambda v: int(v, 16), default=0x8, help='sweep start (hex, default 8)')
    ap.add_argument('--end', type=lambda v: int(v, 16), default=None, help='sweep end (hex, default end of RAM)')
    ap.add_argument('--near', type=int, default=4096, help='address-taken window below the field (bytes)')
    ap.add_argument('--max', type=int, default=40, help='rows shown per secondary list (default 40)')
    a = ap.parse_args()

    kind, reg, fstart = parse_field(a.field)
    flo, fhi = fstart, fstart + a.width - 1
    ram = ram_from_snap(a.snap)
    dis = Disassembler(ram, rom_base=0)
    end = min(a.end if a.end is not None else len(ram), len(ram)) - 10

    def decode(addr):
        try:
            text, nxt = dis.decode_one(addr)
        except (IndexError, KeyError):
            return None
        if '???' in text or nxt <= addr:
            return None
        return text, nxt

    # linear sweep: instruction starts
    starts = set()
    addr = a.start & ~1
    while addr < end:
        d = decode(addr)
        if d is None:
            addr += 2
            continue
        starts.add(addr)
        addr = d[1]

    writers, readers, indexed, taken, off = [], [], [], [], []
    for addr in range(a.start & ~1, end, 2):
        d = decode(addr)
        if d is None:
            continue
        text = d[0]
        if '?' in text:
            continue   # the decoder marks guesses (`ori?`, `tas ea?`) with '?': not evidence either way
        mn, _, rest = text.partition(' ')
        ops = split_ops(rest.split(' == ')[0]) if rest else []
        w = width_of(mn, ops)
        base = mn.split('.')[0]
        found = None
        for i, op in enumerate(ops):
            c = classify_operand(op, kind, reg)
            if c is None:
                continue
            if base in ('lea', 'pea'):
                if flo - a.near <= c[1] <= fhi:
                    found = ('taken', i, flo - c[1])
                continue
            if c[0] == 'indexed':
                if i == len(ops) - 1 and not base.startswith(NOWRITE) and not (mn.startswith('movem') and i == 0):
                    found = found or ('indexed', i)
                continue
            lo, hi = c[1], c[1] + w - 1
            if lo <= fhi and hi >= flo:
                is_dst = (i == len(ops) - 1) and len(ops) >= 1 and not base.startswith(NOWRITE)
                if mn.startswith('movem') and i == 0:
                    is_dst = False   # movem <ea>,#mask is a load into registers
                found = ('write' if is_dst else 'read', i)
        if not found:
            continue
        row = (addr, text)
        if addr not in starts:
            off.append((found[0],) + row)
        elif found[0] == 'write':
            writers.append(row)
        elif found[0] == 'read':
            readers.append(row)
        elif found[0] == 'indexed':
            indexed.append(row)
        else:
            taken.append((found[2],) + row)

    fld = a.field + (f' (+{a.width} bytes)' if a.width > 1 else '')
    print(f'=== {fld}: {len(writers)} writer(s) on instruction boundaries (sweep ${a.start:06x}-${end:06x}) ===')
    for r in writers:
        print(f'  ${r[0]:06x}: {r[1]}')
    if a.all:
        print(f'=== reads ({len(readers)}) ===')
        for r in readers:
            print(f'  ${r[0]:06x}: {r[1]}')
    cap = a.max
    def more(n):
        if n > cap:
            print(f'  ... {n - cap} more (--max)')
    print(f'=== indexed writes through the same base, may cover ({len(indexed)}) ===')
    for r in indexed[:cap]:
        print(f'  ${r[0]:06x}: {r[1]}')
    more(len(indexed))
    taken.sort()
    print(f'=== address taken within {a.near} bytes below the field, nearest first (block clear/copy bases to read by hand) ({len(taken)}) ===')
    for r in taken[:cap]:
        print(f'  ${r[1]:06x}: {r[2]}    (field - {r[0]})')
    more(len(taken))
    offw = [r for r in off if r[0] == 'write']
    print(f'=== writes off the sweep boundary: data or mid-instruction decodes, or code a linear sweep missed ({len(offw)}) ===')
    for r in offw[:cap]:
        print(f'  ${r[1]:06x}: {r[2]}')
    more(len(offw))
    print('not visible here: writes through computed pointers (see "address taken"), code outside this image, '
          'self-modifying code, FDC DMA. Confirm a negative with `watch`.')


if __name__ == '__main__':
    main()
