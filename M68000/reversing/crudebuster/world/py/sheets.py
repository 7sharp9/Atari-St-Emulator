"""sheets.py <force log> <snapdir> <outprefix> [types...]: contact sheets of forced-spawn screenshots (free@4,free@50,on@4,on@50)."""
import sys, os, re
from PIL import Image, ImageDraw
log, snapdir, outp = sys.argv[1:4]
want = set(int(x) for x in sys.argv[4:]) if len(sys.argv) > 4 else None
cases = []
for l in open(log):
    m = re.match(r"CASE (\w) (\d+) (\w+) var=(\d+) sx=([0-9a-f]+) p=([0-9a-f]+),([0-9a-f]+) at=([0-9a-f]+),([0-9a-f]+)", l)
    if m: cases.append((m.group(1), int(m.group(2)), m.group(3), int(m.group(5), 16), int(m.group(8), 16), int(m.group(9), 16), int(m.group(4))))
state = re.search(r"force_(\w+?)_([BC])\.txt", log)
st, pool = (state.group(1), state.group(2)) if state else (os.environ["ST"], cases[0][0])
CW, CH = 96, 120
types = sorted(set((c[1], c[6]) for c in cases if want is None or c[1] in want))
byt = {}
for c in cases: byt.setdefault((c[1], c[6]), {})[c[2]] = c
rows = []
for t in types:
    row = Image.new("RGB", (CW * 4, CH + 10), (20, 20, 20))
    d = ImageDraw.Draw(row); d.text((2, 0), "%s%d.%d" % (pool, t[0], t[1]), fill=(255, 255, 0))
    k = 0
    for md in ("free", "on"):
        c = byt[t].get(md)
        for n in (4, 50):
            f = os.path.join(snapdir, "fs_%s_%s%d_v%d_%s_%d.png" % (st, pool, t[0], t[1], md, n))
            if c and os.path.exists(f):
                im = Image.open(f).convert("RGB")
                xs = c[4] - c[3]
                x0 = max(0, min(256 - CW, xs - CW // 2)); y0 = 120
                row.paste(im.crop((x0, y0, x0 + CW, y0 + CH)), (k * CW, 10))
            k += 1
    rows.append(row)
per, cols = 18, 3
for s in range(0, len(rows), per):
    chunk = rows[s:s + per]
    nrow = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * CW * 4 + (cols - 1) * 6, nrow * (CH + 10)), (60, 60, 60))
    for i, r in enumerate(chunk):
        sheet.paste(r, ((i % cols) * (CW * 4 + 6), (i // cols) * (CH + 10)))
    sheet.save("%s_%d.png" % (outp, s // per))
print(len(rows), "types")
