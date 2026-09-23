"""byte6 census over the $47970 per-cell bucket walk (what $115e0 draws), whole map.
usage: census.py <snap-or-ram> ...   (tolerates a torn chain: reports it)"""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from pm_export import ram_from_snap, Ram
from pathlib import Path
BUCK, OBJ_BASE = 0x47970, 0x51B66
def walk(r):
    ram = Ram(r)
    out, seen, torn = [], set(), 0
    for wcy in range(128):
        for wcx in range(64):
            d4 = ram.u16(BUCK + (wcy*64+wcx)*2)
            while d4:
                off = d4 - 0x10000 if d4 >= 0x8000 else d4
                o = OBJ_BASE + off
                if not (0x40000 <= o < 0x60000) or o in seen:
                    torn += 1; break
                seen.add(o)
                out.append((o, wcx, wcy, r[o:o+50]))
                d4 = ram.u16(o)
    return out, torn
if __name__ == '__main__':
    for p in sys.argv[1:]:
        r = ram_from_snap(Path(p)) if p.endswith('.snap') else Path(p).read_bytes()
        recs, torn = walk(r)
        c = collections.Counter(rec[6] for _,_,_,rec in recs)
        print(Path(p).stem, 'params', r[0x58146:0x58152].hex(), 'season', r[0x57fd1],
              'torn', torn, 'byte6', dict(sorted(c.items())))
