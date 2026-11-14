"""flights.py: chain of attract flights from one demo-start snapshot with no input except the ESC that ends a flight.
For flight k: start snapshot S_k (at $230c0, demo flag $ff). Fly BUDGET steps, read score/tick/RNG. Then ESC, run to the
next scatter ($236f8): record RNG R_k, snapshot Q_k; then (natural) bp 230c0 -> S_{k+1}.
Variant 'seed': from Q_k poke the power-up RNG seed (labelled poke), run to $230c0 -> Sp_k, fly BUDGET, read score.
Usage: flights.py <S1.snap> <outdir> <nflights> [budget]"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
S, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3]); B = sys.argv[4] if len(sys.argv) > 4 else '20000000'
os.makedirs(out, exist_ok=True)
def rd(snap, cmds, k):
    rows = drv.mem(drv.run(snap, cmds)); return rows[-k:]
def state(rows):  # score(4) tick(2) y/pos(12) wave(2)
    sc, tk, sh, ls = rows
    return int.from_bytes(sc,'big',signed=True), int.from_bytes(tk,'big'), [int.from_bytes(sh[i:i+2],'big') for i in (0,2,4)], int.from_bytes(ls,'big')
READ = ['m 2708e 4', 'm 32a44 2', 'm 270b0 6', 'm 32a4e 2']
cur = S
for k in range(1, n+1):
    fly = rd(cur, ['s '+B] + READ, 4)
    print(f'flight {k} natural: score,tick,pos,landscape =', state(fly), flush=True)
    q = f'{out}/Q{k}.snap'; nxt = f'{out}/S{k+1}.snap'
    r = drv.mem(drv.run(cur, ['s 3000000', 'kbd 01', 's 60000', 'kbd 81', 'bp 236f8 150000000', 'm 2706e 8', f'snap {q}', 'bp 230c0 150000000', f'snap {nxt}']))
    print(f'  RNG at flight {k+1} scatter = {r[-1].hex()}')
    # seed variant
    sp = f'{out}/Sp{k+1}.snap'
    drv.run(q, ['w 2706e 1234abdf', 'w 27072 5678e7f2', 'bp 230c0 150000000', f'snap {sp}'])
    fp = rd(sp, ['s '+B] + READ, 4)
    print(f'flight {k+1} with RNG seed poked at scatter: score,tick,pos,landscape =', state(fp), flush=True)
    cur = nxt
