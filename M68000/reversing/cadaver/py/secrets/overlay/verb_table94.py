"""verb_table94.py [snap]: dump the object-script verb dispatch table at $00ffba.  Entry i is a word offset from $00ffba; the
first entry ($00bc) equals the table size in bytes, so the table has $bc/2 = 94 entries and ends exactly where $010076 begins.
mechanics.md 23a's '59-entry table at $010000-$010075' is this table's last 59 entries (old id = new id - 35).  The consumer
that runs it: $00fe46-$00fe5e (`move.b (A1)+,D0 / cmpi.b #$17,D0 (END) / lea $ffba.l,A2 / bsr $11728`).  Also dumps the
precondition table at $00fe84 (29 entries, gate per queued event opcode) for contrast.  Start snapshot gameplay_empire.snap."""
import sys, struct
sys.path.insert(0, 'tools')
from gfxview import load_ram
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, _ = load_ram(snap)
U16 = lambda a: struct.unpack_from('>H', ram, a)[0]
n = U16(0xffba) // 2
print('verb table $00ffba: %d entries' % n)
ents = [0xffba + U16(0xffba + 2 * i) for i in range(n)]
known = {0x10914: 'CREATE (old id 1)', 0x1039a: 'UNINV (old 15)', 0x1049a: 'LOCK (old 18)', 0x10e7e: 'STOPACTI (old 31)', 0x10ea2: 'MOVE (old 32)', 0x10ee2: 'UNLOCK CHEST (old 34)', 0x10f0e: 'UNTRAP CHEST tail (old 35)',
         0x10e38: 'queue event (type,sub) into 1266(A5): feeds $e218 (old 25 entry body)', 0x100b0: 'SHOW object = export service 21', 0x10076: 'resolve-by-operand alias (mechanics 24a aside)', 0x101c2: 'hide current actor target', 0x101a8: 'HIDE object (export 20 enters at $101ae)', 0x10f7c: 'POISON(strength,duration,interval) -> timers 0/1'}
for i, a in enumerate(ents):
    print('  verb %2d (old id %3s) -> $%06x  %s' % (i, i - 35 if i >= 35 else '-', a, known.get(a, '')))
print('precondition table $00fe84:')
m = U16(0xfe84) // 2
print('  %d entries' % m, ['$%06x' % (0xfe84 + U16(0xfe84 + 2 * i)) for i in range(m)])
