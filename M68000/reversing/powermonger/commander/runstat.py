"""runstat.py <run dir> ...: one line per loop.py run from its decisions.jsonl: the last decision's step (M), per side
(lords, men at home + group men), the local groups [k, men, state, food], the last rollout choice, and the end record
(reason, ratio, step) when the run has ended. Safe on a run still in progress."""
import json, sys
for f in sys.argv[1:]:
    L = [json.loads(l) for l in open(f + '/decisions.jsonl')]
    d = [e for e in L if e['kind'] == 'decision']
    if not d:
        print(f, 'no decision'); continue
    e = d[-1]; t = e['totals']
    end = L[-1] if L[-1]['kind'] == 'end' else None
    print(f, e['step'] // 1000000, 'M', {s: (t[s]['lords'], t[s]['men_home'] + t[s]['group_men']) for s in t},
          'grp', [g[:4] for g in e.get('groups', [])], 'best', e.get('rollout', {}).get('best'),
          'END %s ratio %s step %s' % (end['reason'], end.get('ratio'), end['step']) if end else '')
