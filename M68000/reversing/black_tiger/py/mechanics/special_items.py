"""List the non-urn/non-coin item markers (x,y in pixels as the scanner stores them: col*16+8, row*16+16) per level.
Types: $0a chest, $0f hourglass, $10 smart-bomb, $11 shop man, $12-$16 old men, $1b door-in, $1c door-out, $1d fire-column trap,
$1e rock trap, $1f checkpoint, $20 level exit.  Writes special_items.txt next to the notes."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b, levelmap as lm
out = []
for n in range(8):
    w, h, words, _ = lm.load(n)
    out.append("level %d (file %d, %dx%d tiles)" % (n + 1, n, w, h))
    byt = {}
    for i, wd in enumerate(words):
        m = wd >> 10
        if m in (3, 4, 5, 6, 7, 8, 9, 0xa, 0xc, 0xd, 0xe, 0xf, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20):
            byt.setdefault(m, []).append(((i % w) * 16 + 8, (i // w) * 16 + 16))
    for m, pts in sorted(byt.items()):
        out.append("  item %02x x%-2d %s" % (m, len(pts), " ".join("(%d,%d)" % p for p in pts)))
open(os.path.join(b.OUT, "special_items.txt"), "w").write("\n".join(out) + "\n")
print("\n".join(out[:20]))
