"""Gate: the two random-number routines, $f21e (32-bit shift/xor generator, returns the high word of its new state)
and $f23e (6-byte additive lagged generator with carry chain, returns the 16-bit word at 538(A6)) against Python
models, 200 random states each from the g_game1 snapshot.  Usage (from M68000/):
    python3 reversing/starglider/py/objects/rng_gate.py [--break]   # --break: control, one wrong constant
Expected: 'f21e 200/200', 'f23e 200/200' (and with --break both fail)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem

BREAK = '--break' in sys.argv
M32 = 0xffffffff
XORK = 0x1d872b41 ^ (1 if BREAK else 0)

def model_f21e(S, A92, c3ce):
    t = (S << 1) & M32
    carry = (S >> 31) & 1
    if carry or t == 0:                      # add.l D0,D0 / bhi not taken (C=1 or Z=1): eori
        t ^= XORK
    t = (t & 0xffff0000) | (((t & 0xffff) + c3ce) & 0xffff)   # add.w $c3ce.l,D0
    t = (t + A92) & M32                      # add.l 92(A6),D0
    return t                                 # new 100(A6); D0.w result = t >> 16

def model_f23e(b, d0, c3ce):
    """b = bytes 92..97 (list of 6). returns (new b, word at 538)."""
    b = list(b)
    s = (b[0] << 8 | b[1]) + ((d0 + (0 if BREAK else c3ce)) & 0xffff)      # add.w D0,92(A6): word at 92..93
    X = 1 if s > 0xffff else 0
    b[0] = (s >> 8) & 0xff; b[1] = s & 0xff
    def step(X):
        d0 = b[0]
        t = d0 + b[4] + X; X = t >> 8; d0 = t & 0xff        # addx.b 96(A6)
        t = d0 + b[5] + X; X = t >> 8; d0 = t & 0xff        # addx.b 97(A6)
        b[0] = d0
        b[5] = b[4]; b[4] = b[3]; b[3] = b[2]; b[2] = b[1]; b[1] = b[0]
        return d0, X
    r1, X = step(X)
    r2, X = step(X)
    return b, (r1 << 8) | r2

def main():
    random.seed(208)
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    lines = []; cases = []
    for k in range(200):
        S = random.getrandbits(32); A92 = random.getrandbits(32); c = random.getrandbits(16)
        if k < 8: S = [0, 0x80000000, 0x7fffffff, 0xffffffff, 0, 1, 0x80000000, 0][k]
        lines += ['w %x %x' % (A6 + 100, S), 'w %x %x' % (A6 + 92, A92), 'ww c3ce %x' % c,
                  'callcap f21e 200 A6=%x' % A6]
        cases.append((S, A92, c))
    out = ol.repl_run(snap, lines)
    cc = ol.parse_callcaps(out)
    ok = 0
    for (S, A92, c), r in zip(cases, cc):
        exp = model_f21e(S, A92, c)
        got = 0
        for i in range(4):
            a = A6 + 100 + i
            got = (got << 8) | (r['mem'][a][1] if a in r['mem'] else (S >> (24 - 8 * i)) & 0xff)
        d0 = r['regs']['D0'][1] & 0xffff
        ok += (got == exp and d0 == exp >> 16 and len(r['mem']) <= 4)
    print('f21e %d/%d' % (ok, len(cases)))
    lines = []; cases = []
    for k in range(200):
        bs = [random.getrandbits(8) for _ in range(6)]
        if k < 6: bs = [[0] * 6, [255] * 6, [0, 0, 0, 0, 0, 0], [255, 255, 0, 0, 255, 255], [1] * 6, [128] * 6][k]
        d0 = random.getrandbits(16); c = random.getrandbits(16)
        for i, v in enumerate(bs): lines.append('wb %x %x' % (A6 + 92 + i, v))
        lines += ['wb %x 0' % (A6 + 538), 'wb %x 0' % (A6 + 539), 'ww c3ce %x' % c,
                  'callcap f23e 200 A6=%x D0=%x' % (A6, d0)]
        cases.append((bs, d0, c))
    out = ol.repl_run(snap, lines)
    cc = ol.parse_callcaps(out)
    ok = 0
    for (bs, d0, c), r in zip(cases, cc):
        nb, w = model_f23e(bs, d0, c)
        got = [r['mem'][A6 + 92 + i][1] if (A6 + 92 + i) in r['mem'] else bs[i] for i in range(6)]
        gw = (r['mem'].get(A6 + 538, (0, 0))[1] << 8) | r['mem'].get(A6 + 539, (0, 0))[1]
        ok += (got == nb and gw == w and (r['regs']['D0'][1] & 0xffff) == w)
    print('f23e %d/%d' % (ok, len(cases)))
main()
