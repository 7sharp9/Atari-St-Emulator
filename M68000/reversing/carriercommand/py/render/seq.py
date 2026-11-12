import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys, struct
REC = struct.Struct('<QIIHBB')
d = open(sys.argv[1], 'rb').read()
want=set(int(x,16) for x in sys.argv[2:])
last=None; n=0
for off in range(16, len(d) - REC.size + 1, REC.size):
    sc, pc, tgt, op, kind, fl = REC.unpack_from(d, off)
    if kind==3 and (tgt&0xffffff) in want:
        t=tgt&0xffffff
        print(f'{sc} ${t:x} from ${pc:x}')
