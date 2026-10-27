"""Print sabotage-relevant state of a snapshot: 264(A6), current char, char record, its site."""
import sys, os, struct
here = os.path.dirname(os.path.abspath(__file__))
r = here
while not os.path.exists(os.path.join(r, 'tools', 'rdis.py')):
    r = os.path.dirname(r)
sys.path.insert(0, os.path.join(r, 'tools'))
from disassemble import ram_from_snap
TYPES = ['Hut','CableCar','Pylon','Garage','Bunker','House','Church','Store','Police','Magazine','HeatMine',
         'Warehouse','Synth','Factory','Radio','HQ','Ruin']
def w(ram, a): return struct.unpack_from('>H', ram, a)[0]
def l(ram, a): return struct.unpack_from('>I', ram, a)[0]
def records(ram):
    a = 0x2a150; out = []
    for i in range(2000):
        k = ram[a]; n = k & 0x7f
        if a >= 0x2b16a: break
        out.append((i, a, k, ram[a+1], w(ram, a+2), w(ram, a+4), [w(ram, a+6+2*j) for j in range(n)]))
        a += 6 + 2*n
    return out
if __name__ == '__main__':
    ram = ram_from_snap(sys.argv[1])
    A6 = 0x2c376
    print('264(A6)=%04x cur=%d clock=%d 24b7a=%04x 14dfc=%04x 25046=%04x' % (w(ram, A6+264), w(ram, A6+96), w(ram, 0x2c172), w(ram,0x24b7a), w(ram,0x14dfc), w(ram,0x25046)))
    print('2c188:', ram[0x2c188:0x2c188+17].hex(), '24e8c', '%04x' % w(ram, 0x24e8c), '2c186', '%04x' % w(ram, 0x2c186))
    team = []
    a = 0x2b16c
    while ram[a] < 0x80: team.append(ram[a]); a += 1
    print('team', team)
    recs = {r[1]: r for r in records(ram)}
    for c in ([int(x) for x in sys.argv[2:]] or team):
        b = 0x2b194 + c*0x4a
        p = l(ram, b+52)
        print('char %d @%x: +0=%02x morale=%d +15=%02x +32=%d pos=%x,%x +52=%x +56..64=%s +72=%d' % (
            c, b, ram[b], ram[b+1], ram[b+15], w(ram, b+32), l(ram, b+34)>>8, l(ram, b+38)>>8, p,
            ram[b+56:b+65].hex(), ram[b+72]))
        if p in recs:
            i, a, k, b1, x, y, bl = recs[p]
            print('   node #%d kind=%02x b1=%02x (%d,%d) bldgs=%s' % (i + 1, k, b1, x, y,
                  ['%04x:%s' % (v, TYPES[(v >> 8) & 0x1f] if ((v>>8)&0x1f) < 17 else '?') for v in bl]))
