"""render.py - terrain + A* path + follower path PNG. Used by report.py."""
from PIL import Image, ImageDraw
def render(tr, start, target, astar_pts, fpts, fname, title='', margin=3):
    allp = [start, target] + list(astar_pts) + list(fpts)
    xs = [p[0] for p in allp]; ys = [p[1] for p in allp]
    cx0 = max(0, min(xs) // 256 - margin); cx1 = min(63, max(xs) // 256 + margin)
    cy0 = max(0, min(ys) // 256 - margin); cy1 = min(127, max(ys) // 256 + margin)
    sc = max(2, min(8, 900 // max(1, (cx1 - cx0 + 1))))   # pixels per cell
    ppu = sc / 256.0
    wpx, hpx = (cx1 - cx0 + 1) * sc, (cy1 - cy0 + 1) * sc
    img = Image.new('RGB', (wpx, hpx))
    px = img.load()
    for yy in range(hpx):
        for xx in range(wpx):
            wx = int((xx + .5) / ppu) + cx0 * 256; wy = int((yy + .5) / ppu) + cy0 * 256
            px[xx, yy] = (96, 150, 80) if tr.free(wx, wy) else (40, 70, 140)
    d = ImageDraw.Draw(img)
    T = lambda p: ((p[0] - cx0 * 256) * ppu, (p[1] - cy0 * 256) * ppu)
    if len(astar_pts) > 1:
        d.line([T(p) for p in astar_pts], fill=(255, 215, 0), width=2)
    if len(fpts) > 1:
        d.line([T(p) for p in fpts], fill=(230, 40, 40), width=1)
    a = T(start); b = T(target)
    d.ellipse([a[0]-4, a[1]-4, a[0]+4, a[1]+4], fill=(255, 255, 255), outline=(0, 0, 0))
    d.rectangle([b[0]-4, b[1]-4, b[0]+4, b[1]+4], fill=(255, 0, 255), outline=(0, 0, 0))
    d.text((4, 4), title, fill=(255, 255, 255))
    img.save(fname)
