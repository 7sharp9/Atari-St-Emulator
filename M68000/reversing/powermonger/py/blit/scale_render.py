"""Render the `scale_da` (`$16bf8`, 5 frames x 640 bytes = 20 rows x 32 bytes, 4-plane interleaved, 64 px wide) tilt pictures
the way `_draw_sc` ($16bb8) copies them (frame = 4 - D0, D0 = ratio word $57fce 0..4). Writes scale_da.png.   cd M68000 && .venv/bin/python <this file>"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[3] / "tools"))
from ramlib import ram, ROOT
DATA = ROOT / "scratchpad/pm140/agents/blit"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
from gfxview import load_video_regs
from PIL import Image
snap = "scratchpad/pm123/win/m1_s0.snap"
r = ram(snap)
pal = [((w >> 8 & 7) * 36, (w >> 4 & 7) * 36, (w & 7) * 36) for w in load_video_regs(ROOT / snap)["palette_words"]]
S = 4
im = Image.new("RGB", (5 * (64 * S + 8), 20 * S + 8), (30, 30, 30))
for f in range(5):                      # frame f is shown when D0 = 4 - f
    base = 0x16bf8 + f * 640
    for y in range(20):
        for g in range(4):
            a = base + y * 32 + g * 8
            pl = [int.from_bytes(r[a + 2 * p:a + 2 * p + 2], "big") for p in range(4)]
            for b in range(16):
                i = sum(((pl[p] >> (15 - b)) & 1) << p for p in range(4))
                for dy in range(S):
                    for dx in range(S):
                        im.putpixel((4 + f * (64 * S + 8) + (g * 16 + b) * S + dx, 4 + y * S + dy), pal[i])
im.save(DATA / "scale_da.png")
print(DATA / "scale_da.png")
