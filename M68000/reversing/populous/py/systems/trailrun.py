"""trailrun.py - live check of the trail effects against trail_ref.py.

  python trailrun.py [nframes] [type]

Starts from systems/spawn.snap (natural run late4 -> frame $1000, stopped at $13372 entry,
called from $b8f4 with type = $37ec2&3 = 2 and edge = the caller's stack word = 0). With a type
argument, the pushed type word (4(A7) at the breakpoint) is poked first (labelled POKED).

1. spawn: RAM at $13372 entry -> spawn_13372 model -> compared with RAM at its return ($b8fa)
   over the effect records, occupancy map, seed, frame counter and both god_rec ctrl words.
2. then per frame, RAM at $12f84 entry and at its return ($b7c8): tick_12f84 on the entry state
   compared with the exit state over the effect records and the class/feature/occupancy maps and
   the whole entity array (victims), i.e. every byte of those regions.
"""
import os, re, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import OUT, R, DLL, DISK
import trail_ref as T

REG = [(0x3b278, T.ESZ * 0xd3), (0x36e78, 0x1000), (0x3c522, 0x1000), (0x37fd4, 0x1000),
       (0x3b226, 0x20), (0x3d52e, 2), (0x3c4c8, 2), (0x3c4c6, 2), (0x21e0c, 0x5c), (0x3c4b4, 4),
       (0x21d58, 4), (0x3affe, 2), (0x21e7c, 48), (0x21ea0, 0x40)]


def dump():
    L = []
    for a, n in REG:
        L += ['m %x %d' % (a, n), 'r']
    return L


def parse(out):
    blobs, cur = [], None
    for line in out.splitlines():
        t = line.split()
        if t and all(re.fullmatch('[0-9a-f]{2}', x) for x in t):
            cur = (cur or bytearray()) + bytes(int(x, 16) for x in t)
        elif cur is not None:
            blobs.append(bytes(cur)); cur = None
    return blobs


def to_mem(blobs):
    m = bytearray(0x40000)
    for (a, n), b in zip(REG, blobs):
        assert len(b) == n, (hex(a), len(b), n)
        m[a:a + n] = b
    return m


def diff(m1, m2):
    bad = []
    for a, n in REG:
        for i in range(n):
            if m1[a + i] != m2[a + i]:
                bad.append(a + i)
    return bad


def main():
    nfr = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    ptype = int(sys.argv[2]) if len(sys.argv) > 2 else None
    L = ['r']
    if ptype is not None:
        L += ['w 3f4b0 %08x' % (ptype << 16)]   # type word at 4(A7), edge word 0 kept
    L += dump() + ['m 3f490 40', 'r', 'u b8fa 200000'] + dump()
    skip = int(os.environ.get('TRAIL_SKIP', '0'))   # jump over this many $12f84 calls first
    for f in range(nfr):
        if f == 0 and skip:
            L += ['bpc 12f84 %d 400000000' % skip] + dump() + ['u b7c8 3000000'] + dump()
        else:
            L += ['u 12f84 3000000'] + dump() + ['u b7c8 3000000'] + dump()
    L += ['q']
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', os.path.join(OUT, 'spawn.snap'), 'repl', '--disk-a', DISK],
                       input='\n'.join(L) + '\n', capture_output=True, text=True, cwd=R, env=env)
    blobs = parse(p.stdout)
    k = len(REG)
    pre = to_mem(blobs[0:k]); stk = blobs[k]; post = to_mem(blobs[k + 1:2 * k + 1])
    a7 = 0x3f4ac
    typ = int.from_bytes(stk[a7 + 4 - 0x3f490:a7 + 6 - 0x3f490], 'big')
    edge = int.from_bytes(stk[a7 + 6 - 0x3f490:a7 + 8 - 0x3f490], 'big')
    mm = bytearray(pre)
    mm[0x3f490:0x3f490 + 40] = stk
    slot = T.spawn_13372(mm, typ, edge, a7 - 4)
    bad = diff(mm, post)
    e = T.ENT + slot * T.ESZ
    print('spawn%s type %d edge %d -> slot $%x cell %d (x %d y %d): %s (%d bytes compared)'
          % (' POKED' if ptype is not None else '', typ, edge, slot, T.rsw(post, e + 8),
             T.rsw(post, e + 8) & 63, T.rsw(post, e + 8) >> 6,
             'MATCH' if not bad else 'MISMATCH at ' + ' '.join('%x' % a for a in bad[:10]),
             sum(n for _, n in REG)))
    good = alive = steps = kills = marks = 0
    fails = []
    i = 2 * k + 1
    prev = None; ran = 0
    for f in range(nfr):
        a = to_mem(blobs[i:i + k]); b = to_mem(blobs[i + k:i + 2 * k]); i += 2 * k
        hum = T.rsw(a, 0x3affe)
        if (prev is not None and T.rw(a, T.FRAME) == prev) or T.rl(a, 0x3b22e + 16 * hum) == 0:
            # `u 12f84` did not reach it: the game left the main loop (from spawn.snap the
            # computer wipes out the idle human side at frame 4291 -> score screen)
            print('game stopped simulating at frame %d (human population %d): %d $12f84 calls captured'
                  % (T.rw(a, T.FRAME), T.rl(a, 0x3b22e + 16 * T.rsw(a, 0x3affe)), f))
            break
        prev = T.rw(a, T.FRAME); ran += 1
        mm = bytearray(a)
        try:
            T.tick_12f84(mm)
            bad = diff(mm, b)
        except T.NotModelled as ex:
            bad = ['notmodelled ' + str(ex)]
        live = [s for s in (0xd1, 0xd2) if T.rw(a, T.ENT + s * T.ESZ + 4)]
        alive += bool(live)
        for s in live:
            if T.rw(a, T.ENT + s * T.ESZ + 12) >= 7: steps += 1
        kills += sum(1 for j in range(0xd1) if T.rw(a, T.ENT + j * T.ESZ + 4) and not T.rw(b, T.ENT + j * T.ESZ + 4))
        marks += sum(1 for c in range(4096) if a[0x36e78 + c] != b[0x36e78 + c] or a[0x3c522 + c] != b[0x3c522 + c])
        if os.environ.get('TRAIL_VERBOSE'):
            e = T.ENT + 0xd1 * T.ESZ
            print(f, 'frame', T.rw(a, T.FRAME), T.rw(b, T.FRAME), 'pop', T.rl(a, 0x3b22e), T.rl(a, 0x3b23e), 'pre', a[e:e + 22].hex(), 'post', b[e:e + 22].hex(), 'model', mm[e:e + 22].hex())
        if not bad:
            good += 1
        else:
            fails.append((f, [('%x' % x) if isinstance(x, int) else x for x in bad[:8]]))
    print('ticks: %d/%d frames match (every byte of %d); frames with a live trail %d, steps %d, '
          'cells re-marked %d, entities killed %d' % (good, ran, sum(n for _, n in REG), alive, steps, marks, kills))
    for f in fails[:10]:
        print('FAIL frame', f)
    if ptype is None or '--keep' in sys.argv:
        pass


if __name__ == '__main__':
    main()
