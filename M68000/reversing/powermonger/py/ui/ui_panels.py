"""Decode every PowerMonger info panel opener in $9000..$b000: template grid (as $a91a expands it)
and the formatter table (A6) the '@' runs index.  python ui_panels.py [ram]  (default m1_s0.ram)."""
import os, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
R = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT/'scratchpad/pm123/win/m1_s0.ram').read_bytes()
def w(a): return (R[a]<<8)|R[a+1]
def l(a): return (w(a)<<16)|w(a+2)
codes=[]; a=0xa99c
while R[a]: codes.append(R[a]); a+=1
MAP={c:R[0xa99c+i+25] for i,c in enumerate(codes)}
def expand(t):
    out=bytearray(R[t:t+2]); p=t+2
    while R[p]:
        b=R[p]; p+=1
        if b&0x80 and b in MAP: b=MAP[b]
        out.append(b)
    return out
OPEN={ # opener: (name, template, formatter table)
 0x9036:('captain info (masterca)',0x921a,0x905a),
 0x9656:('click_st',0x9712,0x9672),
 0x9806:('click_eq',0x9878,0x9822),
 0x98ec:('click_ob',0x9954,0x9908),
 0x99ac:('click_pi',0xa0d4,0x99c8),
 0x99e0:('click_an',0xa082,0x99fc),
 0x9a38:('click_ho',0x9e76,0x9a5c),
 0x9c16:('click_pe',0xa328,0x9c32),
 0xa46c:('click_sp',0xa52c,0xa488),
 0xa5d8:('click_mi',0xa658,0xa5f4),
 0xa738:('click_tr',0xa7f8,0xa790),
}
for op,(name,t,tab) in OPEN.items():
    g=expand(t); wd=g[0]*4; h=g[1]; body=g[2:]
    runs=[]; i=0
    while i<len(body):
        if body[i]==0x40:
            j=i
            while j<len(body) and body[j]==0x40: j+=1
            runs.append((i,j-i)); i=j
        else: i+=1
    print(f"== opener ${op:x} {name}: template ${t:x} {wd}x{h} cells, table ${tab:x}, {len(runs)} '@' runs")
    for r in range(h):
        print('   '+''.join(chr(x) if 32<=x<127 else '.' for x in body[r*wd:(r+1)*wd]))
    for k,(off,n) in enumerate(runs):
        tw=w(tab+2*k)
        print(f"   run {k}: row {off//wd} col {off%wd} len {n} -> formatter ${tab+tw:x}")
