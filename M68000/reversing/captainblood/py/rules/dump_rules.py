"""Print one race's stream A as words. usage: uv run python reversing/captainblood/py/rules/dump_rules.py <race index> [max records]"""
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cbdata import *
b,vocab,races=load()
race=int(sys.argv[1]); mx=int(sys.argv[2]) if len(sys.argv)>2 else 10**9
def nm(t): return vocab[t-1][1] if 1<=t<=120 else f'?{t}'
def toks(p):
    out=[];i=0
    while i<len(p):
        if p[i]<=3: out.append(f'{nm(p[i])}={p[i+1]<<8|p[i+2]}'); i+=3
        else: out.append(nm(p[i])); i+=1
    return out
e=0
for n,(addr,h,f,p) in enumerate(records(b,races[race])):
    if n>=mx: break
    t=h&0xe0
    if t==0:
        # stream B masks
        k=len(toks(p)); 
        mb=races[race]['B']-BASE
        ms=[]
        for j in range(k):
            ei=e+j; base=mb+3*(ei//8); bit=7-ei%8
            m=[(b[base+x]>>bit)&1 for x in range(3)]
            ms.append(''.join(map(str,m)))
        print(f'{n:4d} PLAIN f={f:02x} '+' '.join(f'{w}[{m}]' for w,m in zip(toks(p),ms)))
        e+=k
    elif t==0x40:
        ws=[p[i]<<8|p[i+1] for i in range(0,len(p),2)]
        print(f'{n:4d} ACTION f={f:02x} '+(' '.join(('-' if w&0x8000 else '+')+str((-w)&0xffff if w&0x8000 else w) for w in ws) or 'EMPTY(end)'))
    else:
        ws=[p[i]<<8|p[i+1] for i in range(0,len(p),2)]
        print(f'{n:4d} COND{t:02x} f={f:02x} '+' '.join((('-' if w&0x8000 else '+')+str((-w)&0xffff if w&0x8000 else w)) for w in ws))
