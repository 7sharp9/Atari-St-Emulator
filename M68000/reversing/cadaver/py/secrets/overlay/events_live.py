"""events_live.py: prove the scripted-event dispatch ($00e218-$00e24e: event list (A5)+1266, records [type][sub][object ptr.l],
count word (A5)+1264; handler = overlay base + word at (base + 4*(type+9) + 2) + word at (table + 2*sub)).  Start snapshot
scratchpad/cadaver/gameplay_empire.snap (level 0).  One event record (type, sub, $070034) is queued, 60,000 steps run with
`hits` on $00e24e (the `jsr (A1)`) and on the expected overlay handler.  Events: class 4 sub 0/1 ($04c798/$04c7c0), class 7
sub 0 ($04c7e4), class 10 sub 0 ($04c856).  Expected: both addresses hit once for each."""
import sys, struct
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
BASE = 0x4c65e
ov = open('scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin', 'rb').read()[4:]
W = lambda o: struct.unpack_from('>H', ov, o)[0]; S = lambda o: struct.unpack_from('>h', ov, o)[0]
ok = 0
for typ, sub in ((4, 0), (4, 1), (7, 0), (10, 0)):
    evt = W(4 * (typ + 9) + 2)
    tgt = BASE + evt + S(evt + 2 * sub) if evt else None
    r = Repl()
    ww(r, a5(1264), 1)
    # record at 1266(A5): type byte, sub byte, long object ptr (even address 1266 -> write 6 bytes as two longwords)
    wl(r, a5(1266), (typ << 24) | (sub << 16) | 0x0007)
    wl(r, a5(1270), 0x0034 << 16 | 0x0000)
    cur = r.mem(a5(1266), 8); print('  queued', cur.hex(), end=' ')
    addrs = [0xe24e] + ([tgt] if tgt else [])
    h = r.hits(60000, *addrs)
    print('type %d sub %d: event word $%04x handler %s  hits: $e24e=%d handler=%s' % (typ, sub, evt, ('$%06x' % tgt) if tgt else 'none', h[0xe24e], h.get(tgt)))
    ok += (h[0xe24e] == 1 and (tgt is None or h.get(tgt) == 1))
    r.close()
print('matched', ok, 'of 4')
