"""Island-defence census: load a snapshot, apply pokes, step N, count launches by the island structures.
usage: defence.py <snap> <steps> [addr:width:hexvalue ...] [diff=<hex>]  (diff= pokes $446 and every value $18da6 derives from it)   (run from M68000/)
Counts instruction starts at: $19cc6 missile-site launch, $19c0c drone-launcher launch, $19856 command-centre SAM
launch, $19bcc/$19c56/$1980c/$19912 entries; prints $446..$456, $a24/$a40/$a3e/$a41 before and after."""
import sys, struct
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent)); from ccpaths import ROOT
sys.path.insert(0, str(ROOT / 'tools')); from stclient import StServer
snap, steps = sys.argv[1], int(sys.argv[2])
s = StServer(str(ROOT)); s('load', snapshot=snap)
def derive(v):
    """$18da6 transcribed: the parameters the game derives from difficulty $446 (signed cmp.w where the code uses them)."""
    sv = v - 0x10000 if v & 0x8000 else v
    p = {0x446: v, 0x448: 3 if sv >= 0x4000 else 2}
    p[0x44a] = 3 + ((v - 0x8000) // 10000 if sv < 0 else 0)
    d0 = v >> 6; d2 = d0; d0 >>= 4
    p[0x44c] = d0 + (d0 >> 1) + 0x96; p[0x452] = d0 + 0xc8
    d2 += 0x400; p[0x454] = d2; d2 >>= 1; p[0x44e] = d2 + (d2 >> 1)
    p[0x456] = v if sv >= 0x4000 else 0x4000
    p[0x450] = (v >> 4) + 0x200; p[0x18a1c] = p[0x18a74] = p[0x450] + 0x800
    return p
for p in sys.argv[3:]:
    if p.startswith('diff='):
        for a, v in derive(int(p[5:], 16)).items(): s('poke', addr=a, width=2, value=v & 0xffff)
        continue
    a, w, v = p.split(':'); s('poke', addr=int(a, 16), width=int(w), value=int(v, 16))
def show(tag):
    d = struct.unpack('>9H', s.read(0x446, 18))
    a24 = struct.unpack('>I', s.read(0xa24, 4))[0]; f = s.read(0xa3e, 4)
    isl = s.read(a24 + 1, 1)[0] if a24 else -1
    pc60 = struct.unpack('>I', s.read(0x5e95a + 60, 4))[0]
    print(tag, 'diff $446..$456', ' '.join('%04x' % x for x in d), '| $a24', hex(a24), 'isl', isl,
          '$a3e..a41', f.hex(), 'blocks', s.read(0x62cda, 2).hex(), s.read(0x63cec, 2).hex(), '| player carrier +60', hex(pc60), 'state', struct.unpack('>3h', s.read(0x11ba, 6)))
show('before')
L = {0x19cc6: 'missile-site launch', 0x19c0c: 'drone launch', 0x19856: 'SAM launch', 0x19bcc: 'drone-launcher tick',
     0x19c56: 'missile-site tick', 0x1980c: 'command-centre tick', 0x19912: 'drone tick', 0x1ac8c: 'strategy tick'}
r = s('hits', steps=steps, addrs=[f'${a:x}' for a in L])
show('after ')
print(r if not isinstance(r, dict) else '')
for k, v in (r.get('hits', r) if isinstance(r, dict) else {}).items() if False else []:
    pass
import json; print(json.dumps(r)[:3000])
s.close()
