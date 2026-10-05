"""How much does each rule matter?  For every dumped frame of the given dirs, render with one rule changed and count
frames/pixels that then differ from MAME's own snapshot.  Shows the rules are exercised, not vacuously matched.
usage: sensitivity.py name [name...]   (dump dirs under dumps/, snapshots under run/<name>/snap)"""
import os, sys, glob, re
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def variants(st):
    pal = R.palette_rgb(st.palraw)
    out = {}
    out["as_dumped"] = R.render_rgb(st, st.fodd, st.pri)
    out["pri_inverted"] = R.render_rgb(st, st.fodd, 1 - st.pri)
    out["flash_parity_inverted"] = R.render_rgb(st, 1 - st.fodd, st.pri)
    # palette without the 0x8e clamp / scaling: plain 8 bit channels
    raw = st.palraw
    plain = np.stack([(raw >> s) & 0xff for s in (0, 8, 16)], axis=1).astype(np.uint8)
    buf, _ = R.render_indexed(st, st.fodd, pri_override=st.pri)
    out["palette_unscaled"] = plain[buf]
    # sprites drawn without the y bit 15 / colour bit 4 priority split (one layer, behind everything but pf1)
    return out

if __name__ == "__main__":
    tot = {}
    nfr = 0
    for name in sys.argv[1:]:
        for b in sorted(glob.glob(os.path.join(ROOT, "dumps", name, "f*.bin"))):
            f = int(re.search(r"f(\d+)", b).group(1))
            st = R.State.load(b, f)
            ref = np.array(Image.open(os.path.join(ROOT, "run", name, "snap", "f%05d.png" % f)).convert("RGB"))
            nfr += 1
            for k, img in variants(st).items():
                d = int((img != ref).any(axis=2).sum())
                t = tot.setdefault(k, [0, 0]); t[0] += d > 0; t[1] += d
    print("frames", nfr)
    for k, (fr, px) in tot.items():
        print("%-24s frames with any differing pixel: %4d   differing pixels in total: %d" % (k, fr, px))
