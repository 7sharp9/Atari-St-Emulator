"""cmdlog.py SNAP NFRAMES OUTDIR [SNAP_EVERY]

Natural run with no input. At every entry of $1e712 (god_commands_exec) log both god records'
command bytes (+0 cmd, +1 x, +2 y), ctrl/busy, the frame counter, side states and walker count;
a `watch` on both god records ($21e0c..$21e67) records every write with its PC and absolute step
(stderr -> OUTDIR/watch.txt), so each command can be attributed to the routine that wrote it.
Snapshots every SNAP_EVERY frames go to OUTDIR/fNNNNN.snap.
Output: OUTDIR/log.jsonl, one line per $1e712 entry.
"""
import json, os, struct, sys
from aicfg import *
from livelib import Sess, snap_step


def main():
    snap, nframes, outdir = sys.argv[1], int(sys.argv[2]), os.path.abspath(sys.argv[3])
    every = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    os.makedirs(outdir, exist_ok=True)
    base = snap_step(snap)
    S = Sess(snap, errfile=os.path.join(outdir, 'watch.txt'))
    S.cmd('watch 21e0c 92')
    fo = open(os.path.join(outdir, 'log.jsonl'), 'w')
    for i in range(nframes):
        if not S.until(0x1e712, 60000000):
            print('no $1e712 within 60M steps'); break
        g = S.mem(0x21e0c, 92)
        st = S.mem(0x3b226, 32)
        misc = S.mem(0x3c4c8, 2)
        nw = struct.unpack('>H', S.mem(0x3c4e2, 2))[0]
        frame = struct.unpack('>H', misc)[0]
        rec = {'i': i, 'step': base + S.steps, 'frame': frame, 'nwalk': nw}
        for s in (0, 1):
            r = g[s * 0x2e:(s + 1) * 0x2e]
            w = lambda o: struct.unpack_from('>H', r, o)[0]
            t = st[s * 16:(s + 1) * 16]
            tw = lambda o: struct.unpack_from('>H', t, o)[0]
            rec['s%d' % s] = {'cmd': [r[0], r[1], r[2]], 'ctrl': w(6), 'busy': w(8), 'c': w(18),
                              'castles': w(20), 'houses': w(22), 'hold': w(28), 'tgt': w(30),
                              'leader': tw(0), 'magnet': tw(2), 'mode': tw(4), 'towns': tw(6),
                              'pop': struct.unpack_from('>i', t, 8)[0], 'mana': struct.unpack_from('>i', t, 12)[0]}
        fo.write(json.dumps(rec) + '\n'); fo.flush()
        if every and i % every == 0:
            S.cmd('snap ' + os.path.join(outdir, 'f%05d.snap' % frame))
    S.cmd('snap ' + os.path.join(outdir, 'last.snap'))
    S.close()
    print('logged', i + 1, 'frames; steps', S.steps)


if __name__ == '__main__':
    main()
