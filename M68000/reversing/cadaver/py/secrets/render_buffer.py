"""render_buffer.py <snap> <hex addr> <out.png>: render a 320x200x4bpp ST-low planar buffer at any address with the snapshot's live
palette.  Cadaver draws windows/text into the back buffer (A5)/(A5)+188 and only presents them through $011338, so a snapshot taken
while a routine waits inside its own key loop (the stats scroll $00a29c, the pause $011834) shows the old frame in snap_render.py.
    uv run python reversing/cadaver/py/secrets/render_buffer.py foo.snap 19100 foo.png"""
import sys
sys.path.insert(0, 'tools')
from gfxview import load_ram, load_video_regs
from PIL import Image
snap, addr, out = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]
ram, _ = load_ram(snap); regs = load_video_regs(snap)
pal = [((w >> 8 & 7) * 36, (w >> 4 & 7) * 36, (w & 7) * 36) for w in regs['palette_words']]
img = Image.new('RGB', (320, 200)); px = img.load()
for y in range(200):
    for xb in range(20):
        o = addr + y * 160 + xb * 8
        p = [int.from_bytes(ram[o + 2 * i:o + 2 * i + 2], 'big') for i in range(4)]
        for b in range(16):
            v = sum(((p[i] >> (15 - b)) & 1) << i for i in range(4))
            px[xb * 16 + b, y] = pal[v]
img.save(out)
