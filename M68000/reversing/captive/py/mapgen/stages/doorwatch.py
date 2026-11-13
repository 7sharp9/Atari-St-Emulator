"""Who writes the compound door list at federation 2330(A6) = $1beee (8 entries of cell word, state word)?

    uv run python -I reversing/captive/py/mapgen/stages/doorwatch.py shortcut d0,d1,d2,d3
    uv run python -I reversing/captive/py/mapgen/stages/doorwatch.py natural <snap stopped at $b5c2> [steps]

shortcut: gen.py's call of fed_MapGen's body ($20054, labelled register pokes) with a CPU write watch on
$1beee..$1bf0d; prints every write (step, writer PC, address, value) and the list at the return.
natural: from a snapshot stopped at federation's `jsr 32(A4)` ($b5c2), runs `steps` instructions of play with the same
watch (no pokes) and prints every write with its PC, then the list.
"""
import os
import sys


def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = root()
sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen'))
from gen import start  # noqa: E402
from stclient import StServer  # noqa: E402

LO, HI = 0x1b5ce + 2330, 0x1b5ce + 2330 + 31


def show(s, wid):
    ev = s('watch_events', id=wid)[0]
    for e in ev['events']:
        print(e)
    print('dropped', ev['dropped'])
    b = s.read(LO, 32)
    print('list at end:', b.hex(' ', 2))


def main():
    s = StServer(R)
    try:
        if sys.argv[1] == 'shortcut':
            d0, d1, d2, d3 = [int(x, 0) for x in sys.argv[2].split(',')]
            # the watch must exist before the call runs: load first, then add, then call
            from gen import SNAP, ENTRY, RET
            s('load', snapshot=SNAP)
            wid = s('watch_add', lo=LO, hi=HI, kind='w', source='cpu')['id']
            s.call(ENTRY, ret=RET, max_steps=60_000_000, d0=d0, d1=d1, d2=d2, d3=d3, d4=0xFFFFFFFF,
                   a0=0x1d9e8, a1=0xb532, a2=0x303c)
            show(s, wid)
        else:
            snap = sys.argv[2]
            steps = int(sys.argv[3]) if len(sys.argv) > 3 else 3_000_000
            s('load', snapshot=snap)
            wid = s('watch_add', lo=LO, hi=HI, kind='w', source='cpu')['id']
            r = s('run', max_steps=steps)
            print('run', r['reason'], r['steps'])
            show(s, wid)
    finally:
        s.close()


if __name__ == '__main__':
    main()
