"""zoomrow.py <log> <snapdir> <state> <pool> <out.png> <frames,..> <type:var,...> [mode]: rows of zoomed crops around the spawn point, one row per case."""
import sys, re, os
from PIL import Image, ImageDraw
log, snapdir, st, pool, outp, frames, cases = sys.argv[1:8]
mode = sys.argv[8] if len(sys.argv) > 8 else "free"
frames = [int(x) for x in frames.split(",")]
want = [tuple(int(y) for y in x.split(":")) for x in cases.split(",")]
info = {}
for l in open(log):
    m = re.match(r"CASE (\w) (\d+) (\w+) var=(\d+) sx=([0-9a-f]+) p=([0-9a-f]+),([0-9a-f]+) at=([0-9a-f]+),([0-9a-f]+)", l)
    if m: info[(int(m.group(2)), int(m.group(4)), m.group(3))] = (int(m.group(5), 16), int(m.group(8), 16))
CW, CH, Z = 56, 56, 3
rows = []
for (t, v) in want:
    if (t, v, mode) not in info: continue
    sx, x = info[(t, v, mode)]
    row = Image.new("RGB", (CW * Z * len(frames), CH * Z + 12), (25, 25, 25))
    ImageDraw.Draw(row).text((2, 0), "%s%d.%d" % (pool, t, v), fill=(255, 255, 0))
    for k, n in enumerate(frames):
        f = os.path.join(snapdir, "fs_%s_%s%d_v%d_%s_%d.png" % (st, pool, t, v, mode, n))
        if not os.path.exists(f): continue
        im = Image.open(f).convert("RGB")
        xs = x - sx; x0 = max(0, min(256 - CW, xs - CW // 2)); y0 = 240 - CH - 12
        row.paste(im.crop((x0, y0, x0 + CW, y0 + CH)).resize((CW * Z, CH * Z), Image.NEAREST), (k * CW * Z, 12))
    rows.append(row)
H = sum(r.size[1] for r in rows)
sheet = Image.new("RGB", (rows[0].size[0], H))
y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.size[1]
sheet.save(outp)
