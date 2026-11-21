"""Gate for the screen clear $1455c (reached through the jump vector 64(A6) from $14556): rows y = 10..128, bytes 8..151 of each 160-byte row
(x 16..303, all four planes) are zeroed and nothing else.  Natural entries from g_game2 (every 3rd hit), the reference predicts the changed bytes
from the snapshot RAM (a byte already zero is not a change).   python3 gate_clear.py [n]   Expected: `clear $1455c n/n`."""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
ROWS = (10, 128) if '--control' not in sys.argv else (10, 127)
OUT = R.WORK + '/render/caps/clr'
hits = [1 + 3 * i for i in range(n)]
R.cap_calls(R.SNAP_GAME2, 0x1455c, hits, OUT, 'c', callcap_steps=100000)
ok = 0
for h in hits:
    j = json.load(open(f'{OUT}/c_{h}.json')); ram = R.load_ram(f'{OUT}/c_{h}.snap')
    scr = int.from_bytes(ram[0x5bf00:0x5bf04], 'big')
    want = {}
    for y in range(ROWS[0], ROWS[1] + 1):
        for b in range(8, 152):
            a = scr + 160 * y + b
            if ram[a]: want[a] = 0
    stack = (j['entrySP'] - 512, j['entrySP'] + 16)
    got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
    ok += got == want
print(f'clear $1455c {ok}/{len(hits)}   (cleared bytes in the first capture: {len(got)})')
os.system(f'rm -f {OUT}/c_*.snap')
