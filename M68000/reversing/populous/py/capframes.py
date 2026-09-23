"""capframes.py <snap> <nframes> <out.bin>
Runs the emulator REPL from <snap>; for each of nframes frames captures RAM regions at entry to $db4c
(entity update) and at its return ($b7ce), writing a binary file of records:
  pre: [$36e78..$3d550) + [$21e0c..+92) + [$219b0..+4] ; post: same.   (see REGIONS)
If the game leaves $db4c (score screen), `u` gives up and the same state is dumped again: dedupe records
by the frame word $3c4c8 (endgame/brawlcheck.py does)."""
import subprocess,sys,os
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg import R, WORK as S
REGIONS=[(0x36e78,0x3d550-0x36e78),(0x21e0c,92),(0x219b0,4)]
RECLEN=sum(n for _,n in REGIONS)
def dumps(): return ''.join('m %x %d\n'%(a,n) for a,n in REGIONS)
if __name__=='__main__':
    snap,n,out=os.path.abspath(sys.argv[1]),int(sys.argv[2]),sys.argv[3]   # the emulator runs in R
    cmd=''
    for i in range(n): cmd+='u db4c 3000000\n'+dumps()+'u b7ce 3000000\n'+dumps()
    cmd+='q\n'
    env=dict(os.environ,ATARI_NOTRACE='1')
    p=subprocess.run(['dotnet','exec','bin/Debug/net8.0/M68000.dll','resume',snap,'repl','--disk-a',S+'/pop_auto.st'],
                     input=cmd,capture_output=True,text=True,cwd=R,env=env)
    bs=bytearray()
    for line in p.stdout.splitlines():
        t=line.split()
        if t and all(len(x)==2 and all(c in '0123456789abcdef' for c in x) for x in t):
            bs+=bytes(int(x,16) for x in t)
    print('bytes',len(bs),'records',len(bs)/RECLEN, 'reached', p.stdout.count('reached PC=$0000db4c'))
    open(out,'wb').write(bs)
