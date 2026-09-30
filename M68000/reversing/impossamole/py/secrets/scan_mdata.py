import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
r = ram()
for n in ['MDATA1.DCH','MDATA2.DCH','MDATA3.DCH','MDATA4.DCH','MDATA5.DCH','PICTURES.DCH','SELECT44.DAT']:
    f = rd(n)
    o, *_ = depack(f)
    U = len(o)
    # best offset match against $53000.. window
    print(n, 'packed', len(f), 'unpacked', U, 'head', o[:16].hex())
    # search for a 32-byte non-zero-ish chunk of the unpacked data anywhere in RAM
    for off in (0, 64, 4096):
        chunk = o[off:off+48]
        idx = r.find(chunk)
        print('   chunk@%d in RAM at' % off, hex(idx) if idx >= 0 else None)
