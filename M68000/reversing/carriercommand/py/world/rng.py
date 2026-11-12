# Carrier Command RNG at $192bc (also $203ac): 64-bit state at $1230 (D0:D1); returns D0 (new first long).
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
M=0xffff
def step(A,B):
    # add.w D0,D0
    lo=(A&M)*2; X=lo>>16; lo&=M; D2=lo
    A=(A&0xffff0000)|lo
    # addx.w D1,D0 ; move.w D2,D1
    s=(A&M)+(B&M)+X; X=s>>16; A=(A&0xffff0000)|(s&M)
    B=(B&0xffff0000)|D2
    # swap both
    A=((A<<16)|(A>>16))&0xffffffff; B=((B<<16)|(B>>16))&0xffffffff
    D2=A&M
    s=(A&M)+(B&M)+X; A=(A&0xffff0000)|(s&M)
    B=(B&0xffff0000)|D2
    A=((A<<16)|(A>>16))&0xffffffff; B=((B<<16)|(B>>16))&0xffffffff
    return A,B
if __name__=='__main__':
    A,B=step(0x01234567,0x89abcdef); print(hex(A),hex(B))
