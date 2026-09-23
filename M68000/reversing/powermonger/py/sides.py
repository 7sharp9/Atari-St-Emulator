"""Side totals, ratio, leaders, command slots, the local captain group of a PowerMonger RAM image."""
import struct, sys
R=open(sys.argv[1],'rb').read()
w=lambda a: struct.unpack('>H',R[a:a+2])[0]
sw=lambda a: struct.unpack('>h',R[a:a+2])[0]
loc=w(0x57ffe)
print(f"local side {loc}  ratio $57fce={w(0x57fce)}  pending cmd $57fd4={w(0x57fd4):#x}  $57fd2={w(0x57fd2):#x} land $580a4={w(0x580a4)}  tick $2df72={struct.unpack('>I',R[0x2df72:0x2df76])[0]}")
print(" $57fba field/reserve per side:", [(w(0x57fba+4*s), w(0x57fba+4*s+2)) for s in range(5)])
for i in range(64):
    b=0x4e514+32*i
    if R[b]==0 and w(b+4)==0: continue
    c=w(b+4); print(f" leader {i:2d} side {R[b]} cell ({c&63:2d},{(c>>6)&127:3d}) food {w(b+6):4d} field {w(b+8):3d} loy {sw(b+14):4d} goods {list(R[b+24:b+32])}")
for s in range(5):
    a=0x58016+6*s; print(" cmd slot",s,list(R[a:a+6]))
g=0x51538+loc*0x13c
print(" local group rec: owner word +28 =",sw(g+28)," +0 flag",hex(struct.unpack('>I',R[g:g+4])[0]))
