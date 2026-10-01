"""pm140 ui: gate for the person panel ($9c16, template $a328) and the house panel ($9a38, template $9e76) opened through the
click dispatcher $95f6.  A Python model of every formatter, written from the code at $9c4c..$9e52 and $9a7c..$9bae, builds the
text rows from the pre-call RAM only; the real routine is run by callcap (A3 = record, $2df96 = 1) and the grid it builds is
read back; every row must be identical.
    cd M68000 && .venv/bin/python reversing/powermonger/py/ui/gate_panels.py [snap ...]     (default: m1_s0 and k5_s4)
Prints matched/total per snapshot and kind; exit 1 on any mismatch."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'reversing/powermonger/py'))
from uilib import *
from census import walk
import gate_getname as G   # model() and the table readers; importing runs its gate on m1_s0 (quiet enough)
MODEL = None

def mk(R):
    w = lambda a: (R[a] << 8) | R[a + 1]
    def cstr(a):
        o = bytearray()
        while R[a]: o.append(R[a]); a += 1
        return o.decode('latin1')
    def table(base, hdr, n, bytes_=True):   # byte-offset table: string at base+hdr+byte[i]
        return [cstr(base + hdr + (R[base + i] if bytes_ else w(base + 2 * i))) for i in range(n)]
    T = dict(kind=[cstr(0xa128 + 12 + w(0xa128 + 2 * i)) for i in range(6)],
             house=[cstr(0xa15a + 26 + w(0xa15a + 2 * i)) for i in range(13)],
             health=table(0xa2dc, 9, 9), job=table(0xa200, 10, 10), speed=table(0xa1d8, 4, 4), loyal=table(0x959e, 8, 8),
             item=[cstr(0xa242 + 18 + w(0xa242 + 2 * i)) if i < 9 else '' for i in range(9)])
    def gn(seed): return G.model_from(R, seed)
    def side(n): return cstr(0x582f9 + 16 * (n - 1))
    def person(a):
        def item(code): return T['item'][code // 2] if code % 2 == 0 and code // 2 < 9 else '?'
        king = False
        if R[a + 7] & 0x10 and w(a + 42):
            q, r = divmod(w(a + 42), 0x13c)
            if r == 0x4c: king = True; kside = q
        name = side(kside) if king else gn((a - OBJ) & 0xffff)
        bld = 0x4f916 + w(a + 34); lord = 0x4e514 + w(bld + 14)
        rank = T['kind'][R[lord + 1] - 1]; town = gn(w(lord + 4))
        health = T['health'][8 if R[a + 5] & 0x80 else (R[a + 45] >> 4) & 7]
        kind = T['house'][R[bld + 7]]
        d1 = a - OBJ; d0 = w(bld + 10); d3 = d0; sex = 0; comp = ''
        if d0:
            d2 = 0
            while d0 != d1:
                d2 += 1; d3 = d0; d0 = w(OBJ + d0 + 24)
                if not d0: break
            if d2 == 0:
                d3 = w(a + 24)
            if d2 == 0 and d3 == 0: comp = 'No One'; sex = 0
            else: comp = gn(d3); sex = (d2 & 1) * 4
        pron = 'he' if (R[a + 7] & 0x10) else ('he', 'she')[sex // 4]
        job = T['job'][9 if R[a + 7] & 0x10 else R[a + 7] & 0xf]
        speed = T['speed'][(R[a + 16] >> 4) & 3]
        i1, i2 = R[a + 33], R[a + 44]
        items = (item(i1) + ((' & ' + item(i2)) if i2 else '')) if i1 else (item(i2) if i2 else '')
        if not items: items = 'Nothing'
        obeys = 'nobody' if king else side(R[a + 5])
        return [f'{name} of the {rank} of', f'{town} is {health} and lives in', f'a {kind} with {comp},',
                f'{speed} working as a {job} {pron}', f'holds {items}. At {R[a + 14]}', f'years old {pron} obeys {obeys}.']
    def house(a):
        kind = 7 if R[a + 6] == 0x10 else R[a + 7]
        lord = 0x4e514 + w(a + 14)
        men = []; d0 = w(a + 10); d2 = 2
        while d0 and d2:
            men.append(gn(d0)); d2 -= 1
            if not d2: break
            d0 = w(OBJ + d0 + 24)
            if not d0: break
        ps = w(lord + 14); idx = 0 if ps & 0x8000 else min(ps // 75, 7)
        goods = [(i, R[lord + 24 + i]) for i in range(8) if R[lord + 24 + i]]
        stock = [f'{n} {T["item"][i + 1].strip()}' + ('s' if n != 1 else '') for i, n in goods]
        return dict(kind=T['house'][kind], town=gn(w(lord + 4)), people=' & '.join(men), kingdom=side(R[lord] if False else R[a + 5]),
                    food=w(lord + 6), men=w(lord + 8), loyal=T['loyal'][idx], forest=gn(w(0x57f68 + w(lord + 22))), stock=stock, ps=ps)
    return person, house

def rows_person(t): return [re.sub(r'^\. | *\.?$', '', r).rstrip('. ').strip() if False else r[2:].rstrip(' .') for r in t[1:7]]

def main(snaps):
    bad_all = 0
    for snap in snaps:
        R = ram_of(snap); person, house = mk(R)
        recs, torn = walk(R)
        men = [o for o, _, _, rec in recs if rec[6] in (0, 0xe)]
        houses = [o for o, _, _, rec in recs if rec[6] in (2, 0x10)]
        calls = []
        for a in men + houses: calls += ['w 2df96 00010001', f'callcap 95f6 60000 A3={a:x}']
        ccs = parse_callcaps(repl(snap, calls))
        okp = okh = 0; bad = []
        for a, cc in zip(men + houses, ccs):
            t = panel_text(R, cc)
            if not t: bad.append((hex(a), 'no panel')); continue
            if a in men:
                exp = person(a); got = [r[2:].rstrip(' .') for r in t[1:7]]
                # model rows carry the tail text of the template row ("of", "and lives in" ...): compare with the template's literal parts
                got = [re.sub(r'\s+', ' ', g) for g in got]
                exp = [re.sub(r'\s+', ' ', e).rstrip('.').rstrip() for e in exp]
                if got == exp: okp += 1
                else: bad.append((hex(a), got, exp))
            else:
                h = house(a); g = {k: v for k, v in zip(('House Name', 'Town Name', 'People Name', 'Kingdom', 'Food', 'Men', 'Near Forest'),
                                                     [re.sub(r'^\. [A-Za-z ]+:\s*', '', r)[:-1].rstrip(' .') for r in t[1:8]])}
                ok = (g['House Name'] == h['kind'] and g['Town Name'] == h['town'] and g['People Name'] == h['people'] and g['Kingdom'] == h['kingdom']
                      and g['Food'] == str(h['food']) and g['Men'] == f"{h['men']} who are {h['loyal']}" and g['Near Forest'] == h['forest'])
                if ok: okh += 1
                else: bad.append((hex(a), g, h))
        print(f'{Path(snap).name}: person panel {okp}/{len(men)}, house panel {okh}/{len(houses)}')
        for b in bad[:6]: print('   MISMATCH', b)
        bad_all += len(bad)
    return bad_all

if __name__ == '__main__':
    snaps = sys.argv[1:] or [str(ROOT / 'scratchpad/pm123/win/m1_s0.snap'), str(ROOT / 'scratchpad/pm121/run/k5_s4.snap')]
    sys.exit(1 if main(snaps) else 0)
