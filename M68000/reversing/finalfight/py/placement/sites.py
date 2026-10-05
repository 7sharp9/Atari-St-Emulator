# every allocator call site (jsr $38ce..$39fa etc.), the handler range that contains it, and the constants stored in the new record's tag/kind/+20/+21
import sys,subprocess,re,bisect
from rom import *
import os
from callers import callers
ALLOC={0x3892:'2',0x38ce:'6',0x390a:'4',0x3946:'8',0x3982:'a',0x39be:'12',0x39fa:'14',0x3a52:'eff-owner',0x3a96:'eff'}
def tables():
    t={}
    def add(base,n,name):
        for i in range(n): t[l(base+4*i)]='%s k%d'%(name,i)
    add(0x5872,60,'pool8'); add(0x598c,6,'pool6'); add(0x59ce,19,'poolA'); add(0x5a52,8,'pool4')
    for i,a in enumerate((0x21cec,0x2813a,0x2a310,0x2ccac,0x3136c,0x3514c,0x389b8,0x3c446,0x3c48e)): t[a]='pool2 k%d'%i
    t[0x5a55a]='pool12 k0'; t[0x563dc]='pool14 k0'; t[0x56e44]='pool14 k1'
    for a,n in ((0x61e24,'camera-update'),(0x6026,'placement'),(0x5aea,'stage-script'),(0x5a934,'prop-drop'),(0x6241e,'camera2-update'),(0x6396,'code $6396-$1a1f0 (hit resolution, camera, player states, helpers)'),(0x4400,'debris/effect spawners $4400-$4700'),(0x4700,'code $4700-$5a1a?'),(0x5a72,'effects')): t[a]=n
    return t
T=tables(); K=sorted(T)
def owner(a):
    i=bisect.bisect_right(K,a)-1
    return T[K[i]],K[i]
def dis(a,n):
    out=subprocess.run([sys.executable,os.path.join(root,'tools/disassemble.py'),'--rom',os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'--base','0','--linear','%x'%a,str(n)],capture_output=True,text=True).stdout
    return out
if __name__=='__main__':
    for t,name in ALLOC.items():
        if name.startswith('eff'): continue
        for a,k in sorted(callers(t)):
            o,base=owner(a)
            txt=dis(a,26)
            kinds=re.findall(r'move\.b #\$([0-9a-f]+),19\(A4\)',txt)
            k2=re.findall(r'move\.w #\$([0-9a-f]+),18\(A4\)',txt)
            c20=re.findall(r'move\.b #\$([0-9a-f]+),20\(A4\)',txt)
            c21=re.findall(r'move\.b #\$([0-9a-f]+),21\(A4\)',txt)
            print('pool %-3s site %06x in %-14s (from %06x) kind=%s tagkind=%s +20=%s +21=%s'%(name,a,o,base,kinds[:1],k2[:1],c20[:1],c21[:1]))
