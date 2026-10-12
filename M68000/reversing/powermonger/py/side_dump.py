"""side_dump.py <snap>: per side, the lords (index, cell x,y, food +6, men at home +8, loyalty +14; the side is byte 0 of
the $4e514 record) and the six groups (men 52(), state 76(), posture 136(), pending word 4()). Used to scope the
transfer arm (`../strategy.md` "Why a drained side is not enough")."""
import sys,struct,collections
from pathlib import Path
_r = next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
sys.path.insert(0,str(_r / 'tools'))
from gfxview import load_ram
r,_=load_ram(sys.argv[1])
h=lambda a: struct.unpack_from('>h',r,a)[0]
H=lambda a: struct.unpack_from('>H',r,a)[0]
by=collections.defaultdict(list)
for i in range(160):
    a=0x4e514+32*i
    if r[a]==0: continue
    c=H(a+4); by[r[a]].append((i,(c&63,(c>>6)&127),h(a+6),h(a+8),h(a+14)))
for s in sorted(by): print('side',s,'lords (idx,(x,y),food,home,loyalty):',by[s])
for s in range(1,5):
    a=0x51538+316*s
    print('side',s,'groups (men,state,posture,pending):',[(h(a+2*k+52),h(a+2*k+76),h(a+2*k+136),h(a+2*k+4)) for k in range(6)])
