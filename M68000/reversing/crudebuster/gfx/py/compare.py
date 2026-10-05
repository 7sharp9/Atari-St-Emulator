"""Render dumped frames with cbrender and count identical pixels against MAME's own snapshot of the same frame.
usage: compare.py <dumps/name> <run/name/snap> [frame ...]   (all frames if none)  [--odd=0|1 to force flash parity]"""
import os, sys, glob, re
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R
import ctllog as CL


_LOGS = {}
def getlog(d):
    p = os.path.join(d, "ctl_log.txt")
    if p not in _LOGS:
        _LOGS[p] = CL.CtlLog(p) if os.path.exists(p) else None
    return _LOGS[p]


def compare(binp, pngp, odd=None, save=None, split=True):
    f = int(re.search(r"f(\d+)\.bin", binp).group(1))
    st = R.State.load(binp, f)
    log = getlog(os.path.dirname(binp)) if split else None
    nseg = 1
    if log is None:
        mine = R.render_rgb(st, st.fodd if odd is None else odd)
    else:
        segs = log.segments(f)
        nseg = len(segs)
        mine = R.render_rgb_segments(st, st.fodd if odd is None else odd, st.pri, segs)
    ref = np.array(Image.open(pngp).convert("RGB"))
    assert ref.shape == mine.shape, (ref.shape, mine.shape)
    same = (ref == mine).all(axis=2)
    if save:
        Image.fromarray(np.concatenate([ref, mine, np.where(same[:, :, None], 0, 255).astype(np.uint8) * np.ones((1, 1, 3), np.uint8)], axis=1)).save(save)
    st.nseg = nseg
    return f, int(same.sum()), same.size, st


if __name__ == "__main__":
    d, snap = sys.argv[1], sys.argv[2]
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    odd = None
    for a in sys.argv[3:]:
        if a.startswith("--odd="): odd = int(a[6:])
    bins = sorted(glob.glob(os.path.join(d, "f*.bin")))
    if args:
        bins = [b for b in bins if int(re.search(r"f(\d+)", b).group(1)) in set(map(int, args))]
    tot = 0; totn = 0
    for b in bins:
        png = os.path.join(snap, os.path.basename(b).replace(".bin", ".png"))
        f, same, n, st = compare(b, png, odd)
        print("frame %5d  %6d / %d identical  pri=%d ctl0=%s ctl1=%s seg=%d" % (f, same, n, st.pri, " ".join("%04x" % c for c in st.ctl[0]), " ".join("%04x" % c for c in st.ctl[1]), st.nseg))
