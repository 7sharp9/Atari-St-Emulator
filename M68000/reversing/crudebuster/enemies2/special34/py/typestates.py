"""For a pool A type: handler address, its state table(s) (by the `lea N(PC)/movea.l 0(A0,D0.w),A0` idiom, searched from the handler to the next handler
address, plus any extra ranges given), and for each distinct state routine the states using it. Shared engine routines ($22000-$27fff) are tagged.
usage: typestates.py <type hex> [extra_lo extra_hi ...]"""
import os, sys, re
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "../.."))
os.environ.setdefault("M68000_ROOT", os.path.abspath(os.path.join(here, "../../../../..")))
sys.path.insert(0, os.path.join(here, "../../py"))
import handler_tables as ht
rom = ht.rom
hs = [int.from_bytes(rom[0x10418 + 4 * i:0x10418 + 4 * i + 4], "big") for i in range(80)]
order = sorted(set(hs))
ty = int(sys.argv[1], 16)
h = hs[ty]
nxt = [x for x in order if x > h]
hi = nxt[0] if nxt else 0x22000
ranges = [(h, hi)] + [(int(sys.argv[i], 16), int(sys.argv[i + 1], 16)) for i in range(2, len(sys.argv) - 1, 2)]
print(f"type {ty:02x}: handler ${h:06x}, own range to ${hi:06x}")
for lo, hh in ranges:
    for a, t, ents in ht.tables(lo, hh):
        print(f" dispatch ${a:06x} table ${t:06x} ({len(ents)} entries)")
        by = {}
        for i, e in enumerate(ents): by.setdefault(e, []).append(i)
        for e, sts in sorted(by.items()):
            tag = "shared engine" if 0x22000 <= e < 0x28000 else ("own" if h <= e < hi else "other type region")
            print(f"   ${e:06x} states {[f'{s:x}' for s in sts]}  [{tag}]")
