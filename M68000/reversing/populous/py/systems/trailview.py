"""trailview.py - rendered frames of a live trail effect, checked against the game's own frame.

  python trailview.py <type> <skip> <n> [snap]

From systems/spawn.snap (stopped at the frame-$1000 spawn, type 2 natural; with type 0 or 1 the
pushed type word is POKED as in trailrun.py), run `skip` frames, then for n frames: at the end of
the trail tick ($b7c8) point the view at the trail (POKED: cx $37e7a / cy $249ae := cell x-3 / y-3,
clamped 0..56), snapshot at the next $14364 entry (pre) and $16ed8 entry (post), and render with
pop_render.py --truth. Prints per frame the trail's sprite frame (+6) and the pixel match.
Snapshots and PNGs go to $POP_WORK/systems/view/t<type>_<frame>.
"""
import os, sys, subprocess
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'powers')))
from pwlib import Repl2, rw, rsw
from popcfg import WORK
PY = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(WORK, 'systems', 'view'); os.makedirs(OUT, exist_ok=True)
ENT, ESZ = 0x3b278, 0x16


def main():
    typ, skip, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    snap = os.path.abspath(sys.argv[4]) if len(sys.argv) > 4 else os.path.join(WORK, 'systems', 'spawn.snap')
    r = Repl2(snap)
    _, regs = r.cmd('m 0 2')                               # (cmd('r') would print the registers twice)
    if typ != 2:
        r.cmd('w %x %08x' % (regs['A7'] + 4, typ << 16))
    r.cmd('u b8fa 200000')                                 # the spawn's return in $b8e8
    for _ in range(skip):
        r.cmd('u 12f84 3000000'); r.cmd('u b7c8 3000000')
    for k in range(n):
        _, regs = r.cmd('u b7c8 3000000')
        e = r.mem(ENT + 0xd1 * ESZ, ESZ)
        if rsw(e, 4) == 0:
            print('trail gone'); break
        cell = rw(e, 8)
        cx, cy = min(max((cell & 63) - 3, 0), 56), min(max((cell >> 6) - 3, 0), 56)
        r.cmd('w 37e7a %08x' % ((cx << 16) | rw(r.mem(0x37e7c, 2), 0)))
        r.cmd('w 249ae %08x' % ((cy << 16) | rw(r.mem(0x249b0, 2), 0)))
        _, regs = r.cmd('u 14364 3000000')
        e = r.mem(ENT + 0xd1 * ESZ, ESZ)
        fr = rw(r.mem(0x3c4c8, 2), 0)
        base = os.path.join(OUT, 't%d_%d' % (typ, fr))
        r.cmd('snap %s_pre.snap' % base)
        r.cmd('u 16ed8 3000000')
        r.cmd('snap %s_post.snap' % base)
        p = subprocess.run([sys.executable, os.path.join(PY, 'pop_render.py'), base + '_pre.snap', base + '.png',
                            '--post', base + '_post.snap', '--truth'], capture_output=True, text=True)
        match = [l for l in p.stdout.splitlines() if 'match' in l.lower()]
        print('frame %d type %d cell %d (x %d y %d) view (%d,%d) sprite frame %d: %s'
              % (fr, e[20], rw(e, 8), rw(e, 8) & 63, rw(e, 8) >> 6, cx, cy, rw(e, 6),
                 match[-1] if match else p.stdout.strip()[-200:] + p.stderr.strip()[-300:]), flush=True)
    r.close()


if __name__ == '__main__':
    main()
