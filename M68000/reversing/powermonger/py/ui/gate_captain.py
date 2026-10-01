"""pm140 ui: gate for the captain panel (opener $9036, template $921a, formatters $907c..$91a8) over every live group of every side,
and the group-aggression read/forcing ($90de, flag $9218).  Model from the code; real routine by callcap (A3 = $51538 + side*$13c + 2*i).
    cd M68000 && .venv/bin/python reversing/powermonger/py/ui/gate_captain.py [snap ...]   -> matched/total, aggression values seen"""
import re, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import *
import gate_getname as G

def model(R, a):
    w = lambda x: (R[x] << 8) | R[x + 1]
    def cstr(x):
        o = bytearray()
        while R[x]: o.append(R[x]); x += 1
        return o.decode('latin1')
    q, r = divmod(a - GROUPS, GSTRIDE)
    first = (r == 0)
    name = cstr(0x582f9 + 16 * (q - 1)) if first else G.model_from(R, w(a + 64))
    state = cstr(0x9486 + 17 + R[0x9486 + w(a + 76)]).strip()
    ag = 0 if first else w(a + 148)
    aggr = cstr(0x9530 + 8 + R[0x9530 + ag])
    post = cstr(0x9580 + 3 + R[0x9580 + w(a + 136) - 2])
    lead = OBJ + w(a + 64)
    hv = 8 if R[lead + 5] & 0x80 else (R[lead + 45] >> 4) & 7
    health = cstr(0xa2dc + 9 + R[0xa2dc + hv])
    items = []
    for j in range(8):
        n = w(a + 160 + 12 * j)
        if n: items.append(f"{n} {cstr(0xa242 + 19 + w(0xa242 + 2 * (j + 1))).strip()}" + ('s' if n != 1 else ''))
    return [name, state, f'{aggr} but {post}', 'trusting', health, str(R[lead + 16]), str(w(a + 112)), str(w(a + 52))], items, ag, first

def main(snaps):
    bad_all = 0
    for snap in snaps:
        R = ram_of(snap); w = lambda x: (R[x] << 8) | R[x + 1]
        groups = [GROUPS + s * GSTRIDE + 2 * i for s in range(1, 6) for i in range(6) if w(GROUPS + s * GSTRIDE + 28 + 2 * i) and w(GROUPS + s * GSTRIDE + 64 + 2 * i)]
        ccs = parse_callcaps(repl(snap, [f'callcap 9036 20000 A3={a:x}' for a in groups]))
        ok = 0; bad = []; agg = collections.Counter(); forced = 0
        for a, cc in zip(groups, ccs):
            t = panel_text(R, cc)
            exp, items, ag, first = model(R, a)
            got = [re.sub(r'^\. [A-Za-z ]+:\s*', '', t[i])[:-1].rstrip(' .') for i in range(1, 9)]
            got = [re.sub(r'\s+', ' ', g) for g in got]
            car = ' '.join(t[i][2:-1].replace('....', '') for i in range(9, 13))
            car = re.sub(r'^Carrying:', '', car); car = re.sub(r'\s+', ' ', car).strip()
            if got == exp and car.replace('. ', '') == ' '.join(items).strip().replace('. ', ''): ok += 1
            else: bad.append((hex(a), got, exp, car, items))
            agg[(ag, first)] += 1
        print(f'{Path(snap).name}: captain panel {ok}/{len(groups)} groups; (aggression word, first group) -> count: {dict(sorted(agg.items()))}')
        for b in bad[:5]: print('   MISMATCH', b)
        bad_all += len(bad)
    return bad_all
if __name__ == '__main__':
    snaps = sys.argv[1:] or [str(ROOT / 'scratchpad/pm123/win/m1_s0.snap'), str(ROOT / 'scratchpad/pm121/run/k5_s4.snap'), str(ROOT / 'scratchpad/pm121/k25.snap')]
    sys.exit(1 if main(snaps) else 0)
