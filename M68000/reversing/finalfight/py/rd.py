import sys,os,struct
root=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
ram=open(os.path.join(root,'scratchpad/finalfight/verify/ff_gameplay_ram.bin'),'rb').read()
def L(a,n,sz=4,mem=rom,base=0):
    out=[]
    for i in range(n):
        o=a-base+i*sz
        out.append(int.from_bytes(mem[o:o+sz],'big'))
    return out
if __name__=='__main__':
    kind=sys.argv[1]; a=int(sys.argv[2],16); n=int(sys.argv[3]); sz=int(sys.argv[4]) if len(sys.argv)>4 else 4
    if kind=='rom': v=L(a,n,sz)
    else: v=L(a,n,sz,ram,0xff0000)
    for i,x in enumerate(v): print('%06x: %0*x'%(a+i*sz,sz*2,x))
