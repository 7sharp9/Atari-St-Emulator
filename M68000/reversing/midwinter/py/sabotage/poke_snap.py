"""poke_snap.py in.snap out.snap addr:width:value ... -- labelled pokes applied in stserver, saved as a snapshot."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')): root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, 'tools'))
from stclient import StServer
DISK = os.path.join(root, 'scratchpad', 'midwinter', 'zuul067.st')

def poke_snap(src, dst, pokes):
    s = StServer(root)
    s('load', snapshot=os.path.abspath(src), disk=DISK)
    for a, w, v in pokes:
        s('poke', addr=a, width=w, value=v)
    s('save', path=os.path.abspath(dst))
    s('shutdown')
    s.close()

if __name__ == '__main__':
    pokes = [tuple(int(x, 16) for x in p.split(':')) for p in sys.argv[3:]]
    poke_snap(sys.argv[1], sys.argv[2], pokes)
    print('saved', sys.argv[2], ['$%x.%d=$%x' % p for p in pokes])
