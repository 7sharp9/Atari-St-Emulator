"""Character data tables: max health per difficulty rank (32 words), defence class (32 bytes at +$40), damage rows (32 bytes each at +$60+row*32)."""
import sys,os
root=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
BASE={'guy':0x10ffa,'cody':0x12b80,'haggar':0x14f4e}  # index 0 = Guy, 1 = Cody, 2 = Haggar
def rows(ch,n=0x20):
    b=BASE[ch]
    print(ch,'max health by rank:',sorted(set(int.from_bytes(rom[b+2*i:b+2*i+2],'big') for i in range(32))))
    print(ch,'defence class by rank (+$40):',sorted(set(rom[b+0x40+i] for i in range(32))))
    for r in range(n):
        vals=[rom[b+0x60+r*32+i] for i in range(32)]
        print('row %02x (off %04x): %s%s'%(r,r*32,' '.join('%02x'%v for v in vals[:8]),' ... all-equal' if len(set(vals))==1 else ' varies: '+' '.join('%02x'%v for v in vals)))
if __name__=='__main__':
    rows(sys.argv[1],int(sys.argv[2],16) if len(sys.argv)>2 else 16)
