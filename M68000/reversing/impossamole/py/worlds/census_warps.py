"""Poke-warp into every destination room of a world's exit table and snapshot it (staging census).

    ATARI_NOTRACE=1 uv run python <this> <gameplay.snap> <name> [--jobs 6] [--steps 1500000]

For every record (dir, trigger block, dest start, dest end, dest hero block-x) of the world's exit list
($e0aa, via level_map.transitions) it resumes <gameplay.snap>, pokes health (labelled), the camera
$227b4/$227b6, the hero x/y ($1a574/$1a576) and state $227f3 so that the exit checker $df4a fires on that
record (README "The level is one tile map of connected rooms": trigger block = (x - $20 + camera + 16) >> 5,
dir 0 = top exit needs state 2 and y <= $fff0, dir 1 = bottom exit needs state 3 and y >= $c8), runs `steps`
steps for the fade, and snapshots to agents/world12/census/<name>_<dir>_<trigger>.snap. All of this is POKED
staging, not played. It also writes the predicted-vs-live room fields ($227b4, camera, limit, hero x) per record
to census/<name>_warps.txt (the same five-field check the 99th pass did by hand).
"""
import argparse, os, struct, subprocess, sys, time
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'reversing/impossamole/py')); sys.path.insert(0, str(ROOT / 'tools'))
from level_map import transitions      # noqa: E402
from pm_export import ram_from_snap    # noqa: E402

DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap'); ap.add_argument('name')
    ap.add_argument('--jobs', type=int, default=6); ap.add_argument('--steps', type=int, default=1500000)
    a = ap.parse_args()
    ram = ram_from_snap(Path(a.snap))
    world, start, recs = transitions(ram)
    limit0 = struct.unpack_from('>H', ram, 0x227b8)[0]
    rel = 'scratchpad/impossamole/agents/world12/census'
    (ROOT / rel).mkdir(parents=True, exist_ok=True)
    hp = f'1212{world:02x}00'
    jobs = []
    for dr, trig, sb, eb, hx in recs:
        cam = trig * 32 + 16 - 0x50
        y, state = (0xffe8, 2) if dr == 0 else (0xd4, 3)
        tag = f'{a.name}_{"up" if dr == 0 else "dn"}_{trig}'
        rp = ROOT / rel / f'{tag}.repl'
        rp.write_text('\n'.join([f'w bb74 {hp}', f'w 227b6 {cam:04x}{limit0:04x}', f'w 1a574 0050{y:04x}',
                                 f'w 227f0 {state:08x}', f's {a.steps}', 'm 227b4 2', 'm 227b6 4', 'm 1a574 2',
                                 f'snap {rel}/{tag}.snap', 'q']) + '\n')
        jobs.append((tag, rp, (dr, trig, sb, eb, hx)))
    env = dict(os.environ, ATARI_NOTRACE='1')
    running, done, res = [], 0, {}
    pending = list(jobs)
    while pending or running:
        while pending and len(running) < a.jobs:
            tag, rp, rec = pending.pop(0)
            p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', a.snap, 'repl', '--disk-a', DISK], cwd=ROOT, env=env,
                                 stdin=open(rp), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            running.append((tag, p, rec))
        time.sleep(1)
        for t in list(running):
            if t[1].poll() is not None:
                res[t[0]] = (t[2], t[1].stdout.read()); running.remove(t)
    lines = []
    for tag, _, rec in jobs:
        dr, trig, sb, eb, hx = rec
        out = [l for l in res[tag][1].splitlines() if l and not l.startswith(('---', 'Snapshot', 'enqueued'))]
        # m 227b4 2 -> block; m 227b6 4 -> camera, limit; m 1a574 2 -> hero x
        try:
            blk = int(out[0].replace(' ', ''), 16); cam, lim = (int(out[1].replace(' ', '')[i:i + 4], 16) for i in (0, 4))
            hxx = int(out[2].replace(' ', ''), 16)
        except Exception:
            lines.append(f'{tag}: unparsed {out}'); continue
        exp = (sb, sb * 32, eb * 32 - 256, (hx << 5) + 0x20)
        got = (blk, cam, lim, hxx)
        lines.append(f'{tag}: record ({dr},{trig},{sb},{eb},{hx}) predicted block/camera/limit/heroX {exp} live {got} '
                     f'{"MATCH" if exp == got else "differs"}')
    (ROOT / rel / f'{a.name}_warps.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
