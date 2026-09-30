"""refs.py - list every reference to a global A4 offset in the whole-TEXT listing (ss.asm), with the
containing function (nearest preceding `link A6`) and the surrounding instructions.

    uv run python refs.py -3874 [-3882 ...] [--ctx 6] [--w]   # --w: only instructions after which the
                                                              # value is plausibly written (lea forms are shown too)

Matches `-N(A4)` textually (both direct `move.w D0,-N(A4)` and `lea -N(A4),An`).  Indexed arrays are
addressed as `lea -N(A4),A0 / adda.w D0,A0 / <op> (A0)`, so the lea site is the reference; read its
following ~6 instructions for the access type (--ctx).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sscfg  # noqa

ASM = os.path.join(sscfg.WORK, 'ss.asm')
LINE = re.compile(r'^\s+\$([0-9a-f]{6}): (.*)$')


def load():
    ins = []
    for l in open(ASM):
        m = LINE.match(l)
        if m:
            a = int(m.group(1), 16)
            if a < 0x1bfd0:
                ins.append((a, m.group(2).rstrip()))
    return ins


def funcs(ins):
    starts = [a for a, t in ins if t.startswith('link A6')]
    return starts


def func_of(starts, a):
    best = None
    for s in starts:
        if s <= a:
            best = s
        else:
            break
    return best


def main():
    args = sys.argv[1:]
    ctx = 6
    if '--ctx' in args:
        i = args.index('--ctx')
        ctx = int(args[i + 1])
        del args[i:i + 2]
    only_w = '--w' in args
    args = [a for a in args if a != '--w']
    ins = load()
    st = funcs(ins)
    for off in args:
        pat = re.compile(r'(?<![\d-])' + re.escape(str(int(off))) + r'\(A4\)')
        print('=== %s(A4) ===' % off)
        for i, (a, t) in enumerate(ins):
            if pat.search(t):
                f = func_of(st, a)
                print('  $%06x [fn $%06x] %s' % (a, f or 0, t))
                if not only_w or 'lea' in t:
                    for j in range(i + 1, min(i + 1 + ctx, len(ins))):
                        print('       $%06x %s' % ins[j])


if __name__ == '__main__':
    main()
