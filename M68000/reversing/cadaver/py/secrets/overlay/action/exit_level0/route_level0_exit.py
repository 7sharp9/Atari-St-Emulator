"""route_level0_exit.py <OUTDIR> [START] [--upto=heal|d1|e1|g1|g2]: the whole natural chain out of level 0 (Cadaver 88th pass).  Zero injected input, nothing poked.

    cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/exit_level0/route_level0_exit.py OUTDIR [START.snap] [--upto=<segment>]      (about 4 min, one emulator process at a time)

START defaults to scratchpad/cadaver/secrets_out/action/rwn2/taken53.snap (the treasury, room 37, crown 53 and key 104 carried, health 35).  Five segments, each started from the previous one's last snapshot:
  heal  ../route_heal_chain.py            treasury -> room 16 -> heal road (flask 392) -> room 13, door $2a opened      hand-off heal/ck_71_L_stall_2a.snap
  d1    d1/route_gems_to_room27.py        room 13 -> gems 164 and 290 -> hole of room 21 -> room 27                     hand-off d1/gems/ last numbered snapshot
  e1    e1/route_room27_to_room22_natural.py   room 27 -> urn 143 and key 167 -> room 22                                 hand-off e1/route/ last numbered snapshot
  g1    g1/route_room22_to_altar99.py     room 22 -> room 40 (371, 110) -> altar 99 (324 in front, phases A-D)          hand-off g1/D_end.snap
  g2    g2/route_altar_to_room36_real.py  altar 99 -> READ MAGIC, 324 -> room 38 -> door $2a -> room 36, MASSACRE -> room 60
Every output lives under OUTDIR/<segment>/ (checkpoint snapshots, log.txt, _scratch/ = the libs' own working dirs, CAD_OUT).  Prints one line per segment and the final room/health/XP; exits non-zero on any failure.
The hand-off rule is the one of the 88th-pass driver full_chain.sh: the last snapshot whose name starts with digits (sorted by name)."""
import sys, os, re, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HERE, *(['..'] * 7)))
ACT = os.path.join(ROOT, 'reversing', 'cadaver', 'py', 'secrets', 'overlay', 'action')
DEFAULT_START = os.path.join(ROOT, 'scratchpad', 'cadaver', 'secrets_out', 'action', 'rwn2', 'taken53.snap')
SEGS = ['heal', 'd1', 'e1', 'g1', 'g2']


def last_numbered(d):
    names = sorted(n for n in os.listdir(d) if re.match(r'[0-9]+_', n) and n.endswith('.snap'))
    if not names: sys.exit('FAIL: no numbered snapshot in %s' % d)
    return os.path.join(d, names[-1])


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]; flags = [a for a in sys.argv[1:] if a.startswith('--')]
    if not pos or len(pos) > 2: sys.exit(__doc__)
    out = os.path.abspath(pos[0]); start = os.path.abspath(pos[1]) if len(pos) > 1 else DEFAULT_START
    upto = ([f.split('=', 1)[1] for f in flags if f.startswith('--upto=')] or ['g2'])[0]
    if upto not in SEGS or any(not f.startswith('--upto=') for f in flags): sys.exit('usage: --upto=<%s>' % '|'.join(SEGS))
    if not os.path.isfile(start): sys.exit('FAIL: start snapshot %s not found' % start)
    py = os.path.join(ROOT, '.venv', 'bin', 'python')
    if not os.path.exists(py): py = sys.executable
    base_env = dict(os.environ, M68000_ROOT=ROOT, ATARI_NOTRACE='1')
    os.makedirs(out, exist_ok=True)
    t0 = time.time(); cur = start; final = None

    def run(seg, script, args):
        sd = os.path.join(out, seg); os.makedirs(sd, exist_ok=True)
        env = dict(base_env, CAD_OUT=os.path.join(sd, '_scratch'))
        log = os.path.join(sd, 'log.txt'); t = time.time()
        with open(log, 'w') as fh:
            rc = subprocess.call([py, script] + args, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
        lines = [l.rstrip() for l in open(log, errors='replace') if l.strip()]
        if rc != 0:
            print('%-4s FAIL rc %d after %ds (log %s)' % (seg, rc, time.time() - t, log), flush=True)
            for l in lines[-6:]: print('   ' + l[:200], flush=True)
            sys.exit(1)
        return sd, lines, time.time() - t

    def report(seg, sd, lines, dt, handoff):
        print('%-4s ok %4ds -> %s\n     %s' % (seg, dt, os.path.relpath(handoff, out), (lines[-1] if lines else '')[:170]), flush=True)

    # heal
    sd, lines, dt = run('heal', os.path.join(ACT, 'route_heal_chain.py'), [os.path.join(out, 'heal'), cur])
    cur = os.path.join(sd, 'ck_71_L_stall_2a.snap')
    if not os.path.isfile(cur): sys.exit('FAIL: heal did not write %s' % cur)
    report('heal', sd, lines, dt, cur)
    if upto == 'heal': return done(final, out, t0)
    # d1
    sd, lines, dt = run('d1', os.path.join(HERE, 'd1', 'route_gems_to_room27.py'), [cur, os.path.join(out, 'd1')])
    cur = last_numbered(os.path.join(sd, 'gems')); report('d1', sd, lines, dt, cur)
    if upto == 'd1': return done(final, out, t0)
    # e1
    sd, lines, dt = run('e1', os.path.join(HERE, 'e1', 'route_room27_to_room22_natural.py'), [cur, os.path.join(out, 'e1')])
    cur = last_numbered(os.path.join(sd, 'route')); report('e1', sd, lines, dt, cur)
    if upto == 'e1': return done(final, out, t0)
    # g1
    sd, lines, dt = run('g1', os.path.join(HERE, 'g1', 'route_room22_to_altar99.py'), [cur, os.path.join(out, 'g1')])
    cur = os.path.join(sd, 'D_end.snap')
    if not os.path.isfile(cur): sys.exit('FAIL: g1 did not write %s' % cur)
    report('g1', sd, lines, dt, cur)
    if upto == 'g1': return done(final, out, t0)
    # g2
    sd, lines, dt = run('g2', os.path.join(HERE, 'g2', 'route_altar_to_room36_real.py'), [cur, os.path.join(out, 'g2')])
    cur = os.path.join(sd, 'end_room60.snap')
    if not os.path.isfile(cur): sys.exit('FAIL: g2 did not write %s' % cur)
    report('g2', sd, lines, dt, cur)
    ends = [l for l in lines if l.startswith('end ')]
    m = ends and re.match(r'end room (\d+) .* health (\d+) xp (\d+)', ends[-1])
    if not m: sys.exit('FAIL: no "end room .. health .. xp .." line in %s/log.txt' % sd)
    final = tuple(int(x) for x in m.groups())
    if final[0] != 60: sys.exit('FAIL: ended in room %d, not 60' % final[0])
    return done(final, out, t0)


def done(final, out, t0):
    if final: print('FINAL room %d health %d xp %d (end_room60.snap)' % final, flush=True)
    print('total %ds, output under %s' % (time.time() - t0, out), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
