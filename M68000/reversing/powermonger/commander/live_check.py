"""live_check.py - does an A* waypoint get a type-(b) stuck man moving where his straight order does not?

From one snapshot, two arms with the same step budget (`s <chunk>` repeated, the record dumped after each):
  control : unchanged
  poked   : target words 20/22 := the first waypoint of astar.Map.path from his position at his speed
            (one `w` of the longword at record+20, which is exactly words 20 and 22)
The record is read back after every chunk; reported per arm: the closest approach to the waypoint and to the
original target, the final position and mode, and the chunk at which the poked arm first stood within
`--near` world units of the waypoint.

Usage (from M68000/): uv run python reversing/powermonger/commander/live_check.py <snap> <obj> [--chunks 30]
       [--chunk 1000000] [--near 128] [--wp k]   (--wp: use the k-th waypoint instead of the first)
Work files: $CMD_WORK/live (default scratchpad/cmd1)."""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astar  # noqa: E402

ROOT = astar.ROOT
WORK = Path(os.environ.get('CMD_WORK', ROOT / 'scratchpad' / 'cmd1')) / 'live'
WORK.mkdir(parents=True, exist_ok=True)
DLL = ROOT / 'bin' / 'Debug' / 'net8.0' / 'M68000.dll'


def opt(name, d):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else d


def run_arm(snap, tag, pokes, rec, chunks, chunk):
    repl = WORK / (tag + '.repl')
    with open(repl, 'w') as f:
        f.write('disk scratchpad/powermonger.st\n')
        for a, v in pokes:
            f.write('w %x %08x\n' % (a, v))
        f.write('m %x 50\n' % rec)
        for _ in range(chunks):
            f.write('s %d\nm %x 50\n' % (chunk, rec))
        f.write('q\n')
    env = dict(os.environ, ATARI_NOTRACE='1')
    out = WORK / (tag + '.out')
    with open(repl) as fi, open(out, 'w') as fo, open(WORK / (tag + '.err'), 'w') as fe:
        subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(snap), 'repl'], stdin=fi, stdout=fo, stderr=fe,
                       cwd=ROOT, env=env, check=False)
    recs = []
    for ln in open(out).read().splitlines():          # `m <addr> 50` prints one line of 50 hex bytes
        if re.fullmatch(r'([0-9a-f]{2} ){49}[0-9a-f]{2}', ln.strip()):
            recs.append(bytes.fromhex(ln.strip()))
    return recs


def sw(b, o):
    return int.from_bytes(b[o:o + 2], 'big', signed=True)


def main():
    snap, obj = sys.argv[1], int(sys.argv[2])
    chunks, chunk, near, k = opt('--chunks', 30), opt('--chunk', 1000000), opt('--near', 128), opt('--wp', 0)
    rec = 0x51b66 + 50 * obj
    mp = astar.Map(ROOT / snap)
    r = mp.ram
    s = (sw(r, rec + 8), sw(r, rec + 10))
    t = (sw(r, rec + 20), sw(r, rec + 22))
    speed = r[rec + 16]
    ok, _p, why = mp.leg(s, t, speed)
    wps, ver = mp.path(s, t, speed)
    print('obj%d rec $%x side %d mode %02x prev %02x speed %d pos %s target %s straight leg %s'
          % (obj, rec, r[rec + 5], r[rec + 31], r[rec + 30], speed, s, t, 'walkable' if ok else 'blocked %s' % (why,)))
    print('path (%s): %s' % ('verified' if ver else 'unverified', wps))
    wp = wps[k]
    v = ((wp[0] & 0xffff) << 16) | (wp[1] & 0xffff)
    print('model: from %s the tick model says straight %s, to the waypoint %s'
          % (s, mp.simulate_walk(s, t, speed, 3000)[:2], mp.simulate_walk(s, wp, speed, 3000)[:2]))
    tag = '%s_obj%d' % (Path(snap).stem, obj)
    res = {}
    for arm, pokes in (('control', []), ('poked', [(rec + 20, v)])):
        recs = run_arm(snap, tag + '_' + arm, pokes, rec, chunks, chunk)
        assert len(recs) == chunks + 1, '%s: parsed %d record dumps, expected %d' % (arm, len(recs), chunks + 1)
        dwp = [max(abs(sw(b, 8) - wp[0]), abs(sw(b, 10) - wp[1])) for b in recs]
        dt = [max(abs(sw(b, 8) - t[0]), abs(sw(b, 10) - t[1])) for b in recs]
        first = next((i for i, d in enumerate(dwp) if d <= near), None)
        b = recs[-1]
        res[arm] = (min(dwp), first)
        print('%-7s start pos (%d,%d) tgt (%d,%d) | end pos (%d,%d) tgt (%d,%d) mode %02x prev %02x | min dist to wp %d '
              '(first <= %d at chunk %s) | min dist to original target %d'
              % (arm, sw(recs[0], 8), sw(recs[0], 10), sw(recs[0], 20), sw(recs[0], 22), sw(b, 8), sw(b, 10),
                 sw(b, 20), sw(b, 22), b[31], b[30], min(dwp), near, first, min(dt)))
        print('        trajectory (cells): ' + ' '.join('(%d,%d)' % (sw(x, 8) >> 8, sw(x, 10) >> 8) for x in recs))
    print('RESULT poked reaches waypoint: %s; control reaches it: %s'
          % (res['poked'][1] is not None, res['control'][1] is not None))


if __name__ == '__main__':
    main()
