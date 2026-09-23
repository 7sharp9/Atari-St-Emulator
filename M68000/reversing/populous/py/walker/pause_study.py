"""pause_study.py <frames.bin> : every flag-$20 pause in a capframes run, checked against the
$eb8c rule and followed to its outcome.

$eb8c (per frame, for each walker B after its own step code): A = occupancy[B.cell]-1; if A != B,
A < $d0, A.anim == 0 and A not in water: A.flags |= $20, A.anim = $65, A.t6 = 0.
A walker's occupancy mark is the cell it is walking away from (set in $ef4c at $f2d2, cleared at its
next step), so the rule reads: B is heading into the cell A has just left on the step A took this
frame (anim 0). The model below predicts, from the frame's entry state and the exit positions,
which walkers get paused, and reports what happens to each paused pair afterwards.
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import walker_ref as W
from capframes import REGIONS as FR, RECLEN

B0 = FR[0][0]


def ents(buf):
    n = struct.unpack_from('>H', buf, W.COUNT - B0)[0]
    out = []
    for i in range(n):
        a = W.ENT + i * W.ESZ - B0
        fl, side = buf[a], buf[a + 1]
        st, t6, cell, off, anim = struct.unpack_from('>hhHhh', buf, a + 4)
        out.append(dict(i=i, fl=fl, side=side, str=st, t6=t6, cell=cell, off=off, anim=anim))
    return out


def main(path, horizon=24):
    b = open(path, 'rb').read()
    recs = [b[k * RECLEN:(k + 1) * RECLEN] for k in range(len(b) // RECLEN)]
    posts = recs[1::2]
    frames = [struct.unpack_from('>H', p, 0x3c4c8 - B0)[0] for p in posts]
    events, rule_ok, rule_n = [], 0, 0
    for f in range(len(posts)):
        pre, post = recs[2 * f], posts[f]
        e0, e1 = ents(pre), ents(post)
        occ = post[W.OCC - B0:W.OCC - B0 + 4096]
        for a in e1:
            i = a['i']
            if i >= len(e0): continue
            if a['fl'] & 0x20 and not e0[i]['fl'] & 0x20:
                # who triggered it: walkers B (flags 2 at exit) whose cell carries A's mark
                bs = [x['i'] for x in e1 if x['i'] != i and x['fl'] == 2 and occ[x['cell']] == i + 1]
                rule_n += 1
                marked = (e1[i]['cell'] - e1[i]['off']) & 0xffff
                if bs and all(e1[j]['cell'] == marked for j in bs): rule_ok += 1
                events.append((f, i, bs, a))
    print('pause events: %d; triggering walker found heading into the cell A just left: %d/%d'
          % (len(events), rule_ok, rule_n))
    # outcomes
    out = {}
    for f, i, bs, a in events:
        side = a['side']
        res = 'none'
        for g in range(f + 1, min(len(posts), f + horizon)):
            e1 = ents(posts[g])
            A = e1[i] if i < len(e1) else None
            Bs = [e1[j] for j in bs if j < len(e1)]
            if any(B['str'] <= 0 for B in Bs) and A and A['str'] > 0:
                res = 'B merged into A' if all(B['side'] == side for B in Bs) else 'B died'; break
            if A and (A['fl'] & 8 or any(B['fl'] & 8 for B in Bs)):
                res = 'fight'; break
            if A and A['str'] <= 0:
                res = 'A gone (merged/died)'; break
            if A and not A['fl'] & 0x20:
                res = 'A resumed, no contact'; break
        out[res] = out.get(res, 0) + 1
    print('outcomes within %d frames:' % horizon, out)
    # pause length and per-frame strength loss while paused (A alone, no merge into A during the pause)
    lens, loss_ok, loss_n = {}, 0, 0
    for f, i, bs, a in events:
        n = 0; g = f
        while g + 1 < len(posts):
            e0, e1 = ents(posts[g]), ents(posts[g + 1])
            if i >= len(e1) or not e1[i]['fl'] & 0x20:
                break
            loss_n += 1; loss_ok += (e0[i]['str'] - e1[i]['str'] == 1)
            n += 1; g += 1
        if g + 1 < len(posts) and i < len(ents(posts[g + 1])) and ents(posts[g + 1])[i]['str'] > 0:
            lens[n + 1] = lens.get(n + 1, 0) + 1
    print('frames with flag $20 set (incl. the trigger frame) for pauses that end alive:', lens)
    print('paused frames losing exactly $37eb0 = 1 strength: %d/%d' % (loss_ok, loss_n))
    same = sum(1 for f, i, bs, a in events if bs and all(ents(posts[f])[j]['side'] == a['side'] for j in bs))
    print('trigger same side as paused walker: %d/%d' % (same, len(events)))
    return events


if __name__ == '__main__':
    main(sys.argv[1])


def blocked40(path):
    """$40 pauses (decision 999 at $efb0): frames spent with $40 set before the walker moves again."""
    b = open(path, 'rb').read()
    posts = [b[k * RECLEN:(k + 1) * RECLEN] for k in range(1, len(b) // RECLEN, 2)]
    lens = {}
    for f in range(1, len(posts)):
        e0, e1 = ents(posts[f - 1]), ents(posts[f])
        for a in e1:
            i = a['i']
            if i < len(e0) and a['fl'] & 0x40 and not e0[i]['fl'] & 0x40 and a['t6'] in (7, 8):
                n, g = 0, f
                while g < len(posts) and i < len(ents(posts[g])) and ents(posts[g])[i]['fl'] & 0x40 \
                        and ents(posts[g])[i]['str'] > 0:
                    n += 1; g += 1
                if g < len(posts): lens[n] = lens.get(n, 0) + 1
    print('$40 (no legal move) pauses: frames with $40 set at frame exit ->', lens)


if __name__ == '__main__' and len(sys.argv) > 2:
    blocked40(sys.argv[1])
