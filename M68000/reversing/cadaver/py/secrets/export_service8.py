"""export_service8.py: the object-verb block's "teleport to room N" verb ($010974, mechanics.md section 4) IS reachable: it is entry 8
(D6=32) of the level overlay's engine export table at $006082 (installed by `move.l #$6082,392(A5)` at $00b5ec, read by the trampoline
$04caaa: `movea.l 392(A5),A6 / movea.l 0(A6,D6.w),A6 / jmp (A6)`).  The raw bytes $00010974 at $0060a2 are not a coincidence of a table read as 4-byte aligned from
$006080: the table is 2 mod 4 ($006082) and $0060a2 = $006082 + 8*4.
Start gameplay_empire.snap (CAVERN loaded, (A5)+1166 = 0).  Writes the 4 script bytes 01 02 03 04 (room 1, dx, dy, facing) at $0f0000,
calls the trampoline with D6=32 A1=$0f0000 under `callcap` (state restored afterwards) and prints the delta of the room fields:
(A5)+1166 -> 1, (A5)+164 (room record pointer) $06bf0a -> $06bf84 (TUNNEL's record, mechanics.md section 5), A1 advanced by exactly 4.
    uv run python reversing/cadaver/py/secrets/export_service8.py"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
r = Repl()
out = r.cmd('w f0000 01020304', 'callcap 4caaa 3000000 - D6=20 A1=f0000')
mem = {}
for l in out:
    if l.startswith('mem $'):
        a, v = l.split()[1], l.split()[2]
        mem[int(a[1:], 16)] = v
for l in out:
    if l.startswith('regdelta'):
        print([t for t in l.split('  ') if t.startswith('A1 ')])
print('(A5)+1166 low byte $%06x:' % (A5 + 1167), mem.get(A5 + 1167))
print('(A5)+164 pointer byte $%06x:' % (A5 + 167), mem.get(A5 + 167), '(expect $0a->$84)')
r.close()
