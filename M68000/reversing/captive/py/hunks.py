#!/usr/bin/env python3
"""Amiga hunk executables in Captive's file system: parse, and align against a RAM snapshot.

Usage (from M68000/):
  uv run python reversing/captive/py/hunks.py <file> [<snap>]

Prints each hunk (type, size, relocation count). With a snapshot, finds where each CODE/DATA hunk
sits in RAM: it anchors on 16-byte windows of the file that contain no relocated long, and
reports the base with the most anchors and the byte match over the whole hunk once the
relocations are applied with the bases found for the hunks they point into.
"""
import os
import struct
import sys

HUNK = {0x3E9: 'CODE', 0x3EA: 'DATA', 0x3EB: 'BSS', 0x3EC: 'RELOC32', 0x3F0: 'SYMBOL',
        0x3F1: 'DEBUG', 0x3F2: 'END', 0x3F3: 'HEADER'}


def parse(b):
    """Return [{'type','data','size','relocs':{target_hunk:[offsets]}}] in hunk order."""
    p = 0

    def L():
        nonlocal p
        v = struct.unpack('>I', b[p:p + 4])[0]
        p += 4
        return v

    if L() != 0x3F3:
        raise ValueError('not a hunk file')
    while L():          # resident library names (none expected)
        pass
    n, first, last = L(), L(), L()
    sizes = [L() & 0x3FFFFFFF for _ in range(last - first + 1)]
    hunks, cur = [], None
    while p < len(b):
        t = L() & 0x3FFFFFFF
        if t in (0x3E9, 0x3EA):
            nl = L()
            cur = {'type': HUNK[t], 'data': b[p:p + nl * 4], 'size': sizes[len(hunks)] * 4,
                   'relocs': {}}
            p += nl * 4
            hunks.append(cur)
        elif t == 0x3EB:
            L()
            cur = {'type': 'BSS', 'data': b'', 'size': sizes[len(hunks)] * 4, 'relocs': {}}
            hunks.append(cur)
        elif t == 0x3EC:
            while True:
                k = L()
                if not k:
                    break
                tgt = L()
                cur['relocs'].setdefault(tgt, []).extend(L() for _ in range(k))
        elif t == 0x3F0:
            while True:
                k = L()
                if not k:
                    break
                p += k * 4 + 4
        elif t == 0x3F1:
            p += L() * 4
        elif t == 0x3F2:
            continue
        else:
            raise ValueError('hunk type $%x at %d' % (t, p - 4))
    return hunks


def align(hunks, ram):
    bases = []
    for h in hunks:
        d = h['data']
        if not d:
            bases.append(None)
            continue
        bad = set()
        for offs in h['relocs'].values():
            for o in offs:
                bad.update(range(o, o + 4))
        votes = {}
        for o in range(0, len(d) - 16, 16):
            if any(x in bad for x in range(o, o + 16)) or len(set(d[o:o + 16])) < 4:
                continue
            i = ram.find(d[o:o + 16])
            while i >= 0:
                votes[i - o] = votes.get(i - o, 0) + 1
                i = ram.find(d[o:o + 16], i + 1)
        bases.append(max(votes, key=votes.get) if votes else None)
    out = []
    for h, base in zip(hunks, bases):
        if base is None:
            out.append((h, None, 0, 0))
            continue
        d = bytearray(h['data'])
        for tgt, offs in h['relocs'].items():
            if bases[tgt] is None:
                continue
            for o in offs:
                v = struct.unpack('>I', d[o:o + 4])[0]
                d[o:o + 4] = struct.pack('>I', (v + bases[tgt]) & 0xFFFFFFFF)
        same = sum(1 for i, x in enumerate(d) if base + i < len(ram) and ram[base + i] == x)
        out.append((h, base, same, len(d)))
    return out


def main():
    b = open(sys.argv[1], 'rb').read()
    hunks = parse(b)
    if len(sys.argv) < 3:
        for i, h in enumerate(hunks):
            print('%d %-4s size $%06x data $%06x relocs %s' % (
                i, h['type'], h['size'], len(h['data']),
                {k: len(v) for k, v in h['relocs'].items()}))
        return
    root = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(root, 'tools', 'rdis.py')):
        root = os.path.dirname(root)
    sys.path.insert(0, os.path.join(root, 'tools'))
    from gfxview import load_ram
    ram, _ = load_ram(sys.argv[2])
    for i, (h, base, same, n) in enumerate(align(hunks, ram)):
        print('%d %-4s size $%06x relocs %4d  base %s  match %d/%d' % (
            i, h['type'], h['size'], sum(len(v) for v in h['relocs'].values()),
            '$%06x' % base if base is not None else '-', same, n))


if __name__ == '__main__':
    main()
