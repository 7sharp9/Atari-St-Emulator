"""summarize_batches.py [OUTDIR]: totals of anim_batch.out and mover_batch.out (the free-run gates): anim passes matching anim_model, mover passes by class, states seen, program ops fetched."""
import sys, os, collections
OUT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('OUTDIR', 'scratchpad/cadaver/s91_state')
ok = m = 0; snaps = 0; skipped = 0; ops = collections.Counter()
for l in open(OUT + '/anim_batch.out'):
    if l.startswith('=='): snaps += 1
    if 'PC never' in l: skipped += 1
    if l.startswith('TOTAL'): t = l.split(); ok += int(t[1]); m += int(t[3])
    if 'ops seen' in l: ops.update(l.split('ops seen')[1].split())
print('anim gate: %d of %d passes match anim_model (%d snapshots, %d not in the main loop); ops seen live %s' % (ok, m, snaps, skipped, dict(ops)))
tot = collections.Counter(); mops = collections.Counter(); snaps = skipped = 0
for l in open(OUT + '/mover_batch.out'):
    if l.startswith('=='): snaps += 1
    if 'PC never' in l: skipped += 1
    if l.startswith('TOTAL'):
        i = l.index(' program'); tot.update(eval(l[6:i])); mops.update(eval(l[i + len(' program ops fetched '):]))
cl = ('MOVED', 'IDLE', 'REFUSED', 'MOVED-ADJUSTED', 'IDLE+displaced', 'BAD'); n = sum(tot[k] for k in cl)
print('mover gate: %d of %d passes match mover_model (%s) (%d snapshots, %d not in the main loop); states %s; program ops fetched %s' % (n - tot['BAD'], n, ', '.join('%s %d' % (k, tot[k]) for k in cl), snaps, skipped, {k: v for k, v in tot.items() if k.startswith('state')}, dict(mops)))
