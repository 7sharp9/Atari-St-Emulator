"""Gate for the hex printer $f60e (D0.w -> four ASCII hex digits at (A1)+) and its digit routine $f634 (low nibble of D1.w -> one digit at (A1)+,
'0'..'9', 'A'..'F').   python3 gate_text.py [n]    --control: digit offset $37 instead of $07 (lower-case would be $27)
Random D0 / D1 by preset, A1 = $5d800 (scratch RAM inside the BSS).  Compared: the memory delta outside the stack and exit A1.  Expected: `hex $f60e n/n`, `digit $f634 n/n`."""
import os, sys, random
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
random.seed(3)
ram = R.load_ram(R.SNAP_GAME2); OUT = R.WORK + '/render/caps'
ADJ = 0x37 if '--control' in sys.argv else 0x07
def digit(d):
    d &= 0xF
    if d > 9: d += ADJ
    return (d + 0x30) & 0xFF
def check(name, addr, mk, ref):
    cases = [mk() for _ in range(n)]
    res = R.cc_jobs(R.SNAP_GAME2, [dict(addr=addr, presets=dict(A6=0x5bf00, A1=0x5d800, **c)) for c in cases], OUT, name, steps=5000)
    ok = 0
    for c, j in zip(cases, res):
        want, a1 = ref(c)
        stack = (j['entrySP'] - 512, j['entrySP'] + 16)
        got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
        want = {0x5d800 + i: v for i, v in enumerate(want) if ram[0x5d800 + i] != v}
        ok += got == want and j['regN'][9] == 0x5d800 + a1
    print(f'{name} {ok}/{len(cases)}')
check('hex_f60e', 0xf60e, lambda: dict(D0=random.randrange(1 << 16)), lambda c: ([digit(c['D0'] >> s) for s in (12, 8, 4, 0)], 4))
check('digit_f634', 0xf634, lambda: dict(D1=random.randrange(1 << 16)), lambda c: ([digit(c['D1'])], 1))
