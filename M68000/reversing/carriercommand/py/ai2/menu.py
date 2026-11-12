"""Click a title-menu button from c_mv.snap and report which branch sets $1244 and the starting owners.
usage: menu.py <snap> <dy> <steps> [out.snap]   (dy: pointer move before the click; 0 = 'Start Strategy Game')
Mouse bytes are sent one at a time (brief's IKBD workaround)."""
import sys, struct
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent)); from ccpaths import ROOT
sys.path.insert(0, str(ROOT / 'tools')); from stclient import StServer
snap, dy, steps = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
s = StServer(str(ROOT)); s('load', snapshot=snap)
def pkt(*b):
    for x in b:
        s('kbd', bytes=[x & 0xff]); s('step', n=3000)
if dy:
    pkt(0xf8, 0, dy); s('step', n=30000)
pkt(0xfa, 0, 0); s('step', n=30000); pkt(0xf8, 0, 0)
r = s('hits', steps=steps, addrs=['$fe72', '$fe7e', '$3ba8', '$3bec', '$3bc6'])
print({h['addr']: (h['count'], h['first']) for h in r['hits']})
own = s.read(0x69b40, 64)
print('$1244', s.read(0x1244, 1).hex(), '$446', s.read(0x446, 2).hex(), 'enemy', [i for i in range(64) if own[i] == 2],
      'player', [i for i in range(64) if own[i] == 1])
if len(sys.argv) > 4: s('save', path=sys.argv[4])
s.close()
