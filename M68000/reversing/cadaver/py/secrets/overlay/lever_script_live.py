"""lever_script_live.py: inject a 'touched' event (ring-304 opcode 5) for the TUNNEL lever object (type 6 id 144, record
$06fa0e) into the queue the consumer $00fdbc drains, and watch its own script run.  Start snapshot
scratchpad/cadaver/room2_tunnel_entry.snap (TUNNEL loaded), or gameplay_empire.snap (the lever record is resident there too).
Expected: $00fe24=1, $00fe30=1, $00fe5a=2, verbs executed (table indices) 10, 14, 30, 32 = the script bytes $0a,$0e,$1e,$20, byte +3 of the record $00->$01.  Ring-304 queue: entries [opcode.w][object ptr.l][word], read from 152(A5), count 1154(A5), write cursor 304(A5).
The lever record's script block at +$10 is [$12 len][$85 = event 5 | keep][verbs ...][$17 end].  Prints hits on $00fe24 (event
matched a block), $00fe5a (verb dispatch via table $00ffba), and the bytes of the record before/after."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
r = Repl(snap)
LEVER = 0x6fa0e
print('lever record before', r.mem(LEVER, 48).hex())
q = int.from_bytes(r.mem(a5(152), 4), 'big')
print('queue base 152(A5) = $%06x, count 1154(A5) = %d' % (q, int.from_bytes(r.mem(a5(1154), 2), 'big')))
wl(r, q, 0x0005_0006); wl(r, q + 4, 0xfa0e_0000)       # [0005][0006fa0e][0000]
ww(r, a5(1154), 1)
print('queue entry', r.mem(q, 10).hex())
h = r.hits(60000, 0xfdbc, 0xfe24, 0xfe30, 0xfe5a, 0x1049a)
print({hex(k): v for k, v in h.items()})
print('lever record after ', r.mem(LEVER, 48).hex())
r.close()

# second pass: which verb handlers ran?  hits on every entry of the $00ffba table
import struct
r = Repl(snap)
ram = None
tab = [0xffba + int.from_bytes(r.mem(0xffba + 2 * i, 2), 'big') for i in range(94)]
q = int.from_bytes(r.mem(a5(152), 4), 'big')
wl(r, q, 0x0005_0006); wl(r, q + 4, 0xfa0e_0000); ww(r, a5(1154), 1)
h = r.hits(60000, *sorted(set(tab)))
fired = [(i, hex(a)) for i, a in enumerate(tab) if h.get(a)]
print('verbs executed (index, handler):', fired)
r.close()
