"""minimap_stale.py <snap-or-ram>...: is the minimap in the master buffer a fresh bake of the current state?

For each snapshot: re-bake `$107d6` in its current mode ($58098) from the same RAM with maps_ref.minimap_107d6 and count
the minimap pixels (63 x 128, at (x, y + 6) of [$e0d4]) that differ from the stored image ('stale'); then the same for a
mode-3 bake, whose colours follow each lord's food less manpower, against a mode-3 bake of the first snapshot given
('m3 drift': how far a mode-3 picture baked then would be from one baked now), and the stored image against the first
snapshot's stored image ('kept': 0 when nothing re-baked in between and the mode is unchanged). The bake runs only at the land build,
the map-strip click, `click_pr` and `_draw_ca` ($187d8: a captain added to or removed from the player's side,
`$273a`/`$28c4`), graphics.md "The minimap and the conquest map".
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
import maps_ref as M

def load(p):
    return bytearray(ram_from_snap(p) if p.endswith('.snap') else open(p, 'rb').read())

def pixels(r):
    base = int.from_bytes(r[0xe0d4:0xe0d8], 'big')
    out = []
    for y in range(6, 134):
        for x in range(63):
            a = base + y * 160 + (x >> 4) * 8 + ((x & 15) >> 3)
            bit = 7 - (x & 7)
            out.append(sum(((r[a + 2 * pl] >> bit) & 1) << pl for pl in range(4)))
    return out

def bake(r, mode):
    q = bytearray(r); M.minimap_107d6(q, mode); return pixels(q)

first3 = first_stored = None
for p in sys.argv[1:]:
    r = load(p)
    mode = int.from_bytes(r[0x58098:0x5809a], 'big')
    stored = pixels(r)
    fresh = bake(r, mode)
    m3 = bake(r, 3)
    if first3 is None: first3, first_stored = m3, stored
    stale = sum(a != b for a, b in zip(stored, fresh))
    drift = sum(a != b for a, b in zip(first3, m3))
    kept = sum(a != b for a, b in zip(first_stored, stored))
    print(f'{Path(p).name:28s} mode {mode}  stale {stale:5d}/8064  m3 drift {drift:5d}/8064  kept {kept:5d}')
