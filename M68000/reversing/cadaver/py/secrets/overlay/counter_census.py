"""counter_census.py [snap ...]: how the shipped scripts use the condition counter 2270(A5).

Every IF verb (14, 48, 58 n, 59 n) clears the counter before running the part it picks (`$01062c` and `$010660`, read), so the
conditions an IF sees are the ones between it and the previous IF.  For each object and room block of each snapshot this
counts the COND verbs since the previous IF at the same nesting depth, tabulates (IF verb, n, conditions), and prints the
blocks where the IF cannot see every condition: verb 14 or 48 after two or more (only the last one decides), or 58/59 with
n other than the count (58 0 after k conditions is true exactly when the last one is false).
Static only; conditions inside an inner part that carry out of it are not followed.
Run from M68000/:  .venv/bin/python reversing/cadaver/py/secrets/overlay/counter_census.py scratchpad/cadaver/gameplay_empire.snap scratchpad/cadaver/level1_loaded.snap"""
import sys, collections
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
import verb_decode as vd
from room_blocks import room_blocks

CONDS = {16, 19, 30, 34, 40, 43, 47, 56, 57, 60, 61, 64, 76, 80, 88, 91}
IFS = {14, 48, 58, 59}


def decode(e, body):
    try: return vd.decode_block(e, body)
    except vd.Bad: return vd.decode_block(e, body[:-1])   # room block of odd content length: one uninitialised pad byte


for snap in sys.argv[1:]:
    vd.load_text(snap)
    blocks = [('obj %d' % oid, e, body) for oid, start, e, body in vd.collect(snap)]
    blocks += [('room %d' % slot, e, body) for slot, e, body, off in room_blocks(snap)[0]]
    hist = collections.Counter(); flagged = []
    for owner, e, body in blocks:
        out = decode(e, body)
        since = collections.defaultdict(int)
        for d, v, args, name in out:
            if v in CONDS: since[d] += 1
            elif v in IFS:
                k = int(args[0], 16) if v in (58, 59) else None
                n = since[d]; since[d] = 0
                hist[(v, k, n)] += 1
                if (v in (14, 48) and n != 1) or (v in (58, 59) and n != k):
                    flagged.append((owner, e & 0x7f, v, k, n, out))
    print('== %s: %d blocks' % (snap, len(blocks)))
    for (v, k, n), c in sorted(hist.items(), key=lambda t: (t[0][0], t[0][1] or 0, t[0][2])):
        print('  IF %-2d %-5s after %d condition(s): %d' % (v, '' if k is None else 'n=%d' % k, n, c))
    print('  IFs that do not see every condition: %d' % len(flagged))
    for owner, ev, v, k, n, out in flagged:
        print('--- %s event %d: IF %d n=%s after %d conditions' % (owner, ev, v, k, n)); print(vd.fmt(out))
