"""trace_cmp.py - compare walker.tick() with the game, tick by tick, from a REPL watch log of one man's record.

Input: the REPL stdout (first `m <rec> 50` line = the initial record) and stderr (WATCH lines from
`watch <rec> 50`), the record address, and the snapshot (for the terrain).
Writes are grouped into clusters (gap > 40000 steps). A cluster is the man's own handler pass when every write
in it comes from the walk handlers or their leaves; otherwise it is an outside writer. For each own-handler
cluster whose start state is in a walk mode, walker.tick() predicts the end state, and CMP fields are compared.

Usage: trace_cmp.py <snap> <rec hex addr> <stdout> <stderr> [--show N]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import walker  # noqa: E402

OWN = [(0x14b72, 0x14bb4), (0x14f08, 0x15018), (0x158da, 0x159a4), (0x161c4, 0x1623c), (0x163ea, 0x164bc), (0x164bc, 0x16600),
       (0x16778, 0x16800)]
RX = re.compile(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(Byte|Word|Long) \$([0-9a-f]+) <- \$([0-9a-f]+)')


def own(pc):
    return any(a <= pc < b for a, b in OWN)


def clusters(errf, base):
    cl, last = [], None
    for ln in open(errf):
        m = RX.search(ln)
        if not m:
            continue
        st, pc, sz, a, v = int(m[1]), int(m[2], 16), m[3], int(m[4], 16), int(m[5], 16)
        n = {'Byte': 1, 'Word': 2, 'Long': 4}[sz]
        if last is None or st - last > 40000:
            cl.append([])
        cl[-1].append((st, pc, a - base, n, v))
        last = st
    return cl


def main(argv):
    snap, base, outf, errf = argv[0], int(argv[1], 16), argv[2], argv[3]
    show = int(argv[argv.index('--show') + 1]) if '--show' in argv else 10
    hexl = [l for l in open(outf) if re.fullmatch(r'([0-9a-f]{2} ){49}[0-9a-f]{2}\s*', l)]
    rec = bytearray(bytes.fromhex(hexl[0].replace(' ', '').strip()))
    mp = walker.astar.Map(snap)
    n_ok = n_bad = n_ext = n_skip = 0
    ext = []
    bad = []
    for c in clusters(errf, base):
        pre = walker.decode(rec)
        for (_st, _pc, off, n, v) in c:
            if 0 <= off and off + n <= 50:
                rec[off:off + n] = v.to_bytes(n, 'big')
        post = walker.decode(rec)
        if not all(own(pc) for (_s, pc, *_r) in c):
            n_ext += 1
            pcs = sorted({'%x' % pc for (_s, pc, *_r) in c if not own(pc)})
            ext.append((c[0][0], pcs, pre['mode'], pre['prev'], (pre['tx'], pre['ty']), post['mode'], post['prev'],
                        (post['tx'], post['ty']), (post['x'], post['y'])))
            continue
        if not any(off not in (0, 1, 2, 3, 14) for (_s, _pc, off, _n, _v) in c):
            continue                                  # bucket links / anim byte only (a neighbour's relink)
        if pre['mode'] not in walker.WALK:
            n_skip += 1
            continue
        try:
            pr = walker.tick(mp, pre)
        except walker.Unmodelled as e:
            n_skip += 1
            continue
        diff = [k for k in walker.CMP if pr[k] != post[k]]
        if diff:
            n_bad += 1
            bad.append((c[0][0], diff, {k: (pre[k], pr[k], post[k]) for k in diff}))
        else:
            n_ok += 1
    print('own-handler ticks: %d match, %d differ, %d skipped (not a walk mode / unmodelled); outside-writer clusters: %d'
          % (n_ok, n_bad, n_skip, n_ext))
    for b in bad[:show]:
        print('  DIFF step %d %s' % (b[0], b[2]))
    for e in ext:
        print('  OUTSIDE step %d pcs %s: mode %02x prev %02x target %s -> mode %02x prev %02x target %s at %s' % e)
    print('final record state:', walker.decode(rec))


if __name__ == '__main__':
    main(sys.argv[1:])
