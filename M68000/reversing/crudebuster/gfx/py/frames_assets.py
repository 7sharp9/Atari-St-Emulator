"""Side-by-side recomposed frames: MAME snapshot | pure-Python renderer | pixel difference (black = identical), and a layer breakdown of one frame.
Writes assets/frames/*.png.  usage: frames_assets.py"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R, compare as C

ROOT = R.ROOT if hasattr(R, "ROOT") else os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PICKS = [("att", 111, "attract_logo"), ("att", 370, "split_frame"), ("att", 1110, "attract_a"), ("a1", 1500, "level0_play"), ("lv1", 2400, "level1_pri1"),
         ("lv2", 2400, "level2_pri1"), ("lv3", 2400, "level3_pri1"), ("lv4", 2400, "level4_pri0"), ("lv5", 2400, "level5_pri1"), ("a1", 720, "stage_fade")]

def main():
    for name, f, tag in PICKS:
        d = os.path.join(ROOT, "dumps", name)
        b = os.path.join(d, "f%05d.bin" % f)
        if not os.path.exists(b):
            # nearest dumped frame
            import glob, re
            fr = sorted(int(re.search(r"f(\d+)", x).group(1)) for x in glob.glob(os.path.join(d, "f*.bin")))
            f = min(fr, key=lambda x: abs(x - f)); b = os.path.join(d, "f%05d.bin" % f)
        png = os.path.join(ROOT, "run", name, "snap", "f%05d.png" % f)
        out = os.path.join(ROOT, "assets", "frames", "%s_%s_f%d.png" % (name, tag, f))
        fr, same, n, st = C.compare(b, png, None, out)
        print(out.split("assets/")[1], "%d/%d identical pri=%d" % (same, n, st.pri))

if __name__ == "__main__":
    main()


def layers(name="lv3", f=2400):
    """each layer alone (pen 0 transparent, shown on grey): chip1 pf2, chip1 pf1, chip0 pf2, chip0 pf1, sprites behind (y15 set), sprites front."""
    st = R.State.load(os.path.join(ROOT, "dumps", name, "f%05d.bin" % f), f)
    pal = R.palette_rgb(st.palraw)
    panels = []
    for chip, pf in ((1, 1), (1, 0), (0, 1), (0, 0)):
        pens, opq, small = R.tilemap_bitmap(st, chip, pf)
        r = R.pf_scroll_map(st, chip, pf, pens, opq, small)
        img = np.full((R.H, R.W, 3), 70, np.uint8)
        if r is not None:
            p, o = r; img[o] = pal[p[o]]
        panels.append(img)
    sb = R.sprite_bitmap_fast(st, st.fodd)[R.VIS_Y0:R.VIS_Y1 + 1]
    for pv in (0x800, 0x000):
        img = np.full((R.H, R.W, 3), 70, np.uint8)
        for v, base in ((pv, 0x100), (pv | 0x100, 0x500)):
            m = ((sb & 0xf) != 0) & ((sb & 0x900) == v)
            img[m] = pal[(sb[m] & 0xff) + base]
        panels.append(img)
    sheet = np.concatenate([np.concatenate(panels[:3], axis=1), np.concatenate(panels[3:], axis=1)], axis=0)
    Image.fromarray(sheet).save(os.path.join(ROOT, "assets", "frames", "layers_%s_f%d.png" % (name, f)))


if __name__ == "__main__":
    layers()
