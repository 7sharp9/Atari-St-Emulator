"""Natural-run check of the needs tick (README, "Needs and the clock"): runs house.snap for N steps under `stserver`
with write watches on the clock, needs, illness and happy words and a read watch on the tick's own read of the frame
counter (`$2464e`). At every tick it runs `lcp_model.needs_tick` on the state so far and checks the last value the
tick's code (`$24648..$24933`) wrote to each word against the model, and that the tick wrote nothing the model leaves
unchanged. Writes by any other code (the man drinking, eating, peeing) are applied to the state as observed. The house
-event roll is not checked (other code draws from the same TOS seed); it changes no watched word.

usage: natural_tick.py [total_steps] [chunk_steps]
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import lcp_model as m  # noqa: E402
from stclient import StServer  # noqa: E402

TOTAL = int(float(sys.argv[1])) if len(sys.argv) > 1 else 1_800_000_000
CHUNK = int(float(sys.argv[2])) if len(sys.argv) > 2 else 50_000_000
KEYS = [k for k in m.TICK if k not in ('event_block', 'away', 'event_flag')]
ADDR = {m.TICK[k]: k for k in KEYS}
TICK_LO, TICK_HI = 0x24648, 0x24933


def w16(v):
    return v - 0x10000 if v & 0x8000 else v


s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
st = {k: w16(int.from_bytes(s.read(m.TICK[k], 2), 'big')) for k in m.TICK}
st['evq'] = [-1] * 10; st['seed'] = 1
start = dict(st)
ids = [s('watch_add', lo=lo, hi=hi, kind='w', max_events=400000)['id'] for lo, hi in
       ((0x5144e, 0x51475), (0x4ca20, 0x4ca23), (0x55102, 0x55103), (0x4c592, 0x4c593), (0x51424, 0x51425),
        (0x2ae18, 0x2ae1f), (0x3dcd0, 0x3dcd1), (0x4097c, 0x4097d))]
rid = s('watch_add', lo=0x51424, hi=0x51425, kind='r', pc_lo=0x2464e, pc_hi=0x2464e, max_events=400000)['id']
ticks = ok = 0; bad = []; other = {}; pending = None


def settle():
    """Compare the writes of the tick just finished with the model's prediction."""
    global ok
    pred, base, wrote = pending
    want = {a: pred[k] for a, k in ADDR.items() if pred[k] != base[k]}
    if all(want.get(a, base[ADDR[a]]) == v for a, v in wrote.items()) and all(wrote.get(a) == v for a, v in want.items()):
        ok += 1
    elif len(bad) < 10:
        bad.append({ADDR[a]: (base[ADDR[a]], want.get(a), wrote.get(a)) for a in set(want) | set(wrote)
                    if want.get(a) != wrote.get(a)})
    for k in KEYS:
        st[k] = base[k] if (m.TICK[k] not in wrote) else wrote[m.TICK[k]]


done = 0
while done < TOTAL:
    s('run', max_steps=min(CHUNK, TOTAL - done)); done += min(CHUNK, TOTAL - done)
    evs = []
    for i in ids + [rid]:
        r = s('watch_events', id=i)[0]
        if r['dropped']:
            sys.exit(f'watch {i} dropped {r["dropped"]} events: lower the chunk')
        for e in r['events']:
            evs.append((e['step'], i == rid, e))
    evs.sort(key=lambda x: (x[0], not x[1]))
    for step, is_tick, e in evs:
        a = int(e['addr'].lstrip('$'), 16); pc = int(e['pc'].lstrip('$'), 16)
        if is_tick:
            if pending:
                settle()
            ticks += 1
            pending = (m.needs_tick(st), dict(st), {})
            continue
        vals = []
        v = int(e['value'].lstrip('$'), 16)
        if e['width'] == 4:
            vals = [(a, v >> 16), (a + 2, v & 0xffff)]
        elif e['width'] == 2:
            vals = [(a, v)]
        else:
            vals = [(a & ~1, None)]     # a byte write: re-read later is not possible; flag it
        for aa, vv in vals:
            if aa not in ADDR:
                continue
            if TICK_LO <= pc <= TICK_HI and pending:
                pending[2][aa] = w16(vv)
            else:
                if pending:                 # the tick's writes are contiguous: it has finished
                    settle(); pending = None
                other[e['pc']] = other.get(e['pc'], 0) + 1
                if vv is None:
                    sys.exit(f'byte write to {e["addr"]} at {e["pc"]}: not modelled')
                st[ADDR[aa]] = w16(vv)
    print(f'{done:>13,} steps: ticks {ticks}, match {ok}, hour {st["hour"]}:{st["min"]:02d}:{st["sec"]:02d}', flush=True)
if pending:
    settle()
s.close()
print('start', {k: start[k] for k in KEYS})
print('end  ', {k: st[k] for k in KEYS})
print(f'ticks {ticks}, model matched {ok}; writes by other code (pc: count): {other}')
for b in bad:
    print('MISMATCH (word: before, model, game)', b)
