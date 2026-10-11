"""xfer_info.py <snap at $668c> <A1 hex> <D7>: the decision inputs of a natural transfer arm: men, food, state, pending, own and enemy lords'
home troops (word 8 of the 32-byte leader records), what $69b4(8) and $68fe return (the model's own leaves), and predicate_check.predict."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/cmdai')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
import pm_fsm_ref as P, cmdai_ref as C
from disassemble import ram_from_snap
import predicate_check as PC
snap, A1, D7 = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
ram = ram_from_snap(snap); P.init_tables(ram)
m = P.Mem(ram)
A2 = (C.OBJ + C.s16(m.wu(A1 + 64))) & 0xfffff
own = m.bu(A2 + 5)
lords = [a for a in range(C.LORDS, C.LORDS_END, 32) if m.bu(a)]
print('side %d group %d men %d food %d state %d prev? %d pending %d camp %d clock %d' % (own, D7 // 2, C.s16(m.wu(A1 + 52)), C.s16(m.wu(A1 + 112)),
      m.wu(A1 + 76), m.wu(A1 + 78), C.s16(m.wu(A1 + 4)), C.s16(m.wu(A1 + 256)), m.wu(0x2df72)))
print('own lords home  :', [C.s16(m.wu(a + 8)) for a in lords if m.bu(a) == own])
print('enemy lords home:', sorted((m.bu(a), C.s16(m.wu(a + 8))) for a in lords if m.bu(a) != own))
r = C.call_69b4(P.Mem(bytearray(ram)), A2, 8); print('$69b4(8) ->', [hex(x) if isinstance(x, int) else x for x in r])
men = C.s16(m.wu(A1 + 52))
if men - 4 > 0: print('$68fe(men-4) ->', C.call_68fe(P.Mem(bytearray(ram)), A1, A2, men - 4))
print('predict:', PC.predict(P.Mem(bytearray(ram)), A1, A2, D7))
