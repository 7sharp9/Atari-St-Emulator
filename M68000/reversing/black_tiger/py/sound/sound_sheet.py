"""Render sound_sheet.png: (top) the measured output level of the volume table by raw sample byte,
(below) the waveform of every sound id as the Timer A handler plays it (min/max envelope per
pixel column), labelled with id, ticks and duration.  Output $BT_WORK/agents/sound/sound_sheet.png
(the committed copy lives in reversing/black_tiger/img/sound/)."""
import os

from PIL import Image, ImageDraw

from btsnd import OUT, centre, level_source, load_tables, music_as_played, stream, ym_level

vt, rates = load_tables()
W, H0, HW = 720, 150, 54
items = [("id %d" % i, stream(i)[0], rates[1 if i == 0 else 0][2]) for i in range(9)]
items.append(("id 0 as played (t0 over BT4 tail)", music_as_played(), rates[1][2]))
img = Image.new("RGB", (W, H0 + HW * len(items) + 10), (250, 250, 250))
d = ImageDraw.Draw(img)
lv = [ym_level(*vt[(b + 0x80) & 0xff]) for b in range(256)]
mx = max(lv)
d.text((6, 4), "volume table: output level (%s) by raw sample byte 0..255" % level_source(), fill=(0, 0, 0))
x0, y0, x1, y1 = 40, 20, W - 10, H0 - 14
d.rectangle([x0, y0, x1, y1], outline=(160, 160, 160))
pts = [(x0 + (x1 - x0) * b / 255.0, y1 - (y1 - y0) * lv[b] / mx) for b in range(256)]
d.line(pts, fill=(30, 80, 200))
d.text((6, y1 + 2), "0", fill=(0, 0, 0)); d.text((x1 - 20, y1 + 2), "255", fill=(0, 0, 0))
for k, (name, data, hz) in enumerate(items):
    top = H0 + k * HW
    lev = centre([ym_level(*vt[(b + 0x80) & 0xff]) for b in data])
    n = len(lev)
    d.text((6, top + 1), "%s: %d ticks, %.2f s at %.1f Hz" % (name, n, n / hz, hz), fill=(0, 0, 0))
    mid = top + 14 + (HW - 18) // 2
    d.line([(x0 - 30, mid), (x1, mid)], fill=(220, 220, 220))
    for px in range(W - 20):
        a, b = px * n // (W - 20), max(px * n // (W - 20) + 1, (px + 1) * n // (W - 20))
        seg = lev[a:b] or [0]
        lo, hi = min(seg), max(seg)
        d.line([(10 + px, mid - hi * (HW - 18) / 2 / 12000.0), (10 + px, mid - lo * (HW - 18) / 2 / 12000.0)], fill=(20, 20, 20))
out = os.path.join(OUT, "sound_sheet.png")
img.save(out)
print(out, img.size)
