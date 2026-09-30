"""PRNG A ($bef4): exact recurrence + check against the live emulator (bp $bef4 / bp $bf58 over many calls).
State: s=$227aa; VBL counters c1=$227ac (+1 per VBL), c2=$227ae (+2), c3=$227b0 (+3), c4=$227b2 (+4) ($beda, called from the VBL handler $1a2c0).
The X flag at entry feeds the first addx (movem/move do not touch X, ror does not affect X), so the caller's X is an input."""
import sys, re
sys.path.insert(0, __file__.rsplit('/', 1)[0])
M = 0xffff
def ror1(v): return ((v >> 1) | ((v & 1) << 15)) & M
def bef4(s, c1, c2, c3, c4, x):
    d = s
    for c in (c4, c2, c3, c1):            # addx.w with $227b2, $227ae, $227b0, $227ac
        t = d + c + x
        x = 1 if t > M else 0
        d = t & M
        d = ror1(d)
    for c in (c3, c1, c4, c2):            # eor.w with $227b0, $227ac, $227b2, $227ae
        d ^= c
        d = ror1(d)
    return d                              # written to $227aa and returned in D7.w
def vbl(c):                               # $beda
    return ((c[0] + 1) & M, (c[1] + 2) & M, (c[2] + 3) & M, (c[3] + 4) & M)

def parse_regs(lines):
    d = {}
    for l in lines:
        for m in re.finditer(r'([DA]\d):([0-9a-f]{8})', l):
            d[m.group(1)] = int(m.group(2), 16)
        if l.startswith('CCR:'):
            d['CCR'] = int(l.split()[1], 2)
    return d

if __name__ == '__main__':
    from repl import Repl
    snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    r = Repl(snap)
    ok = bad = 0
    xs = {0: 0, 1: 0}
    callers = {}
    for i in range(N):
        out = r.cmd('bp bef4 3000000')
        if not any('reached' in l or 'hit' in l for l in out) and not any(l.startswith('PC:') and 'bef4' in l for l in out):
            pass
        regs = parse_regs(out)
        x_in = (regs['CCR'] >> 4) & 1
        st = r.mem(0x227aa, 10)
        s, c1, c2, c3, c4 = [int.from_bytes(st[j:j+2], 'big') for j in range(0, 10, 2)]
        ret = int.from_bytes(r.mem(0, 0), 'big') if False else None
        # return address on the stack (A7) = caller
        a7 = regs['A7']; ra = int.from_bytes(r.mem(a7, 4), 'big')
        callers[ra] = callers.get(ra, 0) + 1
        pred = bef4(s, c1, c2, c3, c4, x_in)
        out2 = r.cmd('bp bf58 100')
        regs2 = parse_regs(out2)
        s_new = r.w(0x227aa)
        got = regs2['D7'] & M
        if pred == s_new == got: ok += 1
        else:
            bad += 1
            print('MISMATCH', i, hex(ra), (s, c1, c2, c3, c4, x_in), 'pred', hex(pred), 'state', hex(s_new), 'D7', hex(got))
        xs[x_in] += 1
        r.cmd('s 1')
    print(f'{ok} match / {ok+bad} calls;  X_in distribution {xs};  callers { {hex(k): v for k, v in sorted(callers.items())} }')
    r.close()
