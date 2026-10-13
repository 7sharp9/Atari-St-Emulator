"""runstat.py [--every M] <run dir> ...: one line per loop.py run from its decisions.jsonl: the last decision's step (M),
per side (lords, men at home + group men), the local groups [k, men, state, food], the last rollout choice, and the end
record (reason, ratio, step) when the run has ended. Safe on a run still in progress.
--every M: the run's trajectory instead, one line per decision at a multiple of M million steps: the step (M), the
local groups [k, men, state, food], per side (lords, men at home, group men, groups alive), the rollout choice and the
decision's actions as (type, x, y, group). A cause read off the end of a run needs this (CLAUDE.md, evidence rules)."""
import json, sys
a = sys.argv[1:]
every = None
if '--every' in a:
    i = a.index('--every'); every = int(float(a[i + 1]) * 1e6); del a[i:i + 2]
for f in a:
    L = [json.loads(l) for l in open(f + '/decisions.jsonl')]
    d = [e for e in L if e['kind'] == 'decision']
    if not d:
        print(f, 'no decision'); continue
    end = L[-1] if L[-1]['kind'] == 'end' else None
    if every:
        print('==', f)
        for e in d:
            if e['step'] % every:
                continue
            t = e['totals']
            print(e['step'] // 1000000, [g[:4] for g in e.get('groups', [])],
                  {s: (t[s]['lords'], t[s]['men_home'], t[s]['group_men'], t[s]['groups_alive']) for s in t if t[s]['lords'] or t[s]['groups_alive']},
                  e.get('rollout', {}).get('best', ''),
                  [(x.get('type'), x.get('x'), x.get('y'), x.get('group')) for x in e['actions'] if 'type' in x])
        if end:
            print('END %s ratio %s step %s' % (end['reason'], end.get('ratio'), end['step']))
        continue
    e = d[-1]; t = e['totals']
    print(f, e['step'] // 1000000, 'M', {s: (t[s]['lords'], t[s]['men_home'] + t[s]['group_men']) for s in t},
          'grp', [g[:4] for g in e.get('groups', [])], 'best', e.get('rollout', {}).get('best'),
          'END %s ratio %s step %s' % (end['reason'], end.get('ratio'), end['step']) if end else '')
