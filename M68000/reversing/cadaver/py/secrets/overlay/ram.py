import sys, struct
sys.path.insert(0, 'tools')
from gfxview import load_ram
def load(snap='scratchpad/cadaver/gameplay_empire.snap'):
    ram,_ = load_ram(snap); return ram
def hexdump(ram, a, n, w=16):
    for i in range(0,n,w):
        b = ram[a+i:a+i+w]
        print('$%06x  %s  %s' % (a+i, ' '.join('%02x'%x for x in b), ''.join(chr(x) if 32<=x<127 else '.' for x in b)))
if __name__=='__main__':
    ram = load(sys.argv[3] if len(sys.argv)>3 else 'scratchpad/cadaver/gameplay_empire.snap')
    hexdump(ram, int(sys.argv[1],16), int(sys.argv[2],0))
