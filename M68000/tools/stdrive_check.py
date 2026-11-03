"""Checks for `stdrive.py`'s hold / wait_until / ab / journal, on Impossamole's boss room.

    uv run python tools/stdrive_check.py <seg5_pit_exit.snap> <impossamole .st> <outdir> [--dll stserver.dll]

Each check prints PASS or FAIL with its numbers:
  1. `hold` refuses a hold shorter than the poll period, and an aligned press lands on a VBL step (step % 12000 == 0).
  2. `ab` with a right-walk hold moves hero x and the control does not; `ab` with no input on either arm differs nowhere
     (the negative control), and both arms end at the same step.
  3. `wait_until(hero x == x0 + 20)` under a held right stops at the step of the write that made it true: from the same
     fork, a non-stop watch over the same field lists the writes, and the first one with that value is at the step
     `wait_until` returned (events report the post-increment step, as REPL `watch` lines do).
  4. The journal (fork/restore from `ab` included) replays to byte-identical saved snapshots.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stdrive as sd

HERO_X = 0x1a574
FIELDS = {'hero_x': (HERO_X, 2), 'hero_y': (0x1a576, 2), 'health': (0xbb74, 1), 'boss_x': (0x1a5e0, 2)}
PERIOD = 24000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap'); ap.add_argument('disk'); ap.add_argument('outdir')
    ap.add_argument('--dll')
    ap.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    jpath = os.path.join(a.outdir, 'check.jsonl')
    d = sd.Drive(a.root, dll=a.dll, journal=jpath, fields=FIELDS, period=PERIOD)
    d.load(a.snap, a.disk)
    ok = []

    def check(name, cond, info):
        ok.append(cond)
        print(('PASS ' if cond else 'FAIL ') + name + ': ' + info, flush=True)

    # 1
    try:
        d.hold(sd.Joy(0x08), steps=PERIOD - 1)
        refused = False
    except ValueError:
        refused = True
    t_press, t_rel = d.hold(sd.Joy(0x00), polls=1)
    check('hold guard and alignment', refused and t_press % sd.FRAME == 0 and t_rel - t_press == PERIOD,
          f'short hold refused={refused}, press at {t_press} (mod {sd.FRAME} = {t_press % sd.FRAME}), held {t_rel - t_press}')
    d.step(5 * PERIOD)          # let the hero settle

    # 2
    r = d.ab(lambda d: d.hold(sd.Joy(0x08), polls=4), budget=10 * PERIOD, save_dir=a.outdir)
    print(r.report())
    xa, xb = int.from_bytes(r.a['fields']['hero_x'], 'big'), int.from_bytes(r.b['fields']['hero_x'], 'big')
    check('ab input arm against control', 'hero_x' in [x[0] for x in r.diff] and r.a['step'] == r.b['step'],
          f'hero x input {xa} control {xb}, steps {r.a["step"]} / {r.b["step"]}')
    n = d.ab(None, budget=10 * PERIOD)
    check('ab negative control (no input either arm)', not n.changed, f'{len(n.diff)} ranges differ')

    # 3
    x0 = d.field('hero_x')
    target = x0 + 20
    f = d.fork()
    d.press(sd.Joy(0x08))
    wres = d.wait_until(HERO_X, target, mask=0xffff, width=2, budget=40 * PERIOD)
    end_w = d.step_count
    d.restore(f)
    t0 = d.step_count
    wid = d.rpc('watch_add', lo=HERO_X, hi=HERO_X + 1, kind='w')['id']
    d.press(sd.Joy(0x08))
    d.step(40 * PERIOD)
    ev = d.rpc('watch_events', id=wid)[0]['events']
    d.rpc('watch_remove', id=wid)
    first = next((e for e in ev if int(e['value'].lstrip('$'), 16) == target), None)
    d.release(sd.Joy(0x08))
    check('wait_until stops at the write', wres.ok and first is not None and first['step'] == end_w,
          f'x0 {x0} target {target}: wait_until {wres} ended at step {end_w}; watch: {len(ev)} writes from {t0}, '
          f'first with the value at step {first and first["step"]} pc {first and first["pc"]}')
    d.drop(f)
    end = d.save(os.path.join(a.outdir, 'check_end.snap'))
    d.close()

    # 4
    saves = sd.replay(jpath, os.path.join(a.outdir, 'replay'), a.root, a.dll)
    same = [open(o, 'rb').read() == open(n, 'rb').read() for o, n in saves]
    check('journal replay', all(same) and len(same) == 3, f'{sum(same)} of {len(same)} saved snapshots identical ({", ".join(os.path.basename(o) for o, _ in saves)})')
    print(f'{sum(ok)} of {len(ok)} checks pass')
    sys.exit(0 if all(ok) else 1)


if __name__ == '__main__':
    main()
