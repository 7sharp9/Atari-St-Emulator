"""magnetcheck.py LOGDIR - every cmd 5 (move papal magnet) found at $1e712: side mana at that moment
and whether the side's magnet cell equals the target one frame later (accepted) or not (refused).
Also: lowest mana seen per side."""
import json, os, sys
from join import dedup
L = dedup([json.loads(l) for l in open(os.path.join(sys.argv[1], 'log.jsonl'))], 'step')
acc = ref = ref_low = acc_low = 0; streak = []
for a, b in zip(L, L[1:]):
    for s in (0, 1):
        x = a['s%d' % s]; c = x['cmd']
        if c[0] != 5: continue
        cell = c[2] * 64 + c[1]
        ok = b['s%d' % s]['magnet'] == cell or x['magnet'] == cell
        if ok: acc += 1; acc_low += x['mana'] < 200
        else: ref += 1; ref_low += x['mana'] < 200
print('cmd5 accepted %d (of which mana<200: %d); refused %d (of which mana<200: %d)' % (acc, acc_low, ref, ref_low))
for s in (0, 1):
    m = min(L, key=lambda e: e['s%d' % s]['mana'])
    neg = sum(1 for e in L if e['s%d' % s]['mana'] < 0)
    print('side %d min mana %d at frame %d; frames with mana < 0: %d' % (s, m['s%d' % s]['mana'], m['frame'], neg))
