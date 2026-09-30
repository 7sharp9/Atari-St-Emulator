"""consumer_live.py: is the ring-304 queue consumer ($00fdbc) the object-verb interpreter's caller?  It matches a queued event
opcode against per-object script blocks (object+$10 / +$20: [len][event|flag][verb bytes .. $17]) and runs the verbs through the
table at $00ffba via `bsr $11728` at $00fe5a (A1 = script cursor).  Start snapshot gameplay_empire.snap: hold joystick-1 Right
(picks up a coin on the way, known from mechanics.md 70).  Expected (negative control): $00fdbc runs every frame (49 calls) but no queued event matches a script block ($00fe24 = 0).  Counts hits on $00fdbc (consumer), $00fe30 (precondition gate),
$00fe5a (verb dispatch) and $00fe24; with `bp` prints A1/D0 at the first verb dispatch."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
r = Repl()
r.cmd('kbd ff', 's 300', 'kbd 08')
h = r.hits(1200000, 0xfdbc, 0xfe24, 0xfe30, 0xfe5a, 0xffa4)
print({hex(k): v for k, v in h.items()})
r.cmd('kbd ff', 'kbd 00')
r.close()
