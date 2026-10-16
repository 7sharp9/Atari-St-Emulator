"""gate_cellpt.py: an order's target cell (slot bytes 2/3) -> the lead's target words (object +20/+22) for supply $1a
(`$390e`) and attack $0c on a lord (`$4a7a` -> `$4b80`): the cell centre (x*256+128, y*256+128), 16/16 (README "Action
interface"). From pm142/rand1.snap, side 3 group 0: take, select, order, `hits` of the writers, snap, read the lead.
Run from anywhere. Work dir $CMD_WORK/cellpt (default scratchpad/cmd1)."""
import struct, subprocess, sys, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT = next(d for d in Path(__file__).resolve().parents if (d / 'tools' / 'rdis.py').exists())
HERE = ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'cellpt'; HERE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'reversing/powermonger/commander')); sys.path.insert(0, str(ROOT / 'tools'))
from act import Poker
from observe import load
SNAP = ROOT / 'scratchpad/pm142/rand1.snap'
R0 = load(SNAP)
H = lambda R, a: struct.unpack_from('>H', R, a)[0]
OBJ = 0x51b66
def lead_of(R, side, k): return H(R, 0x51538 + 0x13c * side + 64 + 2 * k)
LEAD = lead_of(R0, 3, 0)

def run(name, typ, x, y, steps=300000):
    p = Poker(R0); p.take(3); p.order(3, typ, x, y, k=0)
    out = HERE / f'{name}.snap'
    lines = ['disk scratchpad/powermonger.st'] + p.lines + [f'hits {steps} 6c32 6d00 390e 4a7a 4b80', f'snap {out}', 'q']
    (HERE / f'{name}.repl').write_text('\n'.join(lines) + '\n')
    with open(HERE / f'{name}.repl') as i, open(HERE / f'{name}.out', 'w') as o, open(HERE / f'{name}.err', 'w') as e:
        subprocess.run(['dotnet', 'exec', str(ROOT / 'bin/Debug/net8.0/M68000.dll'), 'resume', str(SNAP), 'repl'],
                       stdin=i, stdout=o, stderr=e, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'), check=True)
    R = load(out); o = OBJ + LEAD
    tx, ty = H(R, o + 20), H(R, o + 22)
    return dict(name=name, typ=typ, cell=(x, y), tx=tx, ty=ty, w36=H(R, o + 36), mode=(R[o + 30], R[o + 31]),
                gstate=H(R, 0x51538 + 0x13c * 3 + 0x4c), out=(HERE / f'{name}.out').read_text())

if __name__ == '__main__':
    arms = []
    for i, (x, y) in enumerate([(0, 0), (1, 1), (17, 40), (32, 64), (63, 127), (47, 99), (5, 100), (16, 3)]):
        arms.append((f's{i}', 0x1a, x, y))
    for i, (x, y) in enumerate([(15, 92), (31, 119), (52, 102), (46, 108), (39, 61), (37, 13), (54, 55), (40, 115)]):
        arms.append((f'a{i}', 0x0c, x, y))
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda a: run(*a), arms))
    ok = 0
    for r in res:
        x, y = r['cell']; ex_, ey = x * 256 + 128, y * 256 + 128
        m = (r['tx'], r['ty']) == (ex_, ey)
        ok += m
        print(f"{r['name']} type {r['typ']:02x} cell ({x},{y}) -> target ({r['tx']},{r['ty']}) expect ({ex_},{ey}) {'MATCH' if m else 'NO'} "
              f"w36={r['w36']} (y*64+x={y*64+x}) mode={r['mode']} gstate={r['gstate']}")
    print(f'{ok}/{len(res)} match cell*256+128')
