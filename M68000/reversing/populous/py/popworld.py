"""popworld.py - Populous (Atari ST) world names, name->number, LEVEL.DAT decode, conquest progression.
  name(n)      = $1d0e6/$1d5fc : seed=n; v=rand(); A[v&31]+B[(v>>5)&31]+C[(v>>10)&31]; n==0 -> 'GENESIS'
  number(name) = $1d714        : first n in 0,5,..,5000 whose rand(seed=n) equals the name's code
  level(n)     = $1a5c4        : LEVEL.DAT record n//25 (10 bytes) -> $22ad8
  next_world(n, score) = $1d0e6"""
import os
from popmem import img, l, cstr
m = img()
A = [cstr(m, l(m, 0x21d64+4*i)) for i in range(32)]
B = [cstr(m, l(m, 0x21f7c+4*i)) for i in range(32)]
C = [cstr(m, l(m, 0x21efc+4*i)) for i in range(32)]
def rand1(seed): return (seed*0x24a1 + 0x24df) & 0x7fff
def name(n):
    if n == 0: return 'GENESIS'
    v = rand1(n)
    return A[v & 31] + B[(v >> 5) & 31] + C[(v >> 10) & 31]
def number(s):
    if s == 'GENESIS': return 0
    for i, a in enumerate(A):          # greedy prefix match, table order, exactly as $1d714
        if s.startswith(a): break
    else: return -1
    s2 = s[len(a):]
    for j, b in enumerate(B):
        if s2.startswith(b): break
    else: return -2
    s3 = s2[len(b):]
    for k, c in enumerate(C):
        if s3.startswith(c): break
    else: return -3
    if len(a)+len(b)+len(c) != len(s): return -4
    code = k << 10 | j << 5 | i
    for n in range(0, 5001, 5):
        if rand1(n) == code: return n
    return -5
LEVEL = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'LEVEL.DAT'), 'rb').read()
POW = ['EARTHQUAKE', 'SWAMP', 'KNIGHT', 'VOLCANO', 'FLOOD', 'ARMAGEDDON?']
TYPES = ['GRASS PLANES', 'DESERT', 'SNOW AND ICE', 'ROCKY']
SPEED = ['VERY SLOW', 'SLOW', 'MEDIUM', 'FAST', 'VERY FAST']
RATING = ['VERY POOR', 'POOR', 'AVERAGE', 'GOOD', 'VERY GOOD']
def level(n):
    r = LEVEL[(n//25)*10:(n//25)*10+10]
    f = r[4]
    build = ('CANNOT BE BUILT' if f & 4 else 'BUILT JUST ON TOWNS' if f & 0x10 else
             'ONLY BUILT UP' if f & 8 else 'BUILT ON PEOPLE')
    return dict(rec=n//25, raw=r.hex(), his_rating_raw=r[0], his_rating=RATING[(10-r[0])//2],
                his_reactions_raw=r[1], his_reactions=SPEED[(10-r[1])//2],
                his_powers=[POW[b] for b in range(6) if r[2] >> b & 1],
                your_powers=[POW[b] for b in range(6) if r[3] >> b & 1],
                flags=f, land=build, swamps='BOTTOMLESS' if f & 2 else 'SHALLOW',
                water='FATAL' if f & 1 else 'HARMFUL', landscape=TYPES[r[5]] if r[5] < 4 else r[5],
                your_pop=r[6], his_pop=r[7], seed_base=r[8] << 8 | r[9],
                seed=((r[8] << 8 | r[9]) + (n & 7)) & 0xffff)
def next_world(n, score):
    """$1d0e6: returns (new_world, game_complete)"""
    q = int(score / 5000) if score >= 0 else -int(-score / 5000)   # ldiv_stk truncates toward zero
    n2 = (n + q + 1) & 0xffff
    if n2 >= 0x8000: n2 -= 0x10000
    if n2 % 5: n2 += 5 - (n2 % 5)          # (divs remainder; n2 >= 0 in practice)
    if n2 > 2470:
        return (0, True) if n == 2470 else (2470, False)
    return n2, False
if __name__ == '__main__':
    import sys
    for a in sys.argv[1:]:
        n = int(a) if a.isdigit() else number(a.upper())
        print(n, name(n) if n >= 0 else '?', level(n) if n >= 0 else '')
