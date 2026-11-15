"""check_chain.py <chain.jsonl> [--control]: the gate's checks on a short chain from S1b.snap.  Expected (from py/demo/chain.py's six-game run, reproduced by
this driver): over-ticks 12088, 12894; scores 17526, 19770; waves 3, 3; the queue at game 1's start is zero; $32a52 at game 2's start equals game 1's wave.
--control compares against the same numbers shifted by one tick, which must match 0 of 2."""
import sys, json
rows = [json.loads(l) for l in open(sys.argv[1])]; ctl = '--control' in sys.argv
exp = [(12088, 17526, 3), (12894, 19770, 3)]
if ctl: exp = [(t + 1, s, w) for t, s, w in exp]
ok = sum((r['over']['tick'], r['over']['score'], r['over']['wave']) == e for r, e in zip(rows, exp))
print(f"{'control (expected tick + 1): ' if ctl else ''}over tick, score, wave equal the six-game run: {ok}/{len(exp)} ({len(rows)} games run)")
if not ctl:
    print(f"game 1 start queue zero: {set(rows[0]['queue']) == {'0'}}; $32a52 at game 2 start == game 1 wave: {rows[1]['w32a52'] == rows[0]['over']['wave']} ({rows[1]['w32a52']} vs {rows[0]['over']['wave']})")
