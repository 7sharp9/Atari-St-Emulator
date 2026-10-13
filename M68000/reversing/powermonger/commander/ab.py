"""ab.py [pair ...]: direct order vs A* leg orders, same snapshot, same budget (move.py's proof 1).

Each pair is (name, snap, side, k, goal cell, final order type). Two arms, each one persistent emulator
(commander loop.py's Emu over the REPL pipes), RAM read with `m` every CHUNK steps (reads do not change the
emulation), BUDGET steps in all:
  direct : at step 0 take the side's slot (state 2) and send the final order straight at the goal cell
  legs   : at step 0 take the slot; a move.Mover then sends leg 1 as a go to `$02`, the next leg when the lead
           stands in the leg cell, and the final order from the last leg; re-plan on a stall
Arrival: the first read at which the lead stands in the goal cell (and, for a final go to, the group is camped,
state 6). Also reported: the closest approach (Chebyshev, world units) to the goal centre, the end position, mode
and state, and the tick model's verdict on the straight walk (Map.simulate_walk, 3000 ticks).
Build the boat-stripped starts first: prep.py rand1 $CMD_WORK/move/prep1.snap 20e6 2:0 3:0 3:1 4:0 and
prep.py pm143/run/rand1_s2 $CMD_WORK/move/prep2.snap 20e6 3:0 2:0 4:2 (gate_move.sh does both).
Output: $CMD_WORK/move/ab/<pair>_<arm>.jsonl (one line per read) and a summary table on stdout and in ab/summary.txt.
BUDGET (default 80e6), CHUNK (1e6), PAR (6) from the environment."""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from move import ROOT, CMD, Map, Mover, centre, lead_speed, plan_legs, GOTO
sys.path.insert(0, str(CMD))
from observe import observe, load          # noqa: E402
from act import from_json                  # noqa: E402
from loop import Emu, REGIONS              # noqa: E402

HERE = Path(__file__).resolve().parent
WORK = ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'move'
OUT = WORK / 'ab'
OUT.mkdir(parents=True, exist_ok=True)
BUDGET = int(float(os.environ.get('BUDGET', '80e6')))
CHUNK = int(float(os.environ.get('CHUNK', '1e6')))
R1 = 'scratchpad/pm142/rand1.snap'
P1 = str((WORK / 'prep1.snap').relative_to(ROOT))   # prep.py rand1 +20M: sides 2..4 taken, 2:0 3:0 3:1 4:0 boats stripped
P2 = str((WORK / 'prep2.snap').relative_to(ROOT))   # prep.py rand1_s2 +20M: sides 2..4 taken, 3:0 2:0 4:2 boats stripped
PAIRS = {
    'p1': (R1, 1, 0, (23, 120), GOTO),      # the local captain (no boats on rand1, no poke)
    'p2': (R1, 1, 0, (15, 119), GOTO),
    'p3': (P1, 4, 0, (48, 86), GOTO),
    'p4': (P1, 4, 0, (18, 59), GOTO),
    'p5': (P1, 4, 0, (20, 91), GOTO),
    'p6': (P1, 3, 1, (19, 65), GOTO),       # group 1: every order goes by pigeon
    'p7': (P1, 3, 1, (11, 66), 0x08),       # get men at own lord 0 (11,66)
    'p8': (P2, 3, 0, (48, 86), GOTO),
    'p9': (P2, 4, 2, (36, 51), GOTO),       # group 2, pigeon
    'p10': (R1, 1, 0, (15, 92), 0x08),      # get men at own lord 9: the tick model says the $48 sweep arrives
    'b1': (R1, 3, 0, (46, 89), GOTO),       # boat control: 12 boats held, the model's blocked leg is crossed
}


def arm(name, mode):
    snap, side, k, goal, ftype = PAIRS[name]
    R0 = load(ROOT / snap)
    mp = Map(R0)
    emu = Emu(ROOT / snap, OUT / f'{name}_{mode}.err')
    log = open(OUT / f'{name}_{mode}.jsonl', 'w')
    mv = Mover(mp, side, k, goal, ftype) if mode == 'legs' else None
    clock, arrived, best, nord, rec = 0, None, 1 << 30, 0, None
    gc = centre(goal)
    t0 = time.time()
    while True:
        R = emu.read('m', None)
        obs = observe(R)
        g = obs['sides'][side]['groups'][k]
        acts = [dict(side=side, take=True)] if clock == 0 else []
        if mode == 'direct':
            if clock == 0:
                acts.append(dict(side=side, type=ftype, x=goal[0], y=goal[1], group=k))
        else:
            acts += mv.tick(obs, R, clock)
        if acts:
            emu.mem(0x58010, 0x40)
            emu.poke(from_json(emu.ram, acts))
            nord += sum(1 for a in acts if 'type' in a)
        lo = g.get('lead_obj', {})
        pos = (lo.get('x'), lo.get('y'))
        d = max(abs(pos[0] - gc[0]), abs(pos[1] - gc[1])) if lo else None
        if d is not None:
            best = min(best, d)
        at = lo and tuple(lo['cell']) == tuple(goal) and (ftype != GOTO or g['state'] == 6)
        final_out = mode == 'direct' or (mv and mv.done)
        if at and final_out and arrived is None:
            arrived = clock
        rec = dict(step=clock, pos=pos, cell=lo.get('cell'), mode=lo.get('mode'), state=g['state'], men=g['men'],
                   w4=g['raw_w4'], acts=[a for a in acts if 'type' in a])
        log.write(json.dumps(rec) + '\n')
        if clock >= BUDGET:
            break
        n, hit = emu.run(CHUNK)
        clock += n
        if hit:
            break
    emu.close()
    if mv:
        log.write(json.dumps(dict(events=mv.events, failed=mv.failed, replans=mv.replans)) + '\n')
    log.close()
    return dict(name=name, mode=mode, arrived=arrived, best=best, end=rec, orders=nord,
                legs=(mv.legs if mv else None), replans=(mv.replans if mv else None), failed=(mv.failed if mv else None),
                wall=round(time.time() - t0, 1))


def main(names):
    names = names or list(PAIRS)
    jobs = [(n, m) for n in names for m in ('direct', 'legs')]
    with ThreadPoolExecutor(int(os.environ.get('PAR', '6'))) as ex:
        res = list(ex.map(lambda j: arm(*j), jobs))
    lines = [f'budget {BUDGET} steps, read every {CHUNK}']
    for n in names:
        snap, side, k, goal, ftype = PAIRS[n]
        R0 = load(ROOT / snap); mp = Map(R0); g = observe(R0)['sides'][side]['groups'][k]
        pos = (g['lead_obj']['x'], g['lead_obj']['y']); sp = lead_speed(R0, g['lead'])
        straight = mp.leg(pos, centre(goal), sp)
        sim = mp.simulate_walk(pos, centre(goal), sp, 3000)
        lines.append(f'{n}: {Path(snap).stem} side {side} group {k} lead {pos} cell {g["lead_obj"]["cell"]} speed {sp} -> '
                     f'goal {goal} order {ftype:02x}; straight leg {"walks" if straight[0] else "blocked " + str(straight[2])}; '
                     f'tick model straight: {"arrives" if sim[0] else "stuck at " + str(sim[2])}')
        for r in res:
            if r['name'] != n: continue
            e = r['end']
            lines.append(f'   {r["mode"]:6s} arrived {"yes at " + str(r["arrived"]) if r["arrived"] is not None else "NO"}'
                         f' | closest {r["best"]} | end cell {e["cell"]} pos {e["pos"]} mode {e["mode"]:02x} state {e["state"]}'
                         f' | orders {r["orders"]}' + (f' legs {r["legs"]} replans {r["replans"]} failed {r["failed"]}'
                                                       if r['mode'] == 'legs' else '') + f' | {r["wall"]} s')
    txt = '\n'.join(lines)
    print(txt)
    (OUT / ('summary.txt' if not sys.argv[1:] else 'summary_' + '_'.join(names) + '.txt')).write_text(txt + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
