#!/usr/bin/env python3
"""Static prediction of the OKI phrases of every effect id (stream decoded by static_streams.py, table entry -> phrase = byte0-1 of the 4-byte entry in table A
($9E56, oki1) / table B ($9F12, oki2)) against the phrases MAME saw the HuC6280 start on the chips in the sweep (out/sw_all.log)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S, static_streams as SS, analyze_sweep as A
def entry(table, e):
    base = {'A': 0x9e56, 'B': 0x9f12}[table]
    return S.rb(base + 4 * e) - 1
# phrase lengths (oki_phrases.py output): a 1-byte phrase (start == end) never shows busy in the OKI status, so $F6C8's retry loop (X = 4) writes it 4 times
plen = {}
for l in list(open(os.path.join(HERE, 'data', 'oki_phrases.tsv')))[1:]:
    f = l.split('\t'); plen[(f[0], int(f[1]))] = int(f[4])
def expand(chip, lst):
    out = []
    for ph in lst: out += [ph] * (4 if plen.get((chip, ph), 99) == 1 else 1)
    return out
blocks = A.parse(os.path.join(HERE, 'out', 'sw_all.log'))
tot = same = 0
rows = []
for i in range(1, S.MAXID + 1):
    p, h, chans, q = S.header(i)
    if h[2]: continue
    o1 = []; o2 = []
    for ch, a in chans:
        ev, loops = SS.decode(a, ch)
        a1, a2 = SS.oki_starts(ev)
        o1 += a1; o2 += a2
    pred1 = expand('oki1', [entry('A', e) for e in o1]); pred2 = expand('oki2', [entry('B', e) for e in o2])
    r = A.summarise(blocks[i])
    obs1 = [x[0] for x in r['oki1_start']]; obs2 = [x[0] for x in r['oki2_start']]
    if not (pred1 or pred2 or obs1 or obs2): continue
    tot += 1
    ok = (pred1 == obs1 and pred2 == obs2)
    same += ok
    rows.append((i, ok, pred1, obs1, pred2, obs2))
    if not ok: print('MISMATCH %02x static oki1 %s oki2 %s | MAME oki1 %s oki2 %s' % (i, pred1, pred2, obs1, obs2))
print('effect ids with OKI starts: %d, static phrase sequence == MAME phrase sequence: %d' % (tot, same))
