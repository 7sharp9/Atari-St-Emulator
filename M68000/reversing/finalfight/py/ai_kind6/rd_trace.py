#!/usr/bin/env python3
"""Recursive-descent listing of the 68000 program ROM from entry points, following bra/bcc/dbf/bsr/jsr/jmp
and the word-offset dispatch idioms (`move.w d(PC,Dn.w),D1 / jmp|jsr e(PC,D1.w) == $T+D1`).
usage: rd_trace.py <lo> <hi> <entry>...   (lists only addresses in [lo,hi); prints external targets at the end)"""
import sys, re, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import disassemble as D
rom = open(os.path.join(ROOT, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = D.Disassembler(rom, rom_base=0)
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
entries = [int(a, 16) for a in sys.argv[3:]]
limits = {}
absre = re.compile(r'^(bra|bsr|b[a-z]{2}|db[a-z]{1,2} D\d,|jmp|jsr)\.?[a-z]? ?(?:D\d,)?\$([0-9a-f]+)(\.w|\.l)?$')
def tgt(text):
    m = re.match(r'^(?:b[a-z]{2}|bsr|bra|dbf|dbra|db[a-z]{2})[.a-z]* (?:D\d,)?\$([0-9a-f]+)$', text)
    if m: return int(m.group(1), 16)
    m = re.match(r'^(?:jmp|jsr) \$([0-9a-f]+)(?:\.w|\.l)?$', text)
    if m: return int(m.group(1), 16)
    return None
def table_entries(t):
    lim = limits.get(t, 999)
    # entries relative to t, count unknown: scan until we reach the smallest entry offset
    ents = []
    mn = 1 << 30
    i = 0
    while t + 2*i < t + mn and i < lim:
        v = int.from_bytes(rom[t+2*i:t+2*i+2], 'big')
        sv = v - 0x10000 if v & 0x8000 else v
        if abs(sv) > 0x7000: break
        ents.append(t + sv)
        if sv > 0: mn = min(mn, sv)
        i += 1
    return ents
def run():
    global seen, ext, tables, labels
    seen = {}
    ext = {}
    tables = {}
    work = list(entries)
    labels = set(entries)
    while work:
        a = work.pop()
        while True:
            if a in seen: break
            if a < 0 or a >= len(rom) or a & 1: break
            try:
                text, nxt = dis.decode_one(a)
            except Exception as e:
                break
            if '???' in text or 'unknown' in text or text.startswith('<'):
                seen[a] = (text, nxt); break
            seen[a] = (text, nxt)
            t = tgt(text)
            if t is not None:
                if lo <= t < hi:
                    labels.add(t); work.append(t)
                else:
                    ext.setdefault(t, set()).add(a)
            m = re.search(r'== \$([0-9a-f]+)\+D', text)
            if m and (text.startswith('jmp') or text.startswith('jsr')):
                T = int(m.group(1), 16)
                ents = table_entries(T)
                tables[T] = ents
                for e in ents:
                    if lo <= e < hi: labels.add(e); work.append(e)
                    else: ext.setdefault(e, set()).add(a)
            if text.startswith(('rts', 'rte', 'jmp', 'bra', 'illegal')) and not text.startswith('jmp') :
                break
            if text.startswith('jmp'): break
            if text.startswith('bra'): break
            a = nxt


for _ in range(10):
    run()
    ch = False
    for T, ents in tables.items():
        cands = [a for a in seen if a > T and a < T + 2*len(ents) + 2]
        if cands:
            lim = (min(cands) - T)//2
            if limits.get(T, 999) > lim:
                limits[T] = lim; ch = True
    if not ch: break
for T, ents in sorted(tables.items()):
    print('; table $%x: %s' % (T, ' '.join('%x' % e for e in ents)))
last_end = None
for a in sorted(seen):
    if not (lo <= a < hi): continue
    text, nxt = seen[a]
    if last_end is not None and a != last_end: print()
    print('%s$%06x: %s' % ('L' if a in labels else ' ', a, text))
    last_end = nxt
print('; external targets:')
for t in sorted(ext): print(';  $%x from %s' % (t, ' '.join('%x' % x for x in sorted(ext[t])[:6])))
