"""Drive the game OS's memory functions through real trap #9 calls from mg_entry.snap (stub poked into the
zero block of fed_MapGen at $21000, which nothing runs before $20040): fn 116 (largest free, total free),
fn 108 alloc (D0 flags, D1 size), fn 112 free (A0), fn 116 again; prints the 16-byte block headers
(+0 next, +4 prev, +8 id|in-use bit 0 of byte 11, +12 size) around the block. Each call is a labelled poke.
usage: heap_proof.py <snap> [size] [flags]  (STSERVER_DLL as for trap9_log.py)"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from util import root
from stclient import StServer
STUB = 0x21000
def trap(s, fn, **regs):
    code = bytes([0x7e, fn, 0x4e, 0x49, 0x4e, 0x75])  # moveq #fn,D7 / trap #9 / rts
    for i in range(0, 6, 2): s('poke', addr=STUB + i, width=2, value=int.from_bytes(code[i:i+2], 'big'))
    s.call(STUB, ret=0x21100, **regs)
    return s.reg('d0'), s.reg('d1')
def hdr(s, a):
    n, p, f, z = struct.unpack('>4I', s.read(a, 16)); return f'@${a:x}: next ${n:x} prev ${p:x} id ${f:x} size ${z:x}'
s = StServer(root(), dll=os.environ.get('STSERVER_DLL'))
s('load', snapshot=os.path.abspath(sys.argv[1]))
size = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x100; flags = int(sys.argv[3]) if len(sys.argv) > 3 else 4
head = int.from_bytes(s.read(0x1032, 4), 'big')
print('heap list head ($1032):', hex(head), hdr(s, head))
print('fn116 before: largest, total =', [hex(x) for x in trap(s, 116)])
a, _ = trap(s, 108, d0=flags, d1=size)
print(f'fn108 flags {flags} size ${size:x} -> ${a:x}'); print(' ', hdr(s, a - 16))
nxt = int.from_bytes(s.read(a - 16, 4), 'big')
if nxt: print('  next', hdr(s, nxt))
print('fn116 after alloc:', [hex(x) for x in trap(s, 116)])
trap(s, 112, a0=a)
print('fn112 free'); print(' ', hdr(s, a - 16))
print('fn116 after free:', [hex(x) for x in trap(s, 116)])
# clear-flag control: poke a marker (labelled poke) where the block lands, allocate again with and without flag 4
for fl in (flags & ~4, flags | 4):
    s('poke', addr=a, width=4, value=0xa5a5a5a5)
    b, _ = trap(s, 108, d0=fl, d1=size)
    print(f'marker $a5a5a5a5 poked at ${a:x}; fn108 flags {fl} -> ${b:x}, first long now {s.read(b, 4).hex()}')
    trap(s, 112, a0=b)
s.close()
