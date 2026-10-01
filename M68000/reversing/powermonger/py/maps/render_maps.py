"""render_maps.py: the PNGs of the `maps` area, from existing snapshots (no emulator run).

    cd M68000 && .venv/bin/python reversing/powermonger/py/maps/render_maps.py

 worldmap_full.png      the whole 320 x 608 conquest-map bitmap ($3f364, resource 10) with the map palette of pm123/win/m1_map.snap
                        and the 13 x 15 land grid (cells 24 x 40, pick box 16 x 32 at (24c+8, 40r+8)) as thin lines
 minimap_modes.png      the four `_show_ma` ($58098) modes of `$107d6` (maps_ref transcription, pixel exact to the real routine) for
                        pm121/run/k5_s4.snap, with the in-game HUD palette, 4x
 terrain_roads.png      top-down 64 x 128 cell map of pm121/k5.snap / pm121/run/k5_s4.snap: sea / land by the mode-2 colour map,
                        cells whose triangle colour A or B is $1d (roads from `$10910`, town ground from `$10638`) in white, 6x
"""
import os, sys
from pathlib import Path
from PIL import Image
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/maps"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
from gfxview import load_video_regs
import maps_ref as M


def st(w):
    return ((w >> 8 & 7) * 36, (w >> 4 & 7) * 36, (w & 7) * 36)


def planar(buf, base, w, h, pal, stride=160):
    img = Image.new('RGB', (w, h)); px = img.load()
    for y in range(h):
        for x in range(w):
            o = base + y * stride + (x >> 4) * 8 + ((x >> 3) & 1); bit = 0x80 >> (x & 7)
            px[x, y] = pal[sum(((buf[o + 2 * p] & bit) != 0) << p for p in range(4))]
    return img


s = 'scratchpad/pm123/win/m1_map.snap'
ram = bytearray(ram_from_snap(str(ROOT / s)))
pal = [st(w) for w in load_video_regs(str(ROOT / s))['palette_words']]
img = planar(ram, M.MAPBMP, 320, 608, pal)
px = img.load()
for r in range(16):
    for x in range(320):
        if 6 + 40 * r < 608: px[x, 6 + 40 * r] = (255, 255, 255) if x % 2 else px[x, 6 + 40 * r]
for c in range(14):
    for y in range(608):
        if 6 + 24 * c < 320: px[6 + 24 * c, y] = (255, 255, 255) if y % 2 else px[6 + 24 * c, y]
img.save(DATA / 'worldmap_full.png')

s = 'scratchpad/pm121/run/k5_s4.snap'
ram = bytearray(ram_from_snap(str(ROOT / s)))
pal = [st(w) for w in load_video_regs(str(ROOT / s))['palette_words']]
base = int.from_bytes(ram[0xe0d4:0xe0d8], 'big')
strips = []
for mode in range(4):
    r2 = bytearray(ram); M.minimap_107d6(r2, mode)
    strips.append(planar(r2, base, 64, 134, pal).crop((0, 6, 63, 134)).resize((252, 512), Image.NEAREST))
sheet = Image.new('RGB', (4 * 252 + 3 * 8, 512), (40, 40, 40))
for i, t in enumerate(strips): sheet.paste(t, (i * 260, 0))
sheet.save(DATA / 'minimap_modes.png')

cm = bytes(ram[0x108ce:0x108ce + 66])
img = Image.new('RGB', (64, 128)); px = img.load()
n1d = 0
for y in range(128):
    for x in range(64):
        n = y * 64 + x
        a, b = ram[M.CA + n], ram[M.CB + n]
        if a == 0x1d or b == 0x1d:
            px[x, y] = (255, 255, 255); n1d += 1
        else:
            px[x, y] = pal[cm[a]]
img.resize((384, 768), Image.NEAREST).save(DATA / 'terrain_roads.png')
print('wrote worldmap_full.png, minimap_modes.png, terrain_roads.png; $1d cells in k5_s4: %d' % n1d)
