"""bptrace.py <snap> <out> <budget> <addr> [--order STEP:TYPE:X:Y:K:SIDE]... [--take S]...
Stops at every arrival of <addr> within <budget> steps (repeated `bp`, then `s 1` past it) and logs one JSON line per
stop: step (relative to the snapshot), D0..D7, A0..A7, the longword at (A7) (return address), 8 bytes at A0.
Orders (act.from_json on RAM read with `m`) are applied when the run passes their step (at the first stop/boundary
at or after it; boundaries every 1M steps so the poke lands within 1M of STEP)."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'reversing/powermonger/commander'))
from loop import Emu
from act import from_json

def regs(emu):
    head = emu._line(); R = {}
    while True:
        l = emu._line()
        for m in re.finditer(r'([DA]\d|PC):([0-9a-f]{8})', l): R[m.group(1)] = int(m.group(2), 16)
        if l.startswith('PC:'):
            emu._line(); break
    return head, R

def main(a):
    snap, out, budget, addr = a[0], a[1], int(float(a[2])), int(a[3], 16)
    orders, takes = [], []
    for i, x in enumerate(a):
        if x == '--order':
            f = a[i + 1].split(':')
            orders.append([int(float(f[0])), dict(side=int(f[5]), type=int(f[1], 16), x=int(f[2]), y=int(f[3]), group=int(f[4]))])
        if x == '--take': takes.append(int(a[i + 1]))
    raw = {}
    if '--lines' in a:      # a loop.py decisions.jsonl: its `applied` records' REPL lines at their steps
        for l in open(a[a.index('--lines') + 1]):
            d = json.loads(l)
            if d.get('kind') == 'applied': raw.setdefault(d['step'], []).extend(d['lines'])
    emu = Emu(ROOT / snap, f'{out}.err'); log = open(f'{out}.jsonl', 'w')
    step = 0
    def apply():
        for st in sorted(raw):
            if st <= step:
                emu.poke(raw[st]); log.write(json.dumps(dict(step=step, raw_at=st, poke=raw[st])) + '\n'); del raw[st]
        acts = [o for st, o in orders if st <= step and not o.get('_done')]
        acts = [dict(side=s, take=True) for s in takes if step == 0] + acts
        if acts:
            R = emu.read('m', None)
            lines = from_json(R, [{k: v for k, v in o.items() if k != '_done'} for o in acts]); emu.poke(lines)
            log.write(json.dumps(dict(step=step, poke=lines)) + '\n')
            for o in acts: o['_done'] = True
    apply()
    while step < budget:
        n = min(1_000_000, budget - step, *[st - step for st in raw if st > step])
        emu.send(f'bp {addr:x} {n}'); head, R = regs(emu)
        if head.startswith('--- breakpoint'):
            step += int(head.split(' after ')[1].split()[0])
            ret = int(emu.mem(R['A7'], 4).hex(), 16); a0 = emu.mem(R['A0'] & 0xfffffe, 8).hex()
            log.write(json.dumps(dict(step=step, ret=hex(ret), a0=a0, **{k: hex(v) for k, v in R.items()})) + '\n'); log.flush()
            emu.send('s 1'); step += 1
        else:
            step += int(head.split()[4])
        apply()
    emu.save(str(ROOT / f'{out}.snap')); emu.close()

if __name__ == '__main__':
    main(sys.argv[1:])
