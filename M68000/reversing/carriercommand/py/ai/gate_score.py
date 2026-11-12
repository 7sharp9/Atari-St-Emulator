"""Gate for the enemy target choice ($2337a, ai.md section 2).

For every snapshot in the corpus (taken at the return of $2337a, bp $1ad02) the model in score.py must
reproduce all 64 words of the game's score table at $232fa and its argmax must equal the target the game
stored at $11ba. Then each scoring constant is nudged in turn (broken models): a term is proven only if
its nudge breaks at least one snapshot.

usage: gate_score.py            corpus under $CARRIER_WORK/ai (README "Snapshots" says how it was made)
"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
from ccpaths import *
import struct

SRC = (_pl.Path(__file__).resolve().parent / 'score.py').read_text()
CORPUS = ([WORK / 'ai' / 'nat' / f'd{i}.snap' for i in (1, 2)]
          + [WORK / 'ai' / 'nat2' / f'e{i}.snap' for i in range(2, 13)]
          + [WORK / 'ai' / f'{n}.snap' for n in ('s1', 's2', 's3', 's3b', 's4', 's5', 's6a', 's6b')])

MUTANTS = [
    ('far cutoff score', '-15000', '-14000'),
    ('carrier distance scale', '(-de)>>11', '(-de)>>10'),
    ('base distance scale', 'y,hx,hy)>>14', 'y,hx,hy)>>13'),
    ('neutral large +3000', 'else 3000', 'else 2500'),
    ('neutral small +2000', '2000 if area', '2200 if area'),
    ('own island -4000', 's+= -4000', 's+= -3500'),
    ('player small +1000', '1000 if area', '1200 if area'),
    ('player large +1500', 'else 1500', 'else 1700'),
    ('area threshold 2000', '<=0x7d0', '<=0x700'),
    ('network neighbour +4000', 'if cnt: s+=4000', 'if cnt: s+=3500'),
    ('home island +5000', 'sc[0]+=5000', 'sc[0]+=4500'),
]


def model(src):
    ns = {'__name__': 'score_model', '__file__': str(_pl.Path(__file__).resolve().parent / 'score.py')}
    exec(compile(src.split("if __name__=='__main__':")[0], 'score.py', 'exec'), ns)
    return ns['S']


def check(S, d):
    sc, _ = S(d)
    wrap = lambda v: ((v + 32768) % 65536) - 32768
    sc = [wrap(v) for v in sc]
    tbl = [struct.unpack('>h', d[0x232fa + 2 * i:0x232fc + 2 * i])[0] for i in range(64)]
    best, bi = -32768, 0
    for i, v in enumerate(sc):
        if v > best:
            best, bi = v, i
    return sum(a == b for a, b in zip(sc, tbl)), bi == struct.unpack('>H', d[0x11ba:0x11bc])[0]


rams = [ram(p) for p in CORPUS]
S = model(SRC)
words = sum(check(S, d)[0] for d in rams)
argmax = sum(check(S, d)[1] for d in rams)
print(f'score words {words}/{64 * len(rams)}, target {argmax}/{len(rams)} snapshots')
for name, a, b in MUTANTS:
    assert a in SRC, a
    Sm = model(SRC.replace(a, b))
    broken = sum(1 for d in rams if check(Sm, d) != (64, True))
    print(f'control {name}: breaks {broken}/{len(rams)}')
