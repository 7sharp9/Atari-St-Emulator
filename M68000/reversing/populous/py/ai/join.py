"""join.py SCEN SNAP [NSTEPS]  (SCEN = A / B: live/<SCEN>_log + live/<SCEN>_<site>.jsonl)

Replays the natural-run command log through the models: every command found in a god record at
$1e712 entry is attributed (WATCH pc of the last write to its cmd byte) to the routine that wrote it,
and the livecheck record of that exact call (the last call of that routine before the write) must
be a model match whose predicted command bytes equal the logged ones.
Only log entries inside the step range covered by every livecheck file are counted.
"""
import collections, json, os, re, sys
from aicfg import *
from livelib import snap_step

RANGES = [(0xef4c, 0xf2f4, 'ef4c'), (0xf6b2, 0xfe00, 'f6b2'), (0x135fc, 0x13816, '135fc'),
          (0x13816, 0x13a44, '13816'), (0x13a44, 0x13eda, '13a44'), (0x13eda, 0x14200, '13eda'),
          (0x1eef4, 0x1ef70, 'clear')]
SITES = {'13eda': ['think'], '13a44': ['powers'], '135fc': ['flat1', 'flat2'], '13816': ['level'],
         'f6b2': ['dir'], 'ef4c': ['step1', 'step2']}
ALLSITES = ['think', 'powers', 'flat1', 'flat2', 'level', 'step1', 'step2', 'dir']
WRE = re.compile(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)')


def routine_of(pc):
    for a, b, n in RANGES:
        if a <= pc < b: return n
    return '%06x' % pc


def dedup(L, key):
    """an interrupt taken at the stop address makes PC reach it again a few dozen steps later
    (RTE back to the same instruction): drop the second stop."""
    out = []
    for r in L:
        if out and r.get('frame') == out[-1].get('frame') and (
                key == 'step' or (r[key] - out[-1][key] < 5000 and r.get('args') == out[-1].get('args'))):
            continue
        out.append(r)
    return out


def main():
    scen, snap = sys.argv[1], sys.argv[2]
    live = os.path.join(AI, 'live')
    base = snap_step(snap)
    log = dedup([json.loads(l) for l in open(os.path.join(live, scen + '_log', 'log.jsonl'))], 'step')
    recs = {}
    lim = None
    for s in ALLSITES:
        p = os.path.join(live, '%s_%s.jsonl' % (scen, s))
        L = [json.loads(l) for l in open(p)] if os.path.exists(p) else []
        for r in L: r['abs'] = base + r['step']
        L = dedup(L, 'abs')
        recs[s] = L
        done = os.path.exists(os.path.join(live, '%s_%s.out' % (scen, s))) and \
            'calls' in open(os.path.join(live, '%s_%s.out' % (scen, s))).read()
        if not done and L:
            last = L[-1]['abs'] if L else base
            lim = last if lim is None else min(lim, last)
    if len(sys.argv) > 3:                                   # livecheck NSTEPS: their common end
        end = base + int(sys.argv[3])
        lim = end if lim is None else min(lim, end)
    writes = {0: [], 1: []}
    for line in open(os.path.join(live, scen + '_log', 'watch.txt')):
        m = WRE.match(line)
        if not m: continue
        a = int(m.group(4), 16)
        for s in (0, 1):
            if a == 0x21e0c + s * 0x2e and m.group(3) == 'Byte':
                writes[s].append((int(m.group(1)), int(m.group(2), 16), int(m.group(5), 16)))
    tot = collections.Counter(); bad = []
    calls = collections.Counter(); callbad = collections.Counter()
    for s in ALLSITES:
        for r in recs[s]:
            if lim is not None and r['abs'] > lim: continue
            calls[s] += 1
            if r['match'] is not True: callbad[(s, str(r['match']))] += 1
    prev = base
    first = last = None
    for e in log:
        if lim is not None and e['step'] > lim: break
        first = first or e['frame']; last = e['frame']
        for s in (0, 1):
            c = e['s%d' % s]['cmd']
            if c[0] == 0: continue
            tot['commands'] += 1
            ws = [w for w in writes[s] if prev < w[0] < e['step']]
            rt = routine_of(ws[-1][1]) if ws else 'none'
            tot['by_' + rt] += 1
            # every checked call in this frame, in execution order
            win = sorted((r for site in ALLSITES for r in recs[site] if prev < r['abs'] < e['step']),
                         key=lambda r: r['abs'])
            chg = [r for r in win if any(x[0] == s for x in r['model_cmd'])]
            if not chg:
                bad.append(('no predicting call', e['frame'], s, c, rt)); continue
            r = chg[-1]
            mc = [x for x in r['model_cmd'] if x[0] == s][0]
            if r['match'] is None:                          # $f6b2 knight re-acquire: $ef4c oracle record
                cc = [x for x in win if x['site'] in ('step1', 'step2') and x['abs'] < r['abs']]
                if cc and cc[-1]['match'] and any(x[0] == s for x in cc[-1]['model_cmd']):
                    mc = [x for x in cc[-1]['model_cmd'] if x[0] == s][0]; tot['via_ef4c_oracle'] += 1
                    r = dict(r, match=True)
            site_rt = {'think': '13eda', 'powers': '13a44', 'flat1': '135fc', 'flat2': '135fc',
                       'level': '13816', 'dir': 'f6b2', 'step1': 'ef4c', 'step2': 'ef4c'}[r['site']]
            if site_rt != rt and not (rt == 'f6b2' and site_rt == 'ef4c'):
                tot['writer_differs'] += 1
            if r['match'] is True and mc[1:4] == c:
                tot['predicted'] += 1
                tot['cmd%d' % c[0] + ('/%d' % c[2] if c[0] == 14 else '')] += 1
            else:
                bad.append(('mismatch', e['frame'], s, c, rt, r))
        prev = e['step']
    print('scenario %s frames %s..%s (livecheck coverage limit %s)' % (scen, first, last, lim))
    print('calls checked:', dict(calls), 'non-match:', dict(callbad))
    print('commands at $1e712:', dict(sorted(tot.items())))
    for b in bad[:20]: print('BAD', b)


if __name__ == '__main__':
    main()
