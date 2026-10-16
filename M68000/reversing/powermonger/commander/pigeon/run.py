"""run.py <snap> <out_prefix> <budget> [--chunk N] [--watch addr len] [--side S] [--k K]
          [--order STEP:TYPE:X:Y[:K[:SIDE]]]... [--take S]... [--setb STEP:ADDR:VAL]...  (one byte poked through an aligned `w`)
One persistent emulator (commander loop.Emu). At each chunk boundary prints a line of the named group (pending, state,
men, lead pos/cell, sender owner) and the live pigeons riding to its lead; applies --order pokes (act.from_json on the
current RAM read with `m`) at their steps; --take S takes side S's slot at step 0. watch output goes to <out>.err.
"""
import json, sys, struct
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists())
CMD = ROOT / 'reversing/powermonger/commander'
sys.path.insert(0, str(CMD)); sys.path.insert(0, str(HERE))
from loop import Emu, REGIONS
from act import from_json
from pig import groups, pigeons, H, OBJ

def main(a):
    snap, out, budget = a[0], a[1], int(float(a[2]))
    chunk = int(float(a[a.index('--chunk') + 1])) if '--chunk' in a else 1_000_000
    side = int(a[a.index('--side') + 1]) if '--side' in a else 4
    k = int(a[a.index('--k') + 1]) if '--k' in a else 2
    orders, takes, setb = [], [], []
    for i, x in enumerate(a):
        if x == '--order':
            f = a[i + 1].split(':'); st = int(float(f[0]))
            orders.append((st, dict(side=int(f[5]) if len(f) > 5 else side, type=int(f[1], 16), x=int(f[2]), y=int(f[3]),
                                    group=int(f[4]) if len(f) > 4 else k)))
        if x == '--take': takes.append(int(a[i + 1]))
        if x == '--setb':
            f = a[i + 1].split(':'); setb.append((int(float(f[0])), int(f[1], 16), int(f[2], 16)))
    raw = {}
    if '--lines' in a:      # a loop.py decisions.jsonl: its `applied` records' REPL lines at their steps
        for l in open(a[a.index('--lines') + 1]):
            d = json.loads(l)
            if d.get('kind') == 'applied': raw.setdefault(d['step'], []).extend(d['lines'])
    emu = Emu(ROOT / snap, f'{out}.err')
    if '--watch' in a:
        i = a.index('--watch'); emu.send(f'watch {a[i+1]} {a[i+2]}'); emu._line()
    log = open(f'{out}.log', 'w')
    def P(*x):
        s = ' '.join(str(v) for v in x); print(s); log.write(s + '\n'); log.flush()
    step = 0; prev = None
    while step <= budget:
        R = emu.read('m', None); emu.mem(0x4c112, 1248)
        acts = [dict(side=s, take=True) for s in takes] if step == 0 else []
        acts += [o for st, o in orders if st == step]
        if step in raw:
            emu.poke(raw[step]); P(step, 'RAW', raw[step])
        for st, ad, val in setb:
            if st == step:
                al = ad & ~3; b = bytearray(emu.mem(al, 4)); b[ad - al] = val
                emu.send(f'w {al:x} {b.hex()}'); P(step, 'SETB', hex(ad), hex(val), b.hex())
        if acts:
            lines = from_json(R, acts); emu.poke(lines); P(step, 'POKE', acts, lines)
        g = groups(R, side)[k]
        lead = g['lead']; pos = (H(R, OBJ + lead + 8), H(R, OBJ + lead + 10)) if lead else None
        pg = [(p['i'], p['own'], p['pos'], p['t18'], p['type'], hex(p['target'])) for p in pigeons(R) if p['i'] and p['rider'] == lead]
        snd = g['sender']
        tgt = (R[OBJ + lead + 20], R[OBJ + lead + 22]) if lead else None
        key = (tgt, g['pending'], g['state'], g['owner'], g['sender_own'], tuple(pg), pos and (pos[0] >> 8, pos[1] >> 8))
        if key != prev or acts:
            P(step, f"tgt {tgt} pend {g['pending']} state {g['state']} own {g['owner']} men {g['men']} lead {lead:x} pos {pos} "
                    f"sender {snd:x} sown {g['sender_own']} spos {(H(R, OBJ+snd+8), H(R, OBJ+snd+10)) if snd else None} pigs {pg}")
        prev = key
        if step == budget: break
        n = min(chunk, budget - step); emu.run(n); step += n
    emu.save(str(ROOT / f'{out}.snap')); emu.close()

if __name__ == '__main__':
    main(sys.argv[1:])
