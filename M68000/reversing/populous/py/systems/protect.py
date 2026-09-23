"""protect.py - the three key checks, live.

All three compare against $54ac0842, the immediate the crack's loader patches into the two
Supexec routines $16014/$17a1c (both `move.l #imm,D0; move.l D0,$24`, i.e. they also point the
trace vector at it):
  A  $e18a  (entity loop, index 20):  $3c4c0 == $21d4c + $14725836
  B  $edc6  (entity loop, index 18):  peek($24) via $15fe2 == 2 * $21d54
  C  $135ae (trail spawn $13372):     $3c4b4 == $21d58 + $12312378
1. natural: late4.snap (58 entities) for 20 frames, `hits` on each compare and each failure branch.
2. forced: poke the key word wrong and run, then read $3d524 (armageddon), both god_rec ctrl words,
   the frame counter and the trail slots.
"""
import os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import WORK, OUT, R, DLL, DISK

env = dict(os.environ, ATARI_NOTRACE='1')


def repl(snap, L):
    return subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                          input='\n'.join(L + ['q']) + '\n', capture_output=True, text=True, cwd=R, env=env).stdout


def hexlines(out):
    return [bytes(int(x, 16) for x in l.split()) for l in out.splitlines()
            if l.split() and all(re.fullmatch('[0-9a-f]{2}', x) for x in l.split())]


STATE = ['m 3d524 2', 'r', 'm 21e12 2', 'r', 'm 21e40 2', 'r', 'm 3c4c8 2', 'r', 'm 3c472 2', 'r', 'm 3c488 2', 'r']


def show(tag, out):
    v = [int.from_bytes(b, 'big') for b in hexlines(out)][-6:]
    print('%-44s armageddon %d  ctrl0 %d ctrl1 %d  frame %d  slot d1 str %d  d2 str %d' % ((tag,) + tuple(v)))
    return v


def main():
    late = os.path.join(WORK, 'late4.snap')
    out = repl(late, ['hits %d e18a e1a0 edc6 edda 135ae 135c4' % (20 * 170000)])
    print(out[out.index('--- hits'):].strip())
    show('natural late4 +20 frames', repl(late, ['s %d' % (20 * 170000)] + STATE))
    show('A: $3c4c0 poked 0, +2 frames', repl(late, ['w 3c4c0 00000000', 's 340000'] + STATE))
    show('B: trace vector $24 poked 0, +2 frames', repl(late, ['w 24 00000000', 's 340000'] + STATE))
    sp = os.path.join(OUT, 'spawn.snap')
    show('C natural: spawn.snap to $b8fa', repl(sp, ['u b8fa 200000'] + STATE))
    show('C: $3c4b4 poked 0, to $b8fa', repl(sp, ['w 3c4b4 00000000', 'u b8fa 200000'] + STATE))
    show('C: $3c4b4 poked 0, +3 frames', repl(sp, ['w 3c4b4 00000000', 'u b8fa 200000', 's 510000'] + STATE))


if __name__ == '__main__':
    main()
