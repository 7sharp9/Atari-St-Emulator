"""boss_atlas.py - BTA / BTB: replacement sprite banks loaded over BTSPR by the level-specific boss
object (file letter from the per-level table at $17226+4*level+2: levels 2,5,7 'a', 4,6 'b'; the
loader is the fn9 call at $cff4..$d00e).  All 20 bank offsets point at one bank at +$50 (H=64):
BTA code 8 (128 px wide, 4096 B/frame), BTB code 4 (64 px wide, 2048 B/frame)."""
import os

from bt_common import *  # noqa
from sprites import *  # noqa
from sprite_atlas import bank_extent


def main():
    out = []
    for nm, tset in (("BTA", "T2"), ("BTB", "T4")):
        d = read_file(nm)
        pal = pal_from_bytes(read_file(tset), 0)
        b, code, slot, first, n, rem, refs = bank_extent(d, 0x50, len(d))
        frames = [(0, k, first + k * slot, code, decode_frame(d, 0x50 + first + k * slot, code, b["H"])) for k in range(n)]
        sheet_image(frames, pal, cols=3, scale=2).save(os.path.join(PNG, "spr_%s_boss.png" % nm))
        out.append("%s: bank at +$50, H=%d code=%d slot=%d first frame +$%x slots=%d trailing=%d anims=%d" %
                   (nm, b["H"], code, slot, first, n, rem, len(b["anims"])))
        for k, a in enumerate(b["anims"]):
            out.append("   anim %d: n=%d dx=%d dy=%d trig=%x frames=%s" % (k, a["n"], a["dx"], a["dy"], a["trig"], [hex(f) for f in a["frames"]]))
    print("\n".join(out))
    open(os.path.join(OUT, "boss_banks.txt"), "w").write("\n".join(out) + "\n")


main()
