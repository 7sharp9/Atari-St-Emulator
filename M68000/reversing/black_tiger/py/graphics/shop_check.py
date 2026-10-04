"""shop_check.py - the shop screen ($ea7c -> $f690) against BTCLIPS 17 and the item icons.
LABELLED POKE: hero record moved onto the shop man cell (kind $11, level 0 at (1256,224)) in play_start.snap,
 bp $f690 (shop routine entry), 300,000 steps.  fn8's D2 is the x position in 8 px units."""
import numpy as np
from pics import *
from drive import run_repl, SNAPDIR

def make():
    d = os.path.join(OUT, "shop")
    os.makedirs(d, exist_ok=True)
    run_repl("play_start.snap", ["w 1f014 04e800e0", "bp f690 3000000", "s 300000", "snap %s/shop_a.snap" % d])

def main():
    n = "agents/graphics/shop/shop_a.snap"
    if not os.path.exists(snap_path(n)):
        make()
    ram = load_snap(n); regs = load_video_regs(snap_path(n))
    print("palette = RAM $172d6:", regs["palette_words"] == [w16(ram, 0x172d6 + 2 * i) for i in range(16)])
    scr = np.array(screen_indices(ram, regs["base"]), dtype=np.uint8)
    d, offs, ents = collection("BTCLIPS")
    pic = np.array(ents[17], dtype=np.uint8)
    sub = scr[0:112, 32:288]
    eq = sub == pic
    box = np.zeros_like(eq); box[8:50, :] = True   # speech box (rows 8..49) is drawn over the scene
    print("scene 256x112 at (32,0): equal %d/%d ; outside rows 8..49 (speech box): %d/%d" % (eq.sum(), eq.size, (eq & ~box).sum(), (~box).sum()))
    xs = [w16(ram, 0x17ab2 + 2 * i) * 8 for i in range(10)]; ys = [w16(ram, 0x17ac8 + 2 * i) for i in range(10)]
    tot_ok = tot = 0
    for i in range(10):
        r = np.array(ents[i], dtype=np.uint8); h, w = r.shape
        sc = scr[ys[i]:ys[i] + h, xs[i]:xs[i] + w]; m = r != 0
        ok = int(((sc == r) & m).sum()); print("icon %d at (%d,%d): %d/%d" % (i, xs[i], ys[i], ok, int(m.sum())))
        tot_ok += ok; tot += int(m.sum())
    print("icons total %d/%d" % (tot_ok, tot))

main()
