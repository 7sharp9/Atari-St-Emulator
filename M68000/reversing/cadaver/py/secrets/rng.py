"""rng.py: Cadaver's random number generator, engine export service 16 = $011544 (mechanics: earlier "no RNG" counts missed it because the
LCG is built from shifts, no mul).  Seed = word at 1134(A5) ($0185c0):
    s' = 4*(((s & $ff) << 8 | $0a) - s) + s + 1  (mod 2^16);  s' = 1 if 0
    RANDOM(D1..D2):  n = D2 - D1 + 1;  d = $ffff // n + 1;  result = D1 + s' // d
(`divu` semantics: 16-bit unsigned quotient).  Start gameplay_empire.snap: for 40 seeds, poke the seed word, `callcap $011544 100000 - D1=lo D2=hi`
and compare the returned D0 with this transcription.
    uv run python reversing/cadaver/py/secrets/rng.py"""
import re, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *

def step(s):
    s = (4 * ((((s & 0xff) << 8) | 0x0a) - s) + s + 1) & 0xffff
    return s or 1

def rnd(s, lo, hi):
    s = step(s); n = hi - lo + 1; d = (0xffff // n) + 1
    return lo + s // d, s

if __name__ == '__main__':
    r = Repl(); seed_addr = A5 + 1134
    nxt = r.mem(seed_addr + 2, 2).hex()
    ok = n = 0
    for i, s in enumerate([1, 2, 0x14f6, 0xffff, 0x8000, 0x00ff, 0x0100] + [(i * 2654435761) & 0xffff for i in range(33)]):
        lo, hi = (0, 63) if i % 2 == 0 else (5, 9)
        out = r.cmd(f'w {seed_addr:x} {s:04x}{nxt}', f'callcap 11544 100000 - D1={lo:x} D2={hi:x}')
        d0 = next(int(m.group(1), 16) for l in out if (m := re.search(r'D0 \$[0-9a-f]{8}->\$([0-9a-f]{8})', l)))
        exp, s2 = rnd(s, lo, hi)
        n += 1; ok += (d0 == exp)
        if d0 != exp: print('MISMATCH seed %04x range %d-%d: game %d python %d' % (s, lo, hi, d0, exp))
    print(f'{ok}/{n} results match')
    r.close()
