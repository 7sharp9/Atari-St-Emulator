"""Command 14 sub 15 (`$3c4e4`, the capacity-50 hook, mechanics.md 7) run live from a labelled poke.

    uv run python reversing/populous/py/hooks/sub15_poke.py [frames]      (from M68000/)

No code in the shipped program posts sub 15 on one machine (mechanics.md 7, the +2 writer census); a serial peer
could, through `$183b4`. This stands in for that peer: from game_start.snap it runs to the dispatcher `$1e712`, pokes
side s's command record ($21e0c + $2e*s, the bytes `$183b4` would unpack) to cmd 14, arg a, sub 15, and runs `frames`
frames. Trials: no poke (control), arg 0, arg 1 on side 0's record, arg 0 on side 1's record. Counted: `$1fbbe` (sub 15),
every CPU write to `$3c4e4` with its PC, `$e65e` (a settlement of side `$3c4e4`-1 given capacity 50), `$ef28` (the
"CHEAT" print at the tail of `$db4c`) and `$16ed8` (frames).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from popcfg import R, WORK, DISK  # noqa: E402
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer  # noqa: E402

REC, HOOK = 0x21e0c, 0x3c4e4
SITES = {0x1fbbe: 'sub15', 0xe65e: 'cap50', 0xef28: 'cheat_print', 0x16ed8: 'frames'}
FRAME = 104000                              # steps per game frame on game_start (23 frames in 2.4M steps)


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 23
    s = StServer(R)
    s('load', snapshot=os.path.join(WORK, 'game_start.snap'), disk=DISK)
    r = s('run', max_steps=400000, until_pc=0x1e712)
    if r['reason'] != 'until':
        sys.exit(f'$1e712 not reached: {r}')
    fork = s('fork')['id']
    s('watch_add', lo=HOOK, hi=HOOK + 1, kind='w', source='cpu')
    trials = [('control (no poke)', None), ('side 0 rec, arg 0', (0, 0)), ('side 0 rec, arg 1', (0, 1)),
              ('side 1 rec, arg 0', (1, 0))]
    for name, poke in trials:
        s('restore', id=fork)
        s('watch_events')
        if poke:
            side, arg = poke
            a = REC + 0x2e * side
            rest = s.read(a + 3, 1)[0]
            s('poke', addr=a, width=4, value=(0x0e << 24) | (arg << 16) | (0x0f << 8) | rest)
        h = s('hits', steps=frames * FRAME, addrs=list(SITES))
        counts = {SITES[int(x['addr'].lstrip('$'), 16)]: x['count'] for x in h['hits']}
        ev = s('watch_events')[0]['events']
        writes = [(e['pc'], e['value']) for e in ev]
        set_by = [w for w in writes if w[0] == '$01fbc4']
        print(f'{name:20s} {counts}  $3c4e4 writes: {len(set_by)} set {set_by}, '
              f'{len(writes) - len(set_by)} clears at {sorted({w[0] for w in writes if w[0] != "$01fbc4"})}')
    s.close()


if __name__ == '__main__':
    main()
