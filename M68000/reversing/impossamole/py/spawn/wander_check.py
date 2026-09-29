"""Live check of the wander rule `$0138dc` (D0 = 2) used by type 114 bees (README "Spawn types", item c).

    ATARI_NOTRACE=1 uv run python wander_check.py [snap]

`$138dc`: while 82(A0) > 0 it just counts down. At 0 it reloads 82(A0) = ((rand & 3) + 3) * 8 (24, 32, 40 or 48 frames) and,
in mode 2, picks index i = ($227aa >> 8) & 7, base speed D7 = 16(A0) (or 18(A0) when 16 is 0), and sets
16(A0) = tab[i].w0 * D7, 18(A0) = tab[i].w1 * D7 and the word 20(A0) (bytes 20 and 21) = tab[i].w2 from `$00ba8e`
(eight compass headings); the animation pointer is reloaded from entry 20(A0). The script stops at `$013928` (index and D7
in registers, i from `$227aa`), then at `$013946` (after the word moves), and compares 16/18/20/21 with the table.
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trigger_scan import regs

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/impossamole/pass103/live_c20.snap'
S = lambda b, k: struct.unpack_from('>h', b, k)[0]
TAB = [(1, 0, 0x0100), (1, 1, 0x0101), (0, 1, 0x0001), (1, 1, 0x0001), (1, 0, 0), (1, 1, 0), (0, 1, 0), (1, 1, 0x0100)]

with Repl(snap) as r:
    r.run('w bb74 12120300')
    ok = n = 0
    seen, reloads = [], []
    for _ in range(30):
        out = r.run('s 1', 'bp 13928 4000000')
        g = regs(out)
        if g.get('PC') != 0x13928:
            break
        a = g['A0']
        i, d7 = g['D0'] & 0xffff, g['D7'] & 0xffff
        # D0 was set from ($227aa >> 8) & 7 at $1391a; check it against RAM as well
        r.run('s 1', 'bp 13946 900000')
        obj = r.mem(a, 108)
        w0, w1, w2 = TAB[i]
        want = (w0 * d7, w1 * d7, w2 >> 8, w2 & 0xff)
        rel = obj[82:84].hex()
        got = (S(obj, 16), S(obj, 18), obj[20], obj[21])
        n += 1
        ok += want == got
        seen.append(i)
        reloads.append(struct.unpack_from('>H', obj, 82)[0])
        if want != got:
            print('MISMATCH obj', hex(a), 'index', i, 'D7', d7, 'want', want, 'got', got)
    print(f'{snap}: {ok}/{n} direction picks match tab[i]*speed; indices seen {sorted(set(seen))}; 82(A0) reloads {sorted(set(reloads))} (24/32/40/48 expected)')
