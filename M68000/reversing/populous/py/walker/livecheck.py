"""livecheck.py <calls.bin> [<frames.bin>] : check every live $ef4c decision against walker_ref.

calls.bin  from capcalls.py: per call, the RAM at $ef4c entry and the D0 at $efa8.
frames.bin from reversing/populous/py/capframes.py over the same run (same start snapshot, no input):
           per frame, RAM at $db4c entry and exit. Every walker's cell change across a frame must equal
           the model's offset for its decision in that frame (0 when it made none).
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import walker_ref as W
import capcalls as C
import hx
from popcfg import WORK

BASE = bytearray(hx.load(WORK + '/game_start.snap'))    # constant DATA tables ($22b4e, $225a4 ...)


def s16(v): return v - 0x10000 if v & 0x8000 else v


def check_calls(path):
    recs = C.load(path)
    good, cov, fails, pred = 0, {}, [], {}
    for r in recs:
        m = C.apply(BASE, r['mem'])
        f6 = W.uses_f6b2(m, r['e'])
        ret = W.choose(m, r['e'], s16(r['idx'])) & 0xffff
        side = m[r['e'] + 1]
        mode = struct.unpack_from('>H', m, W.sidest(side) + 4)[0]
        k = ('f6b2:%s/%s' % (W.INFO.get('who'), W.INFO.get('how'))) if f6 else \
            'side%d m%d:%s' % (side, mode, W.INFO['cat'])
        cov[k] = cov.get(k, 0) + 1
        fr = C.frame_of(r)
        pred.setdefault((fr, r['idx']), []).append(s16(ret))
        if ret == r['d0']: good += 1
        elif len(fails) < 10: fails.append((fr, r['idx'], hex(r['d0']), hex(ret), k))
    print('decisions: %d/%d model == real D0' % (good, len(recs)))
    print('coverage', ' '.join('%s:%d' % kv for kv in sorted(cov.items())))
    for f in fails: print('FAIL', f)
    return recs, pred


def check_frames(path, pred, f0, f1):
    """walker cells, frame by frame, restricted to frames [f0, f1] covered by the call capture."""
    from capframes import REGIONS as FR, RECLEN
    b = open(path, 'rb').read()
    nrec = len(b) // RECLEN

    def rec(i):
        return b[i * RECLEN:(i + 1) * RECLEN]

    def ent(buf, i):
        a = W.ENT + i * W.ESZ - FR[0][0]
        return buf[a], struct.unpack_from('>H', buf, a + 8)[0]
    ok = bad = frames = moved = reused = 0
    fails = []
    for i in range(0, nrec - 1, 2):
        pre, post = rec(i), rec(i + 1)
        fr = struct.unpack_from('>H', post, 0x3c4c8 - FR[0][0])[0]      # frame number after $db58's ++
        if not (f0 <= fr <= f1): continue
        frames += 1
        n = struct.unpack_from('>H', pre, W.COUNT - FR[0][0])[0]
        for j in range(n):
            fl0, c0 = ent(pre, j)
            fl1, c1 = ent(post, j)
            if not (fl0 & 2 or fl0 & 0x60) or fl0 & 0x88: continue          # walkers (incl. paused)
            steps = [p for p in pred.get((fr, j), []) if p != W.NONE]
            exp = (c0 + sum(steps)) & 0xffff
            if fl1 == 0 or fl1 & 0x88 or struct.unpack_from('>h', post, W.ENT + j * W.ESZ + 4 - FR[0][0])[0] <= 0:
                continue                                                  # died / started a fight: cell frozen
            a0 = W.ENT + j * W.ESZ - FR[0][0]
            if struct.unpack_from('>h', pre, a0 + 4)[0] <= 0:
                reused += 1; continue                                     # dead slot refilled this frame
            off1, last1 = struct.unpack_from('>hH', post, a0 + 10)[0], struct.unpack_from('>H', post, a0 + 18)[0]
            if c1 != exp and off1 == 0 and last1 == c1 and any(
                    struct.unpack_from('>H', post, W.ENT + k * W.ESZ + 8 - FR[0][0])[0] == c1
                    and post[W.ENT + k * W.ESZ - FR[0][0]] == 1 for k in range(n)):
                reused += 1; continue                                     # merged away, slot refilled by an emitted walker
            if c1 == exp: ok += 1
            else:
                bad += 1
                if len(fails) < 10: fails.append((fr, j, hex(fl0), c0, c1, steps))
            if c1 != c0: moved += 1
    print('frame cells: %d/%d walker-frames match over %d frames (%d moves; %d slot-reuse frames excluded)'
          % (ok, ok + bad, frames, moved, reused))
    for f in fails: print('FAIL frame', f)


if __name__ == '__main__':
    recs, pred = check_calls(sys.argv[1])
    if len(sys.argv) > 2 and recs:
        check_frames(sys.argv[2], pred, C.frame_of(recs[0]), C.frame_of(recs[-1]) - 1)
