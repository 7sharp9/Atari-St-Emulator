import sys,os,struct
d=os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d,'tools','rdis.py')): d=os.path.dirname(d)
sys.path.insert(0,os.path.join(d,'reversing','starglider','py'))
import sgcommon as sg
from collections import Counter
r=sg.load_ram(sg.SNAP_GAME1)
L=lambda a:struct.unpack('>I',r[a:a+4])[0]
W=lambda a:struct.unpack('>H',r[a:a+2])[0]
seen=[]
for lv in range(0,6):
    p=L(0x22814+4*lv)
    if p in seen: print('level',lv,'= same as',seen.index(p)); seen.append(p); continue
    seen.append(p)
    ents=[]
    while W(p):
        ents.append((W(p),W(p+2),W(p+4),W(p+6))); p+=8
    print('level',lv,'entries',len(ents),'end',hex(p),sorted(Counter(e[0] for e in ents).items()))
    if '-v' in sys.argv: print(ents)
