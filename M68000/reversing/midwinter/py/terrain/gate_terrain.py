"""Gate for the terrain model (terrain.md): fresh emulator runs from d_decisions.snap, then terrain_gen.py.

usage: gate_terrain.py
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_decisions.snap and zuul067.st (indexed in
scratchpad/ANCHORS.md). Writes its snapshots to $MIDWINTER_WORK/terrain/gate/. Expected: 70000/70000 generator cells over
seven targets (the natural ski entry and six poked ones) and 10000/10000 post-pass cells.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
OUT = os.path.join(WORK, 'terrain', 'gate')
DLL = os.path.join(root, 'bin', 'Debug', 'net8.0', 'M68000.dll')
DISK = os.path.join(WORK, 'zuul067.st')
TARGETS = [(800, 800), (400, 1200), (1200, 300), (100, 100), (1500, 1500), (1000, 600)]


def repl(snap, lines):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(lines + ['q']) + '\n', capture_output=True, text=True, env=env, cwd=root)
    if p.returncode or 'state saved' not in p.stdout:
        sys.exit(f'emulator run from {snap} failed:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}')


def main():
    os.makedirs(OUT, exist_ok=True)
    o = lambda n: os.path.join(OUT, n + '.snap')
    # the ski click of drive.txt; $19962 is the generator, $1991a the first post-pass, $149ac after $197ec
    repl(os.path.join(WORK, 'd_decisions.snap'),
         ['mouse move -31 -2', 's 600000', 'mouse down l', 's 600000', 'mouse up l',
          'u 19962 50000000', f'snap {o("gen_in")}', 'u 19960 50000000', f'snap {o("gen_out")}',
          'u 1991a 80000000', f'snap {o("post_in")}', 'u 149ac 80000000', f'snap {o("post_out")}'])
    args = [f'368,1176={o("gen_out")}']
    for x, y in TARGETS:
        name = f't_{x}_{y}'
        repl(o('gen_in'), [f'w 19cd4 {x:04x}{y:04x}', 'u 19960 5000000', f'snap {o(name)}'])
        args.append(f'{x},{y}={o(name)}')
    model = os.path.join(HERE, 'terrain_gen.py')
    r1 = subprocess.run([sys.executable, model, 'targets', o('gen_in')] + args, capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, model, 'post', o('post_in'), o('post_out')], capture_output=True, text=True)
    print(r1.stdout + r2.stdout, end='')
    counts = [tuple(map(int, c)) for c in re.findall(r'grid cells (\d+)/(\d+)', r1.stdout)]
    print(f'generator: {sum(c[0] for c in counts)}/{sum(c[1] for c in counts)} cells over {len(counts)} targets')
    return r1.returncode or r2.returncode


if __name__ == '__main__':
    sys.exit(main())
