"""deadblocks.py - instruction-level flow reachability inside TEXT (ss.asm), starting from every function node that
reach.py finds reachable (plus all call/pointer targets). Lists maximal unreachable instruction ranges = orphan blocks,
e.g. code after an unconditional return that nothing branches to.  Data tables in TEXT decode as junk and show up here too."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
from reach import TEXT0, TEXT1

def main():
    ins = reach.load(); th = reach.thunks()
    idx = {a: i for i, (a, t) in enumerate(ins)}
    entries = set()
    for a, t in ins:
        for k, v in reach.refs_of(a, t, th):
            if k == 'thunk':
                if v in th: entries.add(th[v])
            elif k != 'local' and TEXT0 <= v < TEXT1:
                entries.add(v)
    entries.add(0xA562)
    # exclude the thunk table's own jmp.l edges (entries only via users) -- approximated: keep all, dead nodes reported by reach.py
    seen = set()
    work = sorted(entries)
    ender = ('rts', 'rte', 'bra', 'jmp', 'rtr')
    while work:
        a = work.pop()
        while a in idx and a not in seen:
            seen.add(a)
            t = ins[idx[a]][1]
            mn = t.split()[0]
            for k, v in reach.refs_of(a, t, th):
                if k in ('direct', 'local') and TEXT0 <= v < TEXT1 and v not in seen:
                    work.append(v)
                if k in ('pcrel',) and mn in ('jsr', 'bsr') and v not in seen:
                    work.append(v)
            if mn in ender:
                break
            i = idx[a] + 1
            if i >= len(ins): break
            a = ins[i][0]
    # report maximal unreached runs
    runs = []; cur = None
    for a, t in ins:
        if a in seen:
            if cur: runs.append(cur); cur = None
        else:
            if cur: cur[1] = a
            else: cur = [a, a]
    if cur: runs.append(cur)
    tot = 0
    for lo, hi in runs:
        # skip run made only of ori.b/nop junk
        body = [t for a, t in ins if lo <= a <= hi]
        junk = sum(1 for t in body if t.startswith(('ori.b #$0,D0', 'nop')))
        print('%06x-%06x insns %3d junk %3d %s' % (lo, hi, len(body), junk, body[0]))
        tot += 1
    print('runs', tot)

main()
