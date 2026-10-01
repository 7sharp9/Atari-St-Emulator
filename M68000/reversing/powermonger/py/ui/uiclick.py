"""Click the real UI from a snapshot: toggle the inspect icon ($2c, screen (75,191), sets $57fea), then click an entity and
count the opener hits.  Controls: click without the inspect toggle; inspect toggle without the entity click.
    python uiclick.py <snap> <x,y> [opener hex ...]
Prints, per run, the `hits` table over the entity click and the text grid of panel slot 0 ($7bac)."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import *
HOME = ['mouse move -400 -400', 's 300000', 'mouse move 0 0', 's 300000']
def click(x, y, px, py, hits=None):
    c = [f'mouse move {x-px} {y-py}', 's 300000', 'mouse move 0 0', 's 300000', 'mouse down l', 'mouse move 0 0']
    c.append(hits if hits else 's 300000')
    return c + ['mouse up l', 'mouse move 0 0', 's 300000']
def run(snap, toggle, target, openers):
    cmds = list(HOME); px = py = 0
    if toggle:
        cmds += click(75, 191, 0, 0); px, py = 75, 191
    h = 'hits 300000 ' + ' '.join(['95f6', '7b10', 'a91a'] + openers)
    if target:
        cmds += click(target[0], target[1], px, py, h)
    cmds += ['m 57fea 2', 'm 7a36 8', 'm 7bac 700']
    out = repl(snap, cmds)
    hits = {m.group(1): int(m.group(2)) for m in re.finditer(r'^\s+\$00([0-9a-f]{4})\s+(\d+)\s+first', out, re.M)}
    dumps = [bytes.fromhex(''.join(l.split())) for l in out.splitlines() if re.fullmatch(r'([0-9a-f]{2} ?)+', l.strip() or 'x')]
    grid = dumps[-1]; text = None
    if dumps[1][:2] != b'\0\0':
        w, h2 = grid[0] * 4, grid[1]
        text = [''.join(chr(c) if 32 <= c < 127 else '.' for c in grid[2 + r * w:2 + (r + 1) * w]) for r in range(h2)]
    return hits, dumps[0].hex(), dumps[1].hex(), text
if __name__ == '__main__':
    snap = sys.argv[1]; tx, ty = map(int, sys.argv[2].split(',')); openers = sys.argv[3:]
    for name, toggle, target in (('inspect icon + entity click', True, (tx, ty)), ('control: entity click, no inspect icon', False, (tx, ty)), ('control: inspect icon only', True, None)):
        hits, f57fea, desc, text = run(snap, toggle, target, openers)
        print(f'== {name}: $57fea={f57fea} desc0={desc} hits={hits}')
        if text: print('\n'.join('   ' + t for t in text))
