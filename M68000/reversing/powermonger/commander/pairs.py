"""pairs.py <seeds out dir> <side> [--base ai] [--at 300,440]: a seeds.sh result scored as paired differences.
For each arm and start o<k>, the side's lords and force (men at home + group men, runstat's sum) at the last decision
at or before each --at step (M, relative to the start; the LLM arm decides every 20M, so pick multiples of 20), and
the end record. Then each arm minus the --base arm, start by start, with the mean and the count of starts it is ahead
on (lords first, force to break a tie). A '*' marks a run that ended or stopped before that step: its value is the
last decision's, so read it as a censored score. Safe on runs still in progress."""
import json, sys
from pathlib import Path

a = sys.argv[1:]
def opt(k, d):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
base = opt('--base', 'ai')
at = [int(float(x)) for x in opt('--at', '300,440').split(',')]
out, side = Path(a[0]), a[1]

def score(run):
    f = run / 'decisions.jsonl'
    if not f.exists():
        return None
    L = [json.loads(l) for l in open(f)]
    d = [e for e in L if e['kind'] == 'decision']
    end = L[-1] if L and L[-1]['kind'] == 'end' else None
    r = {}
    for s in at:
        e = [x for x in d if x['step'] <= s * 1000000]
        if not e:
            continue
        t = e[-1]['totals'][side]
        cens = d[-1]['step'] < s * 1000000
        r[s] = (t['lords'], t['men_home'] + t['group_men'], cens)
    r['end'] = '%s@%dM' % (end['reason'], end['step'] // 1000000) if end else 'running %dM' % (d[-1]['step'] // 1000000 if d else 0)
    return r

arms = sorted(p.name for p in out.iterdir() if p.is_dir() and p.name != 'start')
starts = sorted({p.name for arm in arms for p in (out / arm).iterdir() if p.name.startswith('o')}, key=lambda o: int(o[1:]))
S = {(arm, o): score(out / arm / o) for arm in arms for o in starts}

def cell(v):
    return '-' if v is None else '%d/%d%s' % (v[0], v[1], '*' if v[2] else '')

for s in at:
    print('== side %s lords/force at %dM' % (side, s))
    print('%-10s' % 'arm' + ''.join('%11s' % o for o in starts))
    for arm in arms:
        print('%-10s' % arm + ''.join('%11s' % cell((S[arm, o] or {}).get(s)) for o in starts))
    if base not in arms:
        continue
    print('-- minus %s (lords, force); ahead = starts with more lords, or equal lords and more force' % base)
    for arm in arms:
        if arm == base:
            continue
        dl, df, ahead, n = [], [], 0, 0
        row = ''
        for o in starts:
            x, b = (S[arm, o] or {}).get(s), (S[base, o] or {}).get(s)
            if x is None or b is None:
                row += '%11s' % '-'; continue
            l, f = x[0] - b[0], x[1] - b[1]
            dl.append(l); df.append(f); n += 1
            ahead += (l, f) > (0, 0)
            row += '%11s' % ('%+d/%+d' % (l, f))
        m = ' mean %+.1f/%+.1f ahead %d/%d' % (sum(dl) / n, sum(df) / n, ahead, n) if n else ''
        print('%-10s' % arm + row + m)
print('== end')
for arm in arms:
    print('%-10s' % arm + '  '.join('%s %s' % (o, (S[arm, o] or {}).get('end', '-')) for o in starts))
