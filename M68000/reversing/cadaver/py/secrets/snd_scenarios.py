"""Multi-event sound proof: priority, voice round-robin, queued (bit 7) sounds, StopSound and re-pick.

Start snapshot gameplay_empire.snap.  Each scenario is a list of (frame, op, id): after the `frame`-th PSG flush
($015ea2, end of one VBL's sound tick) the op is applied: 'play' = $0158f8 D0=id, 'stop' = $015aec D0=id,
'stop2' = $015ae0 D0=id.  For every event the live routine is first run with `callcap` (state restored) and its
byte delta in the sound state must equal what cad_sound.Sound does; the Python delta is then poked into the live
run so the following VBLs are driven by the same state.  All PSG writes ($ff8800/$ff8802) of the run are captured
with `watch` and compared with Sound.tick() frame by frame.
Prints per scenario: 'events ok n/n' and 'frames M/N match'.  Expected: all events ok, M == N.

Run from M68000/:  uv run python reversing/cadaver/py/secrets/snd_scenarios.py
"""
import json, os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
OUT = os.path.join(os.path.abspath(os.path.join(here, '..', '..', '..', '..')), 'scratchpad/cadaver/secrets_out'); os.makedirs(OUT, exist_ok=True)
from ram import ram
from cad_sound import Sound, A5
M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..')); REPO = os.path.dirname(M68)
DISK = os.path.join(REPO, 'Cadaver', 'Cadaver (1990)(Image Works)[cr Empire][one disk].st')
SNAP = os.path.join(M68, 'scratchpad/cadaver/gameplay_empire.snap')
base = ram(SNAP)
REG = [(0x158f0, 0x16400), (A5 + 2400, A5 + 2600)]
def inreg(a): return any(lo <= a < hi for lo, hi in REG)
ADDR = {'play': '158f8', 'stop': '15aec', 'stop2': '15ae0'}
SCEN = {
 'S1 queued 11 + sfx 7 + stop 11': (260, [(3, 'play', 11), (40, 'play', 7), (90, 'play', 2), (150, 'stop', 11)]),
 'S2 priority 17 then 28 then 33 then 21': (300, [(3, 'play', 17), (50, 'play', 28), (110, 'play', 33), (160, 'play', 21), (200, 'play', 17)]),
 'S3 round robin + all busy': (200, [(3, 'play', 2), (4, 'play', 3), (5, 'play', 4), (6, 'play', 5), (7, 'play', 59), (60, 'play', 18)]),
 'S4 two-voice sfx over busy voice': (200, [(3, 'play', 18), (5, 'play', 1), (7, 'play', 13), (9, 'play', 6)]),
 'S5 queue two, stop other, stop first': (300, [(3, 'play', 12), (30, 'play', 29), (80, 'stop', 29), (120, 'stop', 12), (150, 'stop', 57), (200, 'play', 57), (230, 'stop2', 57)]),
 'S6 all queued ids': (420, [(3 + 30 * i, 'play', k) for i, k in enumerate([11, 12, 15, 16, 29, 34, 41, 44, 54, 57, 51, 52])]),
}
env = dict(os.environ, ATARI_NOTRACE='1')
def repl(cmds):
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', DISK],
                       input='\n'.join(cmds) + '\nq\n', text=True, capture_output=True, cwd=M68, env=env, timeout=3600)
    return p.stdout, p.stderr
def do_op(s, op, sid):
    if op == 'play': s.play(sid)
    elif op == 'stop': s.stop(sid)
    else: s.stop(sid, flag2488=True)
tot_ok = 0
for name, (nframes, events) in SCEN.items():
    # python side: run ticks, apply events, record poke lists and expected frames
    s = Sound(base); exp = []; cmds = []; evinfo = []
    ev = sorted(events); ei = 0; last_frame = 0
    cmds.append('watch ff8800 4')
    for k in range(1, nframes + 1):
        exp.append(s.tick()); s.housekeeping()
        while ei < len(ev) and ev[ei][0] == k:
            _, op, sid = ev[ei]; ei += 1
            before = bytearray(s.m)
            cmds.append('bpc 15ea2 %d 30000000' % (k - last_frame)); last_frame = k
            tmp = os.path.join(OUT, 'scen_cc_%d.json' % len(evinfo))
            cmds.append('callcap %s 500000 %s D0=%x' % (ADDR[op], tmp, sid))
            do_op(s, op, sid)
            pk = []
            t = set(a & ~3 for lo, hi in REG for a in range(lo, hi) if s.m[a] != before[a])
            pyd = {a: s.m[a] for lo, hi in REG for a in range(lo, hi) if s.m[a] != before[a]}
            for a in sorted(t): pk.append('w %x %s' % (a, s.m[a:a + 4].hex()))
            cmds += pk
            evinfo.append((k, op, sid, tmp, pyd, before))
    cmds.append('bpc 15ea2 %d 30000000' % (nframes + 2 - last_frame))
    out, err = repl(cmds)
    # event check: live callcap delta == python delta (compare against live state at that time = python state before)
    ok = 0
    for k, op, sid, tmp, pyd, before in evinfo:
        d = json.load(open(tmp)); live = {a: n for a, o, n in d['mem'] if inreg(a)}
        if live == pyd: ok += 1
        else: print('   event mismatch frame %d %s %d: live-only %s py-only %s' % (k, op, sid, sorted(set(live) - set(pyd))[:8], sorted(set(pyd) - set(live))[:8]))
    w = [(m.group(1), int(m.group(2), 16)) for m in re.finditer(r'WriteByte \$00ff88(0[02]) <- \$([0-9a-f]+)', err)]
    frames = []; cur = []; reg = None
    for port, val in w:
        if port == '00': reg = val
        else: cur.append((reg, val))
        if len(cur) == 11:
            assert [r for r, v in cur] == list(range(11)); frames.append([v for r, v in cur]); cur = []
    n = min(len(frames), nframes)
    match = sum(frames[i] == exp[i] for i in range(n))
    first_bad = next((i for i in range(n) if frames[i] != exp[i]), None)
    print('%-42s events ok %d/%d   frames %d/%d match%s' % (name, ok, len(evinfo), match, n, '' if first_bad is None else '  first mismatch at frame %d py=%s live=%s' % (first_bad + 1, exp[first_bad], frames[first_bad])), flush=True)
