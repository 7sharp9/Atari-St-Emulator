# gate: state 16 (wait at slot): fighter within the 27d30 tolerance of its slot (146(A6)) around its target player 144/148
import rec, collections, sys
DX=[-0x60,-0x80,-0x60,-0x40,0x60,0x80,0x60,0x40]; DY=[0x12,0,-0x16,0,0x12,0,-0x16,0]
def s16(v): return v-65536 if v>=32768 else v
tot=ok=0; slots=collections.Counter(); first_ok=first_tot=0
for fn in sys.argv[1:]:
    fs=rec.load(fn)[1:]
    for pi,f in enumerate(fs):
        for i,r in enumerate(f.p2):
            if not r[0] or r[19]!=0 or r[3]!=16: continue
            t=rec.u16(r,144); p=f.pl[0] if t==1 else f.pl[1]
            s=rec.u16(r,146); slots[s]+=1
            dx=(rec.u16(p,6)+DX[s]-rec.u16(r,6)+8)&0xffff
            dy=(rec.u16(p,14)-rec.u16(p,90)+DY[s]-rec.u16(r,10)+4)&0xffff
            good = dx<=0x10 and dy<=0x10
            tot+=1; ok+=good
print('state 16 frames at slot (27d30 tolerance): %d of %d'%(ok,tot),'slot ids',dict(sorted(slots.items())))
