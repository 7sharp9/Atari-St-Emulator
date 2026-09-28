import struct, sys
for p in sys.argv[1:]:
    R = open(p,'rb').read()
    print(p)
    for s in range(5):
        b = 0x580a6 + 32*s
        blk = list(R[b:b+32])
        sb = [struct.unpack('b', bytes([x]))[0] for x in blk]
        print(f" side {s} @{b:#x} peace(+6)={blk[6]:#04x} +15..+22 (signed) {sb[15:23]}")
