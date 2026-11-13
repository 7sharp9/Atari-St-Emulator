"""Gate the creature scheduler $102a0 (cr_UpdateAll) on a natural run: sched.py <snap> <frames>

Runs the snapshot with no pokes, stopping at every $102a0 entry (one main frame) and every $10304 (cr_GroupThink)
entry. At each frame start it reads every group's timer (+6) and period (+7) and predicts, from $102de-$102fa, that
the group thinks this frame iff timer > period. The observed set is the A0 values of the $10304 entries before the
next $102a0. Prints the match count over group-frames, the main-frame length in steps (min, median, max) and, per
group that thought at least twice, its intervals in frames with the timer it was left at after each think."""
import os, sys, struct, statistics; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *

UPD, THINK = 0x102a0, 0x10304

def groups(s):
    blob = s.read(A6 + 4532, 0x1000); out = []; a = 0
    while True:
        sz = struct.unpack('>h', blob[a + 2:a + 4])[0]
        if sz < 0: return out
        out.append((A6 + 4532 + a, blob[a + 6], blob[a + 7]))
        a += sz

def pc(r): return int(r['pc'].lstrip('$'), 16)

def main():
    s = srv(sys.argv[1]); frames = int(sys.argv[2])
    r = s('run', max_steps=2_000_000, until_pc=[UPD])
    assert pc(r) == UPD, r
    steps = [r['step']]; ok = tot = 0; bad = []; acts = {}; left = {}
    for f in range(frames):
        g = groups(s); idx = {a: i for i, (a, _, _) in enumerate(g)}
        want = {a for a, t, p in g if t > p}
        got = set()
        for i, (a, t, p) in enumerate(g):
            if a in left: acts.setdefault(i, []).append((f, left.pop(a)))
        while True:
            s('step', n=1)
            r = s('run', max_steps=2_000_000, until_pc=[UPD, THINK])
            if pc(r) == UPD: break
            got.add(s.reg('a0') & 0xffffff)
        steps.append(r['step'])
        for a, t, p in g:
            tot += 1
            if (a in want) == (a in got): ok += 1
            elif len(bad) < 10: bad.append((f, idx[a], t, p, a in want, a in got))
        for a, t, p in groups(s):
            if a in got: left[a] = t
    d = [b - a for a, b in zip(steps, steps[1:])]
    print(f'{ok}/{tot} group-frames match (think iff timer > period at frame start), {frames} frames')
    print(f'main frame steps: min {min(d)} median {statistics.median(d)} max {max(d)}')
    for i, lst in sorted(acts.items()):
        fs = [f for f, _ in lst]
        print(f'g{i}: intervals {[b - a for a, b in zip(fs, fs[1:])]} timer after think {[t for _, t in lst]}')
    for b in bad: print('MISMATCH frame,group,timer,period,want,got', b)
    s.close()

if __name__ == '__main__':
    main()
