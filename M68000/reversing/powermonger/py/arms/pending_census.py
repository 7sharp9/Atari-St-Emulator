"""pending_census.py <snap>...: classify every non-lead group (D7 != 0, owner > 0) whose pending word 4(group) is set:
  flying   a live order pigeon (category $14, owner > 0) rides to the group's lead (word 20 == lead offset)
  deadpig  a pigeon to the lead with owner <= 0 (launched by a dead sender: $4562 copies 5(sender); the $3e06 pool loop skips it forever)
  queued   no pigeon, the side's pending record (long at the side's slot, $6522 `tst.l 0(A1)`) non-zero
  orphan   none of these (the pigeon was freed without clearing the word: $2776 on a first group frees every pigeon of the side)
Also counts how many of those sides have a live first group (owner word > 0 and lead owner byte > 0)."""
import collections, sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
OBJ = 0x51b66
def w(r, a): return (r[a] << 8) | r[a + 1]
def s16(v): return v - 0x10000 if v & 0x8000 else v
def s8(v): return v - 0x100 if v & 0x80 else v
tot = collections.Counter(); g0dead = collections.Counter()
for sn in sys.argv[1:]:
    r = ram_from_snap(sn)
    pig = [(0x4c112 + 26 * i) for i in range(1, 48)]
    pig = [p for p in pig if r[p + 6] == 0x14]
    for sd in range(1, 5):
        slot = 0x51538 + sd * 0x13c
        g0 = slot; g0own = s16(w(r, g0 + 28)); g0lead = (OBJ + s16(w(r, g0 + 64))) & 0xfffff
        g0alive = g0own > 0 and s8(r[g0lead + 5]) > 0
        for k in range(1, 6):
            A1 = slot + 2 * k
            if s16(w(r, A1 + 28)) <= 0 or w(r, A1 + 4) == 0: continue
            lead = w(r, A1 + 64)
            ps = [p for p in pig if w(r, p + 20) == lead]
            if any(s8(r[p + 5]) > 0 for p in ps): c = 'flying'
            elif ps: c = 'deadpig'
            elif any(r[slot:slot + 4]): c = 'queued'
            else: c = 'orphan'
            tot[c] += 1; g0dead[(c, 'g0 alive' if g0alive else 'g0 dead')] += 1
print(len(sys.argv) - 1, 'snapshots;', dict(tot)); print(dict(g0dead))
