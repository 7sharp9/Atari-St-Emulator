"""live_bug2.py <snap> <obj> : feed the Bug2 waypoints (live_prep.py json) one at a time through the poke harness
(live_check.py's method: poke target words 20/22 = one `w`), against an unpoked control. Every poke is a poke.
Usage (from M68000/): uv run python reversing/powermonger/commander/bug2/live_bug2.py <snap> <obj> [--chunk N] [--per K]"""
import json, os, re, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve()
sys.path.insert(0, str(here.parent))
from follow import ROOT, DATA
snap, obj = sys.argv[1], int(sys.argv[2])
opt = lambda n, d: int(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
chunk, per = opt('--chunk', 250000), opt('--per', 3)
J = json.load(open(DATA / ('live_%s_obj%d.json' % (Path(snap).stem, obj))))
rec = 0x51b66 + 50 * obj
WORK = DATA / 'live'
WORK.mkdir(exist_ok=True)
DLL = ROOT / 'bin/Debug/net8.0/M68000.dll'
sw = lambda b, o: int.from_bytes(b[o:o + 2], 'big', signed=True)


def run(tag, wps):
    repl = WORK / (tag + '.repl')
    n = 0
    with open(repl, 'w') as f:
        f.write('disk scratchpad/powermonger.st\nm %x 50\n' % rec)
        windows = wps if wps else [None] * 4
        for wp in windows:
            if wp:
                f.write('w %x %08x\n' % (rec + 20, ((wp[0] & 0xffff) << 16) | (wp[1] & 0xffff)))
            for _ in range(per):
                f.write('s %d\nm %x 50\n' % (chunk, rec)); n += 1
        f.write('q\n')
    env = dict(os.environ, ATARI_NOTRACE='1')
    with open(repl) as fi, open(WORK / (tag + '.out'), 'w') as fo, open(WORK / (tag + '.err'), 'w') as fe:
        subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(ROOT / snap), 'repl'], stdin=fi, stdout=fo, stderr=fe, cwd=ROOT, env=env)
    recs = [bytes.fromhex(l.strip()) for l in open(WORK / (tag + '.out')).read().splitlines() if re.fullmatch(r'([0-9a-f]{2} ){49}[0-9a-f]{2}', l.strip())]
    assert len(recs) == n + 1, (tag, len(recs), n + 1)
    return recs


tgt = J['target']
for arm, wps in (('control', None), ('bug2', [tuple(w) for w in J['wps']])):
    recs = run('%s_obj%d_%s' % (Path(snap).stem, obj, arm), wps)
    pos = [(sw(b, 8), sw(b, 10)) for b in recs]
    print(arm, 'start', pos[0], 'chunks', len(recs) - 1)
    print('  trajectory:', pos)
    print('  modes:', ['%02x' % b[31] for b in recs])
    if wps:
        for k, wp in enumerate(wps):
            win = pos[1 + k * per: 1 + (k + 1) * per]
            d = min(max(abs(p[0] - wp[0]), abs(p[1] - wp[1])) for p in win)
            print('  waypoint %d %s: closest approach in its window %d' % (k, wp, d))
    dt = [max(abs(p[0] - tgt[0]), abs(p[1] - tgt[1])) for p in pos]
    print('  distance to the ORIGINAL target (%d,%d): start %d min %d end %d' % (tgt[0], tgt[1], dt[0], min(dt), dt[-1]))
