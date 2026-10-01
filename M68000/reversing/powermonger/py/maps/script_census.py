"""script_census.py [snap]: parse the 195 campaign land scripts the way `$ac20` (_dec_oth) does and count the record kinds.
Table `$3f428` (resource $b, stride $14c); the script is entry + $ac (= $58152 - $580a6): 4-byte records (x, y, d0, type), type 0 ends.
type < $10: settlement (d0 != 0 also queues an 8-byte entry at $4b9f2) + `_flat_ci`; $10: group start cell; $11: road (the next
record supplies the other end; a following $11 is re-read as the next road's start); anything else >= $12: shape stamp."""
import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
ram = ram_from_snap(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'scratchpad/pm122/end/land1_pick_end.snap'))
kinds = collections.Counter(); stamp_lands = []; road_lands = 0; roads = 0
for land in range(195):
    p = 0x3f428 + land * 0x14c + 0xac
    end = 0x3f428 + (land + 1) * 0x14c
    while p < end:
        x, y, d0, ty = ram[p:p + 4]; p += 4
        if ty == 0: break
        if ty < 0x10: kinds['settlement/site'] += 1
        elif ty == 0x10: kinds['group start'] += 1
        elif ty == 0x11:
            nx, ny, _, nty = ram[p:p + 4]; p += 4
            if nty == 0x11: p -= 4
            kinds['road'] += 1; roads += 1
        elif ty == 0x12:
            kinds['stamp $12'] += 1; stamp_lands.append(land)
        else: kinds['other %x' % ty] += 1
print(dict(kinds)); print('standalone $12 stamps in lands:', sorted(set(stamp_lands)))
