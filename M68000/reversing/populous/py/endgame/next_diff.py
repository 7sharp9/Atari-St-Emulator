"""next_diff.py - the conquest next-world step of $1d0e6 ($1d0e6..$1d18e) vs popworld.next_world/name.

From win_next_entry.snap (stopped at $1d0e6 entry, reached by clicking NEW GAME on a real won
score screen), each case pokes the old world $3c51a and the score argument (long at 4(A7)),
runs to $1d18e (after the name is built) and reads $3c51a, the name $37e86 and the conquered
flag -122(A6). One REPL process per case (the step to $1d18e is ~400 instructions).

usage: python next_diff.py [N] [seed]"""
import random, sys
from concurrent.futures import ThreadPoolExecutor
from eg import *
PW = import_popworld()

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
SRC = OUT + '/win_next_entry.snap'
base = ram(SRC)
A7 = 0x3f3b6          # SP at $1d0e6 entry in this snapshot (r); arg long at A7+4
assert l(base, A7) == 0x1d030, hex(l(base, A7))

def rname(n):          # $1d0e6 names every world through rand, world 0 included
    v = PW.rand1(n); return PW.A[v & 31] + PW.B[(v >> 5) & 31] + PW.C[(v >> 10) & 31]

def case(k):
    old = rnd.choice([0, 5, 2470, 2465, 2468, 2469, rnd.randint(0, 2470), rnd.randrange(0, 2471, 5)])
    sc = rnd.choice([500, 4999, 5000, 9999, 10000, 515090, 555555, rnd.randint(500, 555555), rnd.randint(500, 60000)])
    return old, sc

cases = [case(k) for k in range(N)] + [(2470, 500), (2470, 555555), (2465, 500), (0, 500), (2466, 5000)]

def run(c):
    old, sc = c
    P = Poker(base)
    P.w(WORLD, old); P.l(A7 + 4, sc)
    out = repl(SRC, P.flush() + ['bp 1d18e 20000', 'r', 'm 3c51a 2', 'm 37e86 24', 'm 3f338 2'])
    hexl = [x for x in out.splitlines() if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}', x.strip())]
    new = int(hexl[0].replace(' ', ''), 16)
    nb = bytes(int(x, 16) for x in hexl[1].split())
    nm = nb[:nb.index(0)].decode()
    flag = int(hexl[2].replace(' ', ''), 16)
    pc = regs(out)['PC']
    return old, sc, new, nm, flag, pc

good = 0
wraps = 0
with ThreadPoolExecutor(4) as ex:
    for old, sc, new, nm, flag, pc in ex.map(run, cases):
        n2, done = PW.next_world(old, sc)
        ok = pc == 0x1d18e and new == n2 and nm == rname(n2) and flag == int(done)
        good += ok; wraps += done
        if not ok:
            print('MISMATCH old=%d score=%d real=(%d,%s,%d) model=(%d,%s,%d) pc=%x' % (old, sc, new, nm, flag, n2, rname(n2), done, pc))
print('next_diff: %d/%d cases match (world, name, conquered flag); %d wrap-to-0 cases' % (good, len(cases), wraps))
