"""Gate for the mothership's launch ($22722 bsr $21722 with D0..D2 = the mothership's new position, A0..A2 = 0, $80, 0, A3 = $1ff, A4 = $2279a).
For every tick with a 'launch' event the new $2279a record at arrival k+1 must equal gate_chaser.chaser_step applied to
[mx, my, mz, 0, $80, 0, $1ff, pad 0, $2279a] (the appended record gets its first pass in the same walker pass), with the ship at arrival k+1.

    python3 gate_launch.py <mothership_drive json> [--control vy|life]      (vy: launch vy 0 instead of $80; life: $1fe)
"""
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import bh
import gate_chaser as G
S = G.S

a = sys.argv[1:]
control = a[a.index('--control') + 1] if '--control' in a else 'none'
cap = json.load(open(a[0]))
S.load_hmap(cap['snap'])
rows = cap['rows']; pools = [S.unpack_pool(r['pool']) for r in rows]
ok = n = 0
for k in range(len(rows) - 1):
    if not any(e['e'] == 'launch' for e in rows[k]['ev']) or rows[k + 1].get('poked'):
        continue
    if any(e['e'] == 'kill' for e in rows[k]['ev']) or rows[k + 1]['npool'] != rows[k]['npool'] + 1:
        continue                                    # a kill reorders the pool: the appended record is no longer last
    new = [pools[k + 1][-1]] if pools[k + 1][-1][8] == G.MC else []
    m = rows[k + 1]['mship']
    if m is None or len(new) < 1:
        continue
    vy = 0 if control == 'vy' else 0x80
    life = 0x1fe if control == 'life' else 0x1ff
    got, _ = G.chaser_step([m[0], m[1], m[2], 0, vy, 0, life, 0, G.MC], rows[k + 1]['pos'])
    n += 1; ok += got in new
print(f'launches: the record appended last == chaser_step(launch record) {ok}/{n} (control {control})')
