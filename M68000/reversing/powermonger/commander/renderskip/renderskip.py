"""renderskip.py: does stubbing PowerMonger's renderers leave the simulation state unchanged per game tick, and how
many steps does it save? (README.md beside this file holds the result.)

    renderskip.py run  <snap> <arm> <outdir> [--rungs 10,100,1000] [--dump] [--disk <st>] [--tag <name>]
                       [--actions <json list> --gap-ticks G]
    renderskip.py arms

One stserver process: load <snap> (+ disk), apply the arm's pokes, then run tick by tick. A tick boundary is an
arrival at the tick body's entry $13000 (strategy.md "Where it runs"); the tick index is k = clock - clock0 with the
sim clock the long at $2df70 (incremented once per tick at $1302e) read at that arrival, clock0 its value at the first
arrival after the load. At k in rungs the cumulative step count and wall time are written as one JSON line to
<outdir>/<arm>.jsonl, and with --dump the whole 1 MB RAM to <outdir>/<arm>_k<k>.ram (compare.py diffs them).

--actions: a candidate's action list (commander act.from_json format); action i is poked at the first arrival at tick
k = i*G (or at the action's own "tick" key), through act.Poker on the live bytes around the command buffer, as rollout.py pokes action i at step i*gap.

Arms are pokes applied right after load: an `rts` ($4e75) at a routine's entry, or data words.
"""
import json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else \
    next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer             # noqa: E402
sys.path.insert(0, str(ROOT / 'reversing' / 'powermonger' / 'commander'))
from act import from_json                 # noqa: E402

TICK = 0x13000            # pm_tick entry
CLOCK = 0x2df70           # sim clock long, addq.l #1 at $1302e
RTS = 0x4e75

# Each arm: list of (addr, width, value). Routine names are from their own bodies (README "Arms").
ARMS = {
    'base': [],
    'f898': [(0xf898, 2, RTS)],                                    # terrain raster / grid walk (sprites inline)
    'gated': [(0xf898, 2, RTS), (0x178ae, 2, RTS), (0x12ce0, 2, RTS)],   # + HUD bars + master->back-buffer copy
    'draw': [(0xf898, 2, RTS), (0x178ae, 2, RTS), (0x12ce0, 2, RTS),
             (0x17878, 2, RTS), (0x165b2, 2, RTS)],                # + compass + minimap people dots
    'drawall': [(0xf898, 2, RTS), (0x178ae, 2, RTS), (0x12ce0, 2, RTS),
                (0x17878, 2, RTS), (0x165b2, 2, RTS), (0x7a56, 2, RTS), (0x1870, 2, RTS)],  # + requesters + VBL wait
    'divider': [(0x57fee, 2, 0x7fff), (0x57ff0, 2, 0x7fff)],        # the game's own present-rate divider
    # negative controls: stubs that skip simulation routines
    'neg_1abaa': [(0x1abaa, 2, RTS)],                              # seasons: steps the LCG $57ff6 and $57fec
    'neg_3e06': [(0x3e06, 2, RTS)],                                # flag health / armies eat / $57fba group term
}


def main(argv):
    if argv[0] == 'arms':
        print(json.dumps({k: [[hex(a), w, hex(v)] for a, w, v in p] for k, p in ARMS.items()}, indent=1))
        return 0
    a = list(argv)
    opt = lambda name, d: (a.pop(a.index(name) + 1), a.remove(name))[0] if name in a else d
    rungs = sorted(int(x) for x in opt('--rungs', '10,100,1000').split(','))
    disk = opt('--disk', str(ROOT / 'scratchpad' / 'powermonger.st'))
    tag = opt('--tag', None)
    acts = opt('--actions', None)
    gapk = int(opt('--gap-ticks', '2'))
    sched = {}
    if acts:
        for i, ac in enumerate(json.load(open(acts))):
            sched.setdefault(ac.pop('tick', i * gapk), []).append(ac)
    dump = '--dump' in a
    if dump:
        a.remove('--dump')
    _, snap, arm, out = a
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    tag = tag or arm
    s = StServer(str(ROOT))
    t_load = time.time()
    s('load', snapshot=str(Path(snap).resolve()), disk=disk)
    for addr, w, v in ARMS[arm]:
        s('poke', addr=addr, width=w, value=v)
    step0 = int(s('regs')['step'])
    t0 = time.time()
    clock0 = None
    k = -1
    log = open(out / f'{tag}.jsonl', 'w')
    for N in rungs:
        while k < N:
            r = s('run', max_steps=20_000_000, until_pc=TICK)
            if r['reason'] != 'until':
                log.write(json.dumps(dict(arm=arm, error=r, k=k)) + '\n'); log.close()
                sys.exit(f'{arm}: run ended {r["reason"]} at k={k}')
            c = int.from_bytes(s.read(CLOCK, 4), 'big')
            if clock0 is None:
                clock0 = c
            k = c - clock0
            if k in sched:
                ram = bytearray(0x100000)
                ram[0x58000:0x58100] = s.read(0x58000, 0x100)
                for line in from_json(ram, sched.pop(k)):
                    _, ad, hx = line.split()
                    s('poke', addr=int(ad, 16), width=4, value=int(hx, 16))
        step = int(s('regs')['step'])
        row = dict(snap=str(snap), arm=arm, tag=tag, k=k, clock=clock0 + k, steps=step - step0, wall_s=round(time.time() - t0, 3),
                   load_s=round(t0 - t_load, 3), uptime=os.popen('uptime').read().strip())
        if dump:
            p = out / f'{tag}_k{k}.ram'
            p.write_bytes(s.read(0, 0x100000))
            row['ram'] = str(p)
        log.write(json.dumps(row) + '\n'); log.flush()
        print(json.dumps(row), flush=True)
    s.close()
    s.p.wait(timeout=30)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
