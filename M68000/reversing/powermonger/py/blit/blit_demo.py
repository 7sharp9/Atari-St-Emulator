"""Before/after montage of the six clip routines, from the gate's callcap deltas (run blit_gate.py first). One row per variant:
the back buffer (A0 = long at $2df7c of m1_s0) around the sprite before the call, and after it (callcap `mem` delta applied).
Writes scratchpad/pm140/agents/blit/blit_variants.png (committed copy: ../../blit_variants.png).   cd M68000 && .venv/bin/python reversing/powermonger/py/blit/blit_demo.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import blit_gate as G
from gfxview import load_video_regs
from PIL import Image, ImageDraw

pal = [((w >> 8 & 7) * 36, (w >> 4 & 7) * 36, (w & 7) * 36) for w in load_video_regs(G.ROOT / G.SNAP)["palette_words"]]


def crop(mem, x0, y0, x1, y1):
    im = Image.new("RGB", (x1 - x0, y1 - y0))
    px = im.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            a = G.A0 + y * 160 + (x >> 4) * 8
            i = 0
            for p in range(4):
                i |= (((mem[a + 2 * p] << 8 | mem[a + 2 * p + 1]) >> (15 - (x & 15))) & 1) << p
            px[x - x0, y - y0] = pal[i]
    return im


want = ["_left_16", "_all_16", "_right_1", "_left_32", "_all_32", "_right_3"]
picked = {}
for name, entry, a1, x, y, rows, wide in G.cases():
    v = G.variant(x, y, rows, wide)
    if v in want and v not in picked and 0 <= y and y + rows <= 200 and name.startswith(("s16", "s24")):
        if (v == "_left_16" and wide) or (v == "_right_1" and wide):
            continue
        picked[v] = (name, x, y, rows)
S = 4
sheet = Image.new("RGB", (2 * 80 * S + 30, len(want) * (40 * S + 18)), (30, 30, 30))
d = ImageDraw.Draw(sheet)
for r, v in enumerate(want):
    name, x, y, rows = picked[v]
    j = json.load(open(G.OUT / f"o_{name}.json"))
    after = bytearray(G.ram)
    for a, b0, b1 in j["mem"]:
        after[a] = b1
    cx = max(0, min(240, x - 24)); cy = max(0, min(160, y - 8))
    for c, mem in enumerate((G.ram, after)):
        sheet.paste(crop(mem, cx, cy, cx + 80, cy + 40).resize((80 * S, 40 * S), Image.NEAREST),
                    (10 + c * (80 * S + 10), r * (40 * S + 18) + 16))
    d.text((10, r * (40 * S + 18) + 2), f"{v}  {name}  x={x} y={y} rows={rows}  before / after", fill=(255, 255, 255))
out = G.ROOT / "scratchpad/pm140/agents/blit" / "blit_variants.png"
sheet.save(out)
print(out, picked)
