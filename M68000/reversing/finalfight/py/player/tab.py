import sys,os
root=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
T=int(sys.argv[1],16); n=int(sys.argv[2]); kind=sys.argv[3] if len(sys.argv)>3 else 'w'
for i in range(n):
    if kind=='w':
        v=int.from_bytes(rom[T+2*i:T+2*i+2],'big'); print('%d(byte %d) -> $%x'%(i,2*i,(T+v)&0xffffff))
    else:
        v=int.from_bytes(rom[T+4*i:T+4*i+4],'big'); print('%d(byte %d) -> $%x'%(i,4*i,v))
