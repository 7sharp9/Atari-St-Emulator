"""boss_check.py - boss sprite banks (BTA/BTB loaded over BTSPR, BTSPR types 1 and $c) against live boss frames.
Banks are read from the snapshot RAM (the bank the game really loaded).  For every actor in slots 1.. of the
boss snapshots B<k>_<i> (hero left of boss, facing 1) and BR<k>_<i> (hero right of boss, facing 0 = mirrored):
slide the frame (frame, frame-1; both orientations; +-24 px) over the draw buffer.  Reports exact matches
(ok == tot, tot >= 100) per boss type and width code, split by orientation."""
import collections
import glob
import io
import contextlib
import re

from ram_actors import *
from ram_actors import main as ram_main


def main():
    names = sorted(glob.glob(os.path.join(OUT, "boss", "B?_?.snap")) + glob.glob(os.path.join(OUT, "boss", "BR?_?.snap")))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        lines = ram_main(names)
    open(os.path.join(OUT, "boss_check.txt"), "w").write("\n".join(lines) + "\n")
    agg = collections.defaultdict(lambda: [0, 0])
    for l in lines:
        m = re.match(r"(BR?)(\d)_\d.snap slot (\d+) type (\w+) .*code (\d+) H (\d+): best (-?\d+)/(\d+).*mirrored=(\d)", l)
        if not m or m.group(3) == "0":
            continue
        key = (m.group(4), "code %s" % m.group(5), "mirrored" if m.group(9) == "1" else "as stored")
        agg[key][1] += 1
        if m.group(7) == m.group(8) and int(m.group(8)) >= 100:
            agg[key][0] += 1
    tot_e = tot = 0
    for k, (e, n) in sorted(agg.items()):
        print("type %s %s %-9s: exact %d of %d instances" % (k[0], k[1], k[2], e, n))
        tot_e += e; tot += n
    print("boss/object instances (slots 1..): %d, exact %d" % (tot, tot_e))


main()
