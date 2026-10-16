"""gate_trade.py [--run]: the trade $63f4 (economy.md "The trade") against its pseudocode, 67 forced states under callcap.
Builds the at-$63f4 snapshot from pm142/rand1.snap with gate_orders.sh's trade-arm pokes, then pokes each case's group food,
carried goods and posture and the lord's food and stock. Work dir scratchpad/cmd2/trade. Run from anywhere."""
import sys, json, random, subprocess, struct, os
from pathlib import Path
ROOT = next(d for d in Path(__file__).resolve().parents if (d / 'tools' / 'rdis.py').exists())
os.chdir(ROOT); sys.path.insert(0, 'tools')
from disassemble import ram_from_snap
D = 'scratchpad/cmd2/trade'
SNAP = f'{D}/at63f4.snap'
if not os.path.exists(SNAP):
    os.makedirs(D, exist_ok=True)
    open(f'{D}/mk.repl', 'w').write('\n'.join(['disk scratchpad/powermonger.st', 'w 58048 0400053c', 'w 58028 031c2146',
        'w 5802c 02000400', 'bp 63f4 60000000', f'snap {SNAP}', 'q']) + '\n')
    subprocess.run(f'ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm142/rand1.snap repl < {D}/mk.repl > {D}/mk.out 2>&1', shell=True, check=True)
A3 = 0x51938; LORD = 0x4e694
PRICE = [5, 10, 20, 4, 6, 2, 100, 200]
ROWS = [[7,6,2,1,0,4,0xff,0xff],[4,0,1,2,3,6,7,0xff],[3,4,5,0,1,2,6,7]]  # rows from $650a: read live below
ram0 = bytearray(ram_from_snap(SNAP))
R = [list(ram0[0x650a+8*i:0x650a+8*i+8]) for i in range(3)]
assert list(ram0[0x6502:0x650a]) == PRICE
rw = lambda r,a: (r[a]<<8)|r[a+1]
def predict(r):
    F0 = rw(r, A3+36); C = F0
    c = [rw(r, A3+84+12*i) for i in range(8)]
    S = [r[LORD+24+i] for i in range(8)]
    for i in range(8):
        S[i] = min(255, S[i] + c[i]); C += c[i]*2*PRICE[i]
    pos = rw(r, A3+60); row = R[0] if pos == 0 else R[pos-2]
    n = [0]*8
    for k in row:
        if k >= 0x80 or S[k] == 0: continue
        q = 2*PRICE[k]; cost = q*S[k]
        if C - cost >= 0: n[k] = S[k]; C -= cost
        else: n[k] = C // q; C = C % q
        S[k] -= n[k]
    food_l = rw(r, LORD+6)
    spent = F0 - C            # word compare (all values here are < 32768)
    if not (F0 < C): food_l = (food_l + spent) & 0xffff
    loy = rw(r, LORD+14) + (-8 if r[LORD] == rw(r, A3-48) else 8)
    return dict(gfood=C, lfood=food_l, S=S, loy=loy & 0xffff, n=n, spent=spent, F0=F0, C=C)
def lwrite(r, a, bs):  # poke bytes via aligned longwords, updating the model RAM
    lines = []
    for i, b in enumerate(bs): r[a+i] = b
    for w in range(a & ~3, a+len(bs), 4):
        lines.append(f'w {w:x} {r[w]:02x}{r[w+1]:02x}{r[w+2]:02x}{r[w+3]:02x}')
    return lines
def case(food, car, S, pos, lfood):
    r = bytearray(ram0)
    L = []
    L += lwrite(r, A3+36, [food>>8, food&255])
    for i in range(8): L += lwrite(r, A3+84+12*i, [car[i]>>8, car[i]&255])
    L += lwrite(r, A3+60, [pos>>8, pos&255])
    L += lwrite(r, LORD+24, S)
    L += lwrite(r, LORD+6, [lfood>>8, lfood&255])
    return r, L
cases = []
# named branches
cases.append(('nothing to sell, lord stocked, partial buy', *case(300, [0]*8, [3,3,3,3,3,3,3,3], 2, 100)))
cases.append(('nothing to sell, food covers all', *case(24000, [0]*8, [3,3,3,3,3,3,3,3], 2, 100)))
cases.append(('nothing to sell, lord has no stock (C==F0)', *case(500, [0]*8, [0]*8, 2, 100)))
cases.append(('sale covers purchase (sell 10 pot of boats, lord stock 0 but boat)', *case(100, [0,0,0,0,10,0,0,0], [0]*8, 2, 100)))
cases.append(('sell, then buy exactly what was sold (C==F0)', *case(100, [0,0,0,0,5,0,0,0], [0,0,0,0,0,0,0,0], 2, 100)))
cases.append(('sale just under purchase', *case(100, [0,0,0,0,3,0,0,0], [0,0,0,0,1,0,0,0], 2, 100)))
cases.append(('sale beats purchase by a margin', *case(100, [0,0,0,0,10,0,0,0], [0,0,0,0,0,0,0,5], 3, 100)))
rnd = random.Random(7)
for t in range(60):
    food = rnd.choice([0, 7, 50, 400, 3000, 24000])
    car = [rnd.choice([0,0,0,1,2,5,12]) for _ in range(8)]
    S = [rnd.choice([0,0,1,3,10,200,250]) for _ in range(8)]
    cases.append((f'rand{t}', *case(food, car, S, rnd.choice([0,2,3,4]), rnd.choice([0,28,1000])))) 
script = ['disk scratchpad/powermonger.st']
for i, (name, r, L) in enumerate(cases):
    script += L + [f'callcap 63f4 200000 {D}/cc/{i}.json']
script.append('q')
os.makedirs(f'{D}/cc', exist_ok=True)
open(f'{D}/verify.repl', 'w').write('\n'.join(script) + '\n')
if '--run' in sys.argv:
    subprocess.run(f'ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume {SNAP} repl < {D}/verify.repl > {D}/verify.out 2>&1', shell=True, check=True)
tot = {'cases': 0, 'fields_ok': 0, 'fields': 0}
branch = {}
for i, (name, r, L) in enumerate(cases):
    j = json.load(open(f'{D}/cc/{i}.json'))
    o = bytearray(r)
    for a, b, af in j['mem']:
        if a < len(o): o[a] = af   # the 'before' value was checked against the model implicitly via prediction
    p = predict(r)
    obs = dict(gfood=rw(o, A3+36), lfood=rw(o, LORD+6), S=list(o[LORD+24:LORD+32]), loy=rw(o, LORD+14))
    ok = [obs['gfood']==p['gfood'], obs['lfood']==p['lfood'], obs['S']==p['S'], obs['loy']==p['loy']]
    tot['cases'] += 1; tot['fields'] += 4; tot['fields_ok'] += sum(ok)
    if p['spent'] < 0: b = 'sale exceeds purchase (spent<0)'
    elif p['spent'] == 0: b = 'spent==0'
    else: b = 'spent>0'
    kind = 'nothing sold' if sum(rw(r, A3+84+12*i2) for i2 in range(8)) == 0 else 'sold'
    branch.setdefault((kind, b), [0,0]); branch[(kind, b)][0] += 1; branch[(kind, b)][1] += all(ok)
    # lord food delta observed
    if i < 7 or not all(ok):
        print(i, name, 'F0', p['F0'], 'C', p['C'], 'spent', p['spent'], 'lfood', rw(r, LORD+6), '->', obs['lfood'], '(pred', p['lfood'], ') gfood', obs['gfood'], '(pred', p['gfood'], ') S', obs['S'], p['S'], 'ok', ok, 'n', p['n'])
print(tot); print(branch)
print('--- spent<0 cases (lord food must be unchanged and the $64cc add skipped)')
for i, (name, r, L) in enumerate(cases):
    p = predict(r)
    if p['spent'] < 0:
        j = json.load(open(f'{D}/cc/{i}.json')); o = bytearray(r)
        for a, b, af in j['mem']:
            if a < len(o): o[a] = af
        print(i, 'F0', p['F0'], 'C', p['C'], 'lfood', rw(r, LORD+6), '->', rw(o, LORD+6), 'gfood', rw(o, A3+36), 'posture', rw(r, A3+60), 'carried', [rw(r, A3+84+12*k) for k in range(8)])
