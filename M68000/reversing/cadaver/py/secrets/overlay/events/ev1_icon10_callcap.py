"""a3: ev1_icon10_callcap.py -- what the READ-icon handler $00a0ce (icon $10, push site $00a114) writes into the ring-304 queue.  callcap $a0ce with A1 = the record of a scroll (id 132, READ LANGUAGE,
body byte 0 = spell id 3) and 2128(A5) = 51 (the front object, level 0); prints the entry [op][ptr][word] it queued and the ids behind ptr and word.  Expected: op 1, ptr = record of 51, word = 132 (the item id);
the event-1 gate of object 51 (operand 3) then accepts when the word resolves to a record whose body byte 0 is 3."""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
OUTDIR = os.environ.get('OUTDIR') or os.path.join(ROOT, 'scratchpad/cadaver/s91_events'); os.makedirs(OUTDIR, exist_ok=True)   # scratch output (callcap json, caches, scan listings)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
import h as HH
from lib2 import afterl, afterw, afterb
os.chdir(ROOT); HH.TMP = OUTDIR
from h import *
h = HH.H(os.path.join(ROOT, 'scratchpad/cadaver/gameplay_empire.snap'))
r = h.r; A5 = HH.A5
ww(r, A5 + 2128, 51)
wq = r.l(A5 + 304); cnt0 = r.w(A5 + 1154)
d = h.call(0xa0ce, [], cap=20000, regs='A1=%x A0=%x' % (h.obj(132), h.obj(2)))
print('returned', d['ret'], 'steps', d['steps'])
op = (afterw(h, d, wq)); ptr = afterl(h, d, wq + 2); word = afterw(h, d, wq + 6)
print('entry op=%04x ptr=%06x word=%04x   count %d -> %d   write ptr +%d' % (op, ptr, word, cnt0, afterw(h, d, A5 + 1154), afterl(h, d, A5 + 304) - wq))
idof = lambda p: int.from_bytes(h.ram[p + 4:p + 6], 'big')
print('ptr -> object id %d (want 51: %s), word %d (want 132: %s)' % (idof(ptr), idof(ptr) == 51, word, word == 132))
print('body byte0 of object id word=%d is %d (event-1 gate operand of object 51 is 3)' % (word, h.ram[h.obj(word) + h.ram[h.obj(word) + 12]]))
h.close()
