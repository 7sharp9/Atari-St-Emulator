"""Decode Impossamole's level spawn list ($27200, 4-byte records) from a snapshot (README "Rooms").

    uv run python reversing/impossamole/py/spawn_list.py <snap>

Record = tile column (word), row byte (y = row*8+8), type byte; sorted by column, $7fff ends it.
The type byte indexes the descriptor pointer table at $10474; the descriptor's first byte picks the
allocator ($10046: 0 = slots 0-5 at $1a2ea, 1 = slots 7-11 at $1a5de, 2 = $1021a, 3 = $1037a).
Columns are in the whole 1680-column map; the block (col>>2) says which room(s) contain the record.
"""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from level_map import transitions
from pm_export import ram_from_snap

ram = ram_from_snap(Path(sys.argv[1]))
w = lambda a: struct.unpack_from('>H', ram, a)[0]
_, start, recs = transitions(ram)
rooms = sorted({start} | {(r[2], r[3]) for r in recs})
a = 0x27200
while ram[a:a + 4] == b'\0\0\0\0':
    a += 4
print('col  blk  y    type kind descriptor            rooms')
while w(a) != 0x7fff:
    col, row, typ = w(a), ram[a + 2], ram[a + 3]
    d = struct.unpack_from('>I', ram, 0x10474 + 4 * typ)[0]
    inr = '|'.join(f'{s}..{e}' for s, e in rooms if s <= col // 4 < e)
    print(f'{col:4} {col // 4:4} {row * 8 + 8:3}  {typ:3}  {ram[d]:3}  ${d:05x} {ram[d:d + 12].hex()}  {inr}')
    a += 4
