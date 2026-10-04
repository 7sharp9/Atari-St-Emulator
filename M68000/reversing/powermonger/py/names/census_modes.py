"""census_modes.py <snap>... | --glob <dir-glob>: live men (side byte5 > 0) in entity modes $04/$06/$08 (and $02, $0a for context) over snapshots:
count per mode, how many are group followers (flag bit 6 of byte 7), have a lead word 28 != 0 whose record is a live leader (bit 4), a group word 42 != 0,
and the previous-mode byte 30.  Run from M68000/.  Object records: 512 x 50 bytes at $51b66."""
import glob, os, sys
from collections import Counter
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap
OBJ = 0x51b66
args = sys.argv[1:]
if args and args[0] == "--glob":
    args = sorted(glob.glob(str(ROOT / args[1]), recursive=True))
tot = Counter(); detail = {m: Counter() for m in (2, 4, 6, 8, 10)}
n_snaps = 0
for s in args:
    try:
        r = ram_from_snap(s)
    except Exception:
        continue
    if len(r) < 0x60000: continue
    n_snaps += 1
    for i in range(512):
        a = OBJ + 50 * i
        if not (1 <= r[a + 5] <= 127): continue
        m = r[a + 31]
        if m not in detail: continue
        tot[m] += 1
        w = lambda o: int.from_bytes(r[a + o:a + o + 2], "big")
        lead = w(28)
        lr = OBJ + lead if lead else None
        d = detail[m]
        d["bit6"] += bool(r[a + 7] & 0x40)
        d["bit4"] += bool(r[a + 7] & 0x10)
        d["lead!=0"] += lead != 0
        d["lead_is_leader(bit4)"] += bool(lr and r[lr + 7] & 0x10 and 1 <= r[lr + 5] <= 127)
        d["group42!=0"] += w(42) != 0
        d["off20/22!=0"] += (w(20) | w(22)) != 0
        d["prev=%02x" % r[a + 30]] += 1
        d["byte6=%02x" % r[a + 6]] += 1
        d["afloat(bit5)"] += bool(r[a + 7] & 0x20)
print("%d snapshots" % n_snaps)
for m in (2, 4, 6, 8, 10):
    print("mode $%02x: %d men" % (m, tot[m]), dict(detail[m].most_common(14)))
