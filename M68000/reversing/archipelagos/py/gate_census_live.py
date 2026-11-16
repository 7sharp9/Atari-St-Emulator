#!/usr/bin/env python3
"""gate_census_live.py: the model census's three findings (README, "Over all island numbers") checked in the emulator.

Each island is built by the game under `stserver` (tools/stclient.py), from the snapshots py/run_drive.sh writes:
  N > 100:  n2.snap (map screen), POKE `$1d566` = N, space (as capture_islands.sh)
  N <= 100: n0.snap, a character and Return, POKE `$1d566` = N at the entry of the block loader `$1b142`
            (as capture_pictures.sh; a map-screen poke keeps island 1's block)
then run to the `$15a20` entry (snapshot saved), write watches on `$1700..$2fff` and `$13000..$148ff`, and run to the
`$15b8e` return. Every run must stop on the `$15b8e` breakpoint (a watch that finds nothing is bounded by that).

1. Writes outside the map: a write in either range is the builder's when its PC is in the builder's code
   `$15a20..$1663f`, else interrupt-time code. The builder's writes must all be word pushes into its own stack below
   the entry SP; no byte write (the cells are bytes). The interrupt-time writes are compared, as (PC, address)
   pairs, with an idle window of the same length on the map screen (n2.snap, no space).
   POSITIVE CONTROL (POKE at the `$15a20` entry of island 150, as census.py's edge_control): range table `$1698c` =
   03 ff 00 00 (stamps start on rows 0..3), thresholds `$16980/2/4` = 0, 0, 100 (every stamp a circle). The
   builder must then write bytes outside the map; they are compared with the model's out-of-map changes.
2. N and N + 64: the 21-word block at `$1697a` at the entry, word by word, and the two maps.
3. Live sample: the model (island_model.py on the entry snapshot) against the game's map at `$15b8e`, 65536 cells.

usage: uv run python reversing/archipelagos/py/gate_census_live.py     (from M68000/; about a minute on 4 servers)
       J=<servers> (default 4). Writes scratchpad/archipelagos/census_live/: ent_<N>.snap, results.json.
"""
import os, sys, json, random
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import island_model as im
ROOT = im.d
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer
from gfxview import load_ram

W = os.path.join(ROOT, 'scratchpad', 'archipelagos')
OUT = os.path.join(W, 'census_live')
DISK = os.path.join(W, 'tmb58.st')
RANGES = ((0x1700, 0x2fff), (0x13000, 0x148ff))
BUILDER = (0x15a20, 0x1663f)
ENTRY_SP = None   # read per run

# 1: 150 and 4321; above 100 the largest stamp counts (145, 132: 59 stamps, so also the largest start squares,
# side 3 * 59 - 20) and the largest stamp sizes P_c (140, 163), 119 (stamps nearest an edge above 100 after 132);
# the disk islands whose stamps start nearest an edge in the model (81: 32 cells, 93: 37, 28: 49; 79, a circle at 59;
# census.py --edges).
F1 = [150, 4321, 145, 132, 140, 163, 119, 81, 93, 28, 79]
F2 = [(150, 214), (4321, 4385), (9000, 9064), (1000, 1064)]
rnd = random.Random(1989)
F3 = {f'{lo}-{hi}': sorted(rnd.sample(range(lo, hi + 1), 5)) for lo, hi in ((101, 1000), (1001, 3000), (3001, 6000), (6001, 9999))}
F3['disk'] = sorted(rnd.sample([n for n in range(2, 100) if n % 5 and n not in (6, 99)], 5))
CONTROL = 'ctl150'

h = lambda x: int(str(x).lstrip('$'), 16)


def reach(s, N):
    if N > 100:
        s('load', snapshot=os.path.join(W, 'n2.snap'), disk=DISK)
        s('poke', addr=0x1d566, width=2, value=N)
        s('kbd', bytes=[0x39]); s('step', n=40000); s('kbd', bytes=[0xb9])
    else:
        s('load', snapshot=os.path.join(W, 'n0.snap'), disk=DISK)
        for b, n in ((0x02, 40000), (0x82, 100000), (0x1c, 40000)):
            s('kbd', bytes=[b]); s('step', n=n)
        s('kbd', bytes=[0x9c])
        s('bp_set', addrs=[0x1b142]); r = s('run', max_steps=3000000); s('bp_clear', addrs=[0x1b142])
        assert r['reason'] == 'breakpoint' and h(r['pc']) == 0x1b142, (N, r)
        s('poke', addr=0x1d566, width=2, value=N)
    s('bp_set', addrs=[0x15a20]); r = s('run', max_steps=8000000); s('bp_clear', addrs=[0x15a20])
    assert r['reason'] == 'breakpoint' and h(r['pc']) == 0x15a20, (N, r)


def watch_run(s, steps=None, stop_pc=None):
    ids = [s('watch_add', lo=lo, hi=hi, kind='w', max_events=5000000)['id'] for lo, hi in RANGES]
    if stop_pc:
        s('bp_set', addrs=[stop_pc]); r = s('run', max_steps=60000000); s('bp_clear', addrs=[stop_pc])
    else:
        r = s('run', max_steps=steps)
    ev, dropped = [], 0
    for i in ids:
        for w in s('watch_events', id=i):
            ev += w['events']; dropped += w['dropped']
        s('watch_remove', id=i)
    return r, [(h(e['pc']), h(e['addr']), e['width'], h(e['value'])) for e in ev], dropped


def build(s, key):
    N = 150 if key == CONTROL else key
    reach(s, N)
    if key == CONTROL:
        for a, v, wd in ((0x1698c, 0x03ff, 2), (0x1698e, 0, 2), (0x16980, 0, 2), (0x16982, 0, 2), (0x16984, 100, 2)):
            s('poke', addr=a, width=wd, value=v)
    sp = h(s('regs')['a7'])
    block = s.read(0x1697a, 42).hex()
    snap = os.path.join(OUT, f'ent_{key}.snap'); s('save', path=snap)
    r, ev, dropped = watch_run(s, stop_pc=0x15b8e)
    done = r['reason'] == 'breakpoint' and h(r['pc']) == 0x15b8e
    return dict(key=key, N=N, sp=sp, block=block, snap=snap, reached=done, reason=r['reason'], pc=r['pc'], steps=r['steps'],
                events=ev, dropped=dropped, map=s.read(0x3000, 0x10000).hex() if done else None)


def idle(snap, steps, chunk=1000000):
    """(PC, address) pairs written in the two ranges over `steps` from `snap` with no input, read in chunks."""
    s = StServer(ROOT)
    s('load', snapshot=os.path.join(W, snap), disk=DISK)
    pairs, n, dropped = set(), 0, 0
    for k in range(0, steps, chunk):
        r, ev, d = watch_run(s, steps=min(chunk, steps - k))
        pairs |= {(pc, a) for pc, a, _, _ in ev}; n += len(ev); dropped += d
    s.close()
    return pairs, n, dropped


class LogRam(bytearray):
    """The model's RAM copy, logging each write outside the map in order (the control only: it is slow)."""
    def __setitem__(self, i, v):
        if not 0x3000 <= i < 0x13000: self.log.append(i)
        super().__setitem__(i, v)


def model(row):
    ram, _ = load_ram(row['snap'])
    M = im.Model(bytearray(ram))
    if row['key'] == CONTROL:
        M.m = LogRam(M.m); M.m.log = []
    cells = M.run(open(DISK, 'rb').read())
    out = {a for a in range(len(ram)) if not (0x3000 <= a < 0x13000) and ram[a] != M.m[a]}
    return cells, sorted(out), M.shapes, getattr(M.m, 'log', None)


def worker(keys):
    s = StServer(ROOT)
    try:
        return [build(s, k) for k in keys]
    finally:
        s.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    keys = list(dict.fromkeys(F1 + [n for p in F2 for n in p] + [n for v in F3.values() for n in v] + [CONTROL]))
    J = int(os.environ.get('J', '4'))
    with ThreadPoolExecutor(J) as ex:
        rows = [r for part in ex.map(worker, [keys[i::J] for i in range(J)]) for r in part]
    R = {r['key']: r for r in rows}
    with Pool(min(10, len(rows))) as p:
        for r, (cells, out, shapes, log) in zip(rows, p.map(model, rows)):
            r['model_out'] = out; r['shapes'] = shapes; r['model_log'] = log
            r['cells'] = sum(a == b for a, b in zip(cells, bytes.fromhex(r['map']))) if r['map'] else None
    print(f'census_live: {len(rows)} builds; reached $15b8e: {sum(r["reached"] for r in rows)}/{len(rows)}; '
          f'watch events dropped: {sum(r["dropped"] for r in rows)}')

    # 1. writes outside the map
    idle_steps = max(r['steps'] for r in rows if r['reached'])
    with ThreadPoolExecutor(2) as ex:
        idles = dict(zip(('n2', 'n0'), ex.map(lambda sn: idle(sn, idle_steps), ('n2.snap', 'n0.snap'))))
    ipairs = idles['n2'][0] | idles['n0'][0]; ipcs = {pc for pc, _ in ipairs}
    print(f'1. writes in ${RANGES[0][0]:x}..${RANGES[0][1]:x} and ${RANGES[1][0]:x}..${RANGES[1][1]:x} during the build '
          f'($15a20 entry to $15b8e return); builder code ${BUILDER[0]:x}..${BUILDER[1]:x}')
    low = min(e[1] for e in R[150]['events'] if BUILDER[0] <= e[0] <= BUILDER[1] and e[2] != 1 and e[1] < R[150]['sp'])
    clean = 0
    for k in F1 + [CONTROL]:
        r = R[k]; ev = r['events']
        b = [e for e in ev if BUILDER[0] <= e[0] <= BUILDER[1]]
        o = [e for e in ev if not BUILDER[0] <= e[0] <= BUILDER[1]]
        bbytes = [e for e in b if e[2] == 1]
        stack = [e for e in b if e[2] != 1 and e[1] < r['sp']]
        rest = [e for e in b if e[2] != 1 and e[1] >= r['sp']]
        bspan = f'${min(e[1] for e in stack):x}..${max(e[1] + e[2] - 1 for e in stack):x}' if stack else '-'
        onew = {(pc, a) for pc, a, _, _ in o} - ipairs
        ostack = {(pc, a) for pc, a in onew if r['sp'] - 0x100 <= a < r['sp']}
        oother = onew - ostack
        opc = {e[0] for e in o} - ipcs
        ok = r['reached'] and not bbytes and not rest and (k == CONTROL or not (oother or opc))
        clean += ok and k != CONTROL
        line = (f'   {str(k):>6}: reached {r["reached"]}, steps {r["steps"]}; builder writes {len(b)} '
                f'(word pushes below SP ${r["sp"]:x}: {len(stack)}, span {bspan}; byte writes {len(bbytes)}; other {len(rest)}); '
                f'interrupt-time writes {len(o)} from {len({e[0] for e in o})} PCs ({len(opc)} not in the idle window); '
                f'(PC, address) pairs not in the idle window: {len(ostack)} on the stack'
                + (f' ${min(a for _, a in ostack):x}..${max(a for _, a in ostack):x}' if ostack else '') + f', {len(oother)} elsewhere')
        print(line)
        if k == CONTROL:
            seq = [e[1] for e in bbytes if not 0x3000 <= e[1] < 0x13000]
            mlog = r['model_log']
            pre = next((i for i, (x, y) in enumerate(zip(seq, mlog)) if x != y), min(len(seq), len(mlog)))
            st = next((i for i, a in enumerate(seq) if low <= a < r['sp']), len(seq))
            print(f'   control: the build ends with reason {r["reason"]!r} at PC ${h(r["pc"]):x} after {r["steps"]} steps, '
                  f'before $15b8e; its out-of-map byte writes in order equal the model\'s for the first {pre} of {len(seq)}; '
                  f'the first write into the builder\'s own pushes (${low:x}..${r["sp"] - 1:x} '
                  f'in island 150\'s build) is write {st + 1} (${seq[st]:x}, by the fill); the model runs on to {len(mlog)} out-of-map writes')
            live = sorted({e[1] for e in bbytes})
            print(f'   control: builder byte writes outside the map {len(bbytes)} at {len(live)} addresses '
                  f'${live[0]:x}..${live[-1]:x}, PCs {" ".join(f"${x:x}" for x in sorted({e[0] for e in bbytes}))}'
                  if live else '   control: no builder byte write outside the map')
    for sn, (pp, n, d) in idles.items():
        print(f'   idle window ({sn}.snap, {idle_steps} steps, no input): {n} writes, {len(pp)} (PC, address) pairs, '
              f'PCs ${min(pc for pc, _ in pp):x}..${max(pc for pc, _ in pp):x}; builder PCs in it: '
              f'{sum(BUILDER[0] <= pc <= BUILDER[1] for pc, _ in pp)}; dropped {d}')
    print(f'   no builder write outside the map other than its stack: {clean}/{len(F1)} islands')

    # 2. N and N + 64
    print('2. N and N + 64: the 21 words at $1697a at the entry, and the maps at $15b8e')
    for a, b in F2:
        A, B = bytes.fromhex(R[a]['block']), bytes.fromhex(R[b]['block'])
        eq = [A[i:i + 2] == B[i:i + 2] for i in range(0, 42, 2)]
        diff = [f'${0x1697a + 2 * i:x}' for i, e in enumerate(eq) if not e]
        same_cells = sum(x == y for x, y in zip(bytes.fromhex(R[a]['map']), bytes.fromhex(R[b]['map'])))
        print(f'   {a}/{b}: words equal {sum(eq)}/21 (differ: {" ".join(diff) or "-"}); maps equal in {same_cells}/65536 cells; '
              f'model {R[a]["cells"]}/65536 and {R[b]["cells"]}/65536')

    # 3. live sample
    print('3. live sample: model vs the game map at $15b8e')
    allk = [k for k in keys if k != CONTROL]
    for g, ns in F3.items():
        print(f'   {g:>9}: ' + ', '.join(f'{n} {R[n]["cells"]}' for n in ns) +
              f'  -> {sum(R[n]["cells"] == 65536 for n in ns)}/{len(ns)} full')
    full = sum(R[k]['cells'] == 65536 for k in allk)
    print(f'   all live builds (findings 1-3): {full}/{len(allk)} islands match 65536/65536')
    sh = {s_: sum(R[k]['shapes'][s_] for k in allk) for s_ in ('walk', 'wander', 'circle', 'rect')}
    print(f'   stamps over these islands: {sh}')
    for r in rows: r.pop('events')
    json.dump(rows, open(os.path.join(OUT, 'results.json'), 'w'))


if __name__ == '__main__':
    main()
