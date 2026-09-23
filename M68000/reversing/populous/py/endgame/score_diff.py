"""score_diff.py - differential test of score_ref.score() against the real $1c858 via callcap.

For each base snapshot (stopped at $1c858 entry), N randomized states: the entity array
(count, flags, side, str, sprite, knight), battles won, human side, both power masks, the
computer's +16 word, $219b0, $36cea, $21d5e and the lost argument. The real routine runs until
the emulator's loop detector stops it in the click-wait loop at $1cfec. Compared: every byte of
the 7 rows, $36cea, $21d52, $3d528, $16ed4 and the button caption on the stack (-54(A6)), and
no other byte outside the screen and the stack may change.

usage: python score_diff.py [N_per_snap] [seed]"""
import json, os, random, struct, sys
from eg import *
import score_ref as S

SNAPS = ['win_entry.snap', 'lose_entry.snap']
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)


def randomize(P, m):
    n = rnd.choice([0, 1, 5, 20, 60, 120])
    P.w(NENT, n)
    for i in range(n):
        e = ENT + ESZ * i
        P.b(e, rnd.choice([1, 1, 1, 2, 2, 0x12, 0x22, 8, 9, 0x80, 0]))
        P.b(e + 1, rnd.randint(0, 1))
        P.w(e + 4, rnd.choice([0, 0, rnd.randint(1, 3000), -rnd.randint(1, 50) & 0xffff]))
        P.w(e + 12, rnd.choice([0x2a, 0x2a, rnd.randint(0x20, 0x2b), 1, 0x55]))
        P.l(e + 14, rnd.choice([0, 0, 0, ENT + ESZ * rnd.randint(0, 200)]))
    you = rnd.randint(0, 1)
    P.w(HUMAN, you); P.w(OTHER, 1 - you)
    for s in (0, 1):
        P.w(BATTLES + 2 * s, rnd.choice([0, rnd.randint(0, 40), 3]))
        P.w(GOD + 0x2e * s + 14, rnd.choice([0x1ff, 7, rnd.getrandbits(9), rnd.getrandbits(16)]))
        P.w(GOD + 0x2e * s + 16, rnd.choice([rnd.randint(1, 10), rnd.randint(-5, 20) & 0xffff]))
    P.w(0x219b0, rnd.choice([0, 1, 1]))
    P.l(SCORE, rnd.choice([0, 30, rnd.randint(0, 2000), rnd.randint(0, 60000), 55555, 55556,
                           49000, rnd.randint(0, 700000), -rnd.randint(1, 1000) & 0xffffffff]))
    P.w(0x21d5e, rnd.choice([0, 0xffff, 7]))


def check(m, d, lost, sp0):
    rows, sc, btn = S.score(m, lost)
    after = bytearray(m)
    for a, x0, x1 in d['mem']:
        after[a] = x1
    scr = l(m, 0x3c4ce)
    watch = set(range(ROWS, ROWS + 7 * 0x2e)) | set(range(SCORE, SCORE + 4)) | {0x21d52, 0x21d53, 0x3d528, 0x3d529} | set(range(0x16ed4, 0x16ed8))
    stray = [a for a, _, _ in d['mem'] if a not in watch and not (scr <= a < scr + 32000) and not (sp0 - 512 <= a < sp0)]
    real_rows = [rowtext(after, r) for r in range(7)]
    bt = cstr(after, sp0 - 8 - 54)
    ok = (real_rows == rows and struct.unpack_from('>i', after, SCORE)[0] == sc and bt == btn
          and w(after, 0x21d52) == 0 and w(after, 0x3d528) == 2 and l(after, 0x16ed4) == 0 and not stray)
    return ok, (rows, real_rows, sc, struct.unpack_from('>i', after, SCORE)[0], btn, bt, [hex(a) for a in stray][:10])


tot = good = 0
from collections import Counter
cov = Counter()
for sn in SNAPS:
    base = ram(OUT + '/' + sn)
    sp0 = struct.unpack_from('>I', base, 0)[0]  # placeholder, replaced below
    out = repl(OUT + '/' + sn, ['r'])
    sp0 = regs(out)['A7']
    lines, cases = [], []
    for k in range(N):
        P = Poker(base)
        randomize(P, base)
        lost = rnd.choice([0, 1])
        P.l(sp0, (lost << 16) | w(base, sp0 + 2))
        jp = '%s/cc/score_%s_%d.json' % (OUT, sn[:-5], k)
        lines += P.flush() + ['callcap 1c858 400000 %s' % jp]
        cases.append((bytes(P.m), lost, jp))
    os.makedirs(OUT + '/cc', exist_ok=True)
    repl(OUT + '/' + sn, lines)
    for m, lost, jp in cases:
        d = json.load(open(jp))
        ok, info = check(m, d, lost, sp0)
        tot += 1; good += ok
        sc = info[2]; cov['500'] += sc == 500; cov['515090'] += sc == 515090; cov['won'] += lost == 0
        cov['battle+5000'] += S.sw(m, BATTLES + 2 * w(m, HUMAN)) > S.sw(m, BATTLES + 2 * w(m, OTHER))
        cov['castles>0'] += any(c != '0' for c in info[0][5].split()[3:])
        cov['knights>0'] += any(c != '0' for c in info[0][3].split()[3:])
        if not ok:
            print('MISMATCH', jp, lost, info)
        os.remove(jp)
print('coverage', dict(cov))
print('score_diff: %d/%d states match (rows, score, button, side effects)' % (good, tot))
