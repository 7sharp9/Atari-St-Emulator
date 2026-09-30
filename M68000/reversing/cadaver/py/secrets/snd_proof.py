"""Sound-engine proof: cad_sound.py vs the live game.  Start snapshot: scratchpad/cadaver/gameplay_empire.snap.

For each sound id given (default 0..61) it
 (1) runs `callcap 158f8 D0=<id>` in the live emulator and checks that the bytes it changes in the sound state
     ($0158f0-$016400 and the 2400..2600(A5) flag block) are exactly the bytes Sound.play(id) changes   [install check]
 (2) pokes that live delta into a fresh run, `watch ff8800 4` and steps ~N VBLs, collecting the real PSG register
     writes, and compares them frame by frame with Sound.tick() (11 register values per VBL)            [tick check]
Prints per sound: 'id  install: ok|DIFF  frames N: M match'.  Expected: install ok and M == N for every sound.

Run from M68000/:  uv run python reversing/cadaver/py/secrets/snd_proof.py [frames=200] [id ...]
ATARI_NOTRACE=1 and the existing DLL are used (no build).
"""
import json, os, re, subprocess, sys, tempfile
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
OUT = os.path.join(os.path.abspath(os.path.join(here, '..', '..', '..', '..')), 'scratchpad/cadaver/secrets_out'); os.makedirs(OUT, exist_ok=True)
from ram import ram
from cad_sound import Sound, A5
M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..')); REPO = os.path.dirname(M68)
DISK = os.path.join(REPO, 'Cadaver', 'Cadaver (1990)(Image Works)[cr Empire][one disk].st')
SNAP = os.path.join(M68, 'scratchpad/cadaver/gameplay_empire.snap')
base = ram(SNAP)
frames = int(sys.argv[1]) if len(sys.argv) > 1 else 200
ids = [int(x) for x in sys.argv[2:]] or list(range(62))
env = dict(os.environ, ATARI_NOTRACE='1')
def repl(cmds, timeout=3600):
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', DISK],
                       input='\n'.join(cmds) + '\nq\n', text=True, capture_output=True, cwd=M68, env=env, timeout=timeout)
    return p.stdout, p.stderr
REG = [(0x158f0, 0x16400), (A5 + 2400, A5 + 2600)]
def inreg(a): return any(lo <= a < hi for lo, hi in REG)
def pokes_from(delta):
    img = bytearray(base); t = set()
    for a, o, n in delta['mem']:
        if inreg(a): img[a] = n; t.add(a & ~3)
    return ['w %x %s' % (a, img[a:a + 4].hex()) for a in sorted(t)]
def run_one(sid):
    tmp = os.path.join(OUT, 'snd_cc_%d.json' % sid)
    out, err = repl(['callcap 158f8 500000 %s D0=%x' % (tmp, sid)])
    d = json.load(open(tmp))
    live = {a: n for a, o, n in d['mem'] if inreg(a)}
    s = Sound(base); s.play(sid)
    py = {a: s.m[a] for a in range(len(base)) if inreg(a) and s.m[a] != base[a]} if False else {}
    for lo, hi in REG:
        for a in range(lo, hi):
            if s.m[a] != base[a]: py[a] = s.m[a]
    inst = 'ok' if py == live else 'DIFF(live-only %s, py-only %s)' % (sorted(set(live) - set(py))[:6], sorted(set(py) - set(live))[:6])
    # tick check
    cmds = pokes_from(d) + ['watch ff8800 4', 's %d' % ((frames + 3) * 16000)]
    out, err = repl(cmds)
    w = [(m.group(1), int(m.group(2), 16)) for m in re.finditer(r'WriteByte \$00ff88(0[02]) <- \$([0-9a-f]+)', err)]
    live_frames = []; cur = []
    it = iter(w)
    for port, val in it:
        if port == '00': reg = val
        else: cur.append((reg, val))
        if len(cur) == 11: live_frames.append([v for r, v in cur]); assert [r for r, v in cur] == list(range(11)); cur = []
    exp = Sound(base); exp.play(sid)
    match = 0; first_bad = None
    for i in range(min(frames, len(live_frames))):
        e = exp.tick()
        if e == live_frames[i]: match += 1
        elif first_bad is None: first_bad = (i, e, live_frames[i])
    print('%2d  install: %s  frames %d: %d match%s' % (sid, inst, min(frames, len(live_frames)), match, '' if first_bad is None else '  first mismatch %s' % (first_bad,)), flush=True)
    return match == min(frames, len(live_frames)) and inst == 'ok'
ok = sum(run_one(i) for i in ids)
print('sounds fully matching: %d / %d' % (ok, len(ids)))
