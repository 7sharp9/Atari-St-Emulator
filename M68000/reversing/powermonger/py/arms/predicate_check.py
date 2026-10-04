"""predicate_check.py [N] [snaplist]  (PowerMonger 148th, agent A)

Closed-form predicates for the `$65b4` decision arms, checked against the proven model `cmdai_ref._decide` (itself gated against the
real 68000 by py/cmdai/gate_cmdai.py: 323/323 natural, 280/280 synthetic) on every AI group of the census snapshots under random
mutations of the inputs the predicates mention (men, D7, state forced to 6, the lords' home troops and food, group food):

  arm1   men < 22                 and an own-side lord has home > 1                                    -> getmen   ($65c8)
  escort D7 != 0 and group 0 (A1 - D7) in state $d with 280() == 4                                      -> escort   ($65f4)
  attack men > 4 and $68fe(men-4) finds a lord (nearest enemy lord with home < men-4)
         and $68ee(d) <= food                                                                             -> attack   ($6638)
  food   men > 4 and $68fe finds one and $68ee(d) > food and an own lord has food > 1                    -> food     ($66b0, via $66a4)
  food_none: the same without an own lord with food > 1                                                  -> $66a4 then next group
  getmen2: an own lord L has home > 1 (the best, $69b4(8)) and $68fe(men + home(L)) finds a lord        -> getmen2  ($666c)
  xfer   D7 != 0 and men != 0 and none of the above                                                      -> xfer     ($668c)
  idle0  D7 == 0 and none of the above                                                                   -> idle0    ($6680 then $66c8)

Prints the number of (mutated) groups whose predicted arm equals the model's, and the count per arm.
    python predicate_check.py [N mutations per group] [snaplist]
"""
import collections, os, random, sys
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/cmdai'))
import pm_fsm_ref as P, cmdai_ref as C
from disassemble import ram_from_snap

def predict(m, A1, A2, D7):
    men = C.s16(m.wu(A1 + 52)); food = C.s16(m.wu(A1 + 112))
    own_lord, _, own_z = C.call_69b4(m, A2, 8)     # `$69b4(8)`: an own lord with home > 1 (the call is the predicate's own leaf)
    if men < 0x16 and not own_z: return 'getmen'
    if D7 != 0:
        g0 = A1 - D7
        if m.wu(g0 + 76) == 0xd and m.wu(g0 + 280) == 4: return 'escort'
    if men - 4 > 0:
        D3, A3, z = C.call_68fe(m, A1, A2, men - 4)
        if not z:
            if not C.s16(C.call_68ee(men - 4, D3)) > food: return 'attack'
            _, _, fz = C.call_69b4(m, A2, 6)
            return 'food_none' if fz else 'food'
    if not own_z:
        D3, A3, z = C.call_69b4(m, A2, 8)[0], None, False
        # A3 of the best own lord:
        _, lordA, _ = C.call_69b4(m, A2, 8)
        d1 = (men + m.wu(lordA + 8)) & 0xffff
        _, _, z2 = C.call_68fe(m, A1, A2, d1)
        if not z2: return 'getmen2'
    if D7 == 0: return 'idle0'
    if men == 0: return 'idle_nomen'
    return 'xfer'

def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    lst = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / 'scratchpad/pm144/allsnaps.txt')
    snaps = [l.strip() for l in open(lst) if l.strip()]
    rnd = random.Random(148)
    ok = tot = 0; per = collections.Counter(); bad = []
    for s in snaps:
        ram = ram_from_snap(s)
        if len(ram) < 0x59000: continue
        m0 = P.Mem(ram)
        A0 = C.CMD
        while A0 != C.CMD_END:
            if m0.bu(A0 + 4) == 4:
                base = (C.GROUPS + C.sp16((m0.bu(A0) * 0x13c) & 0xffff)) & 0xfffff
                for D7 in range(10, -1, -2):
                    A1 = base + D7
                    if C.s16(m0.wu(A1 + 28)) <= 0: continue
                    for k in range(N + 1):
                        m = P.Mem(ram)
                        m.ww(A1 + 76, 6)
                        A2 = (C.OBJ + C.sp16(m.wu(A1 + 64))) & 0xfffff
                        if k:
                            m.ww(A1 + 52, rnd.choice([0, 1, 2, 3, 4, 5, 8, 12, 21, 22, 23, 33, 40]))
                            if rnd.random() < .5: m.ww(A1 + 112, rnd.choice([0, 5, 20, 50, 400, 24575]))
                            a = C.LORDS
                            while a != C.LORDS_END:
                                if m.bu(a):
                                    m.ww(a + 8, rnd.choice([0, 0, 1, 1, 2, 3, 10]))
                                    m.ww(a + 6, rnd.choice([0, 1, 2, 30]))
                                a += 32
                            if D7 and rnd.random() < .2:
                                g0 = A1 - D7; m.ww(g0 + 76, 0xd); m.ww(g0 + 280, rnd.choice([2, 4]))
                        want = predict(m, A1, A2, D7)
                        C.TRACE.clear()
                        D2 = m.wu(A1 + 28)
                        try:
                            C._decide(m, A0, A1, A2, D2, D7)
                            got = C.TRACE[-1] if C.TRACE else '?'
                        except Exception as e:
                            got = 'ERR'
                        tot += 1; per[got] += 1
                        if got == want: ok += 1
                        else: bad.append((s, D7, want, got))
            A0 += 6
    print('predicate == model on %d / %d mutated AI groups' % (ok, tot))
    print('model arms:', dict(per))
    for b in bad[:8]: print('MISMATCH', b)

if __name__ == '__main__':
    main()
