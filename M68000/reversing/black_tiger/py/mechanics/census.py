"""Marker census of the eight level files (decoded with levelmap.load; no emulator needed).
Prints, per level, item-marker counts (1..$27), actor-marker counts ($28..$3c -> actor type) and anchors."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
import levelmap as lm
for n in range(8):
    w, h, words, ln = lm.load(n)
    cnt = collections.Counter(wd >> 10 for wd in words if wd >> 10)
    items = {k: v for k, v in sorted(cnt.items()) if k < 0x28}
    acts = {k - 0x27: v for k, v in sorted(cnt.items()) if 0x28 <= k < 0x3d}
    anch = {}
    for i, wd in enumerate(words):
        if wd >> 10 in (0x3d, 0x3e, 0x3f): anch["%x" % (wd >> 10)] = (i % w * 16, i // w * 16 + 16)
    print("file %d (%dx%d tiles = %dx%d px, %d bytes)" % (n, w, h, w * 16, h * 16, ln))
    print("  item markers :", " ".join("%x:%d" % kv for kv in items.items()))
    print("  actor types  :", " ".join("%x:%d" % kv for kv in acts.items()))
    print("  anchors 3f(start) 3e(warp-in) 3d(boss):", anch)
