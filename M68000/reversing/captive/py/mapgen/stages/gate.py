"""Gate each post-dig stage model against the emulator, stage by stage, from dumpall.py's dumps.

    uv run python -I reversing/captive/py/mapgen/stages/gate.py <lo> <hi> [d2 ...] [--stage 2533a] [--break name=value]

Each stage's model starts from the emulator's own state just before that stage (module variables at A6 = $20376
and federation's block $1bd3e..$1d9e8) and must reproduce the state after it byte for byte: the whole module block
(G0, G1, G2, lists, counters, RNG seed) and the federation block. Per stage it prints the cases matched exactly and
the G0/G1 bytes that differ in total. --break sets one model constant (models.K) for a broken-model control.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import STAGES, load  # noqa: E402
import models  # noqa: E402


def main():
    args = sys.argv[1:]
    only = None
    if '--stage' in args:
        i = args.index('--stage')
        only = int(args[i + 1], 16)
        del args[i:i + 2]
    while '--break' in args:
        i = args.index('--break')
        name, val = args[i + 1].split('=')
        v = eval(val, {})
        models.K[name] = v
        del args[i:i + 2]
    lo, hi = int(args[0]), int(args[1])
    d2s = [int(a) for a in args[2:]] or [1, 0]
    cache = {(d2, d0): load(d2, d0) for d2 in d2s for d0 in range(lo, hi)}
    for idx, (stop, callee) in enumerate(STAGES):
        f = models.MODELS_BY_STOP.get(stop) or models.MODELS.get(callee)
        if f is None or (only is not None and callee != only):
            continue
        ok = tot = bad = acted = 0
        first_bad = None
        for (d2, d0), recs in cache.items():
            _, m0, f0 = recs[idx - 1]
            _, m1, f1 = recs[idx]
            S = models.State(bytearray(m0), bytearray(f0))
            try:
                f(S)
            except Exception as e:  # a model reading outside the dumped blocks: count as a miss and say so
                print(f'  ${callee:x} d2={d2} d0={d0}: {type(e).__name__} {e}')
                tot += 1
                continue
            dm = [i for i in range(len(m1)) if S.b[i] != m1[i]]
            df = [i for i in range(len(f1)) if S.f[i] != f1[i]]
            tot += 1
            acted += m0 != m1 or f0 != f1
            bad += len(dm) + len(df)
            if not dm and not df:
                ok += 1
            elif first_bad is None:
                first_bad = (d2, d0, dm[:8], df[:8])
        print(f'stage {idx:2d} ${callee:x} (stop ${stop:x}): exact {ok}/{tot} cases ({acted} where the stage changed state), bytes differing {bad}'
              + (f'; first miss d2={first_bad[0]} d0={first_bad[1]} module {first_bad[2]} fed {first_bad[3]}'
                 if first_bad else ''))


if __name__ == '__main__':
    main()
