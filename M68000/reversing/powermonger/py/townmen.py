"""townmen.py <ram> [lord ...]: each lord's house chain and the townsmen on it, as $34f2 walks it
(lord 2(A5) -> house $4f916+off, 10(house) first man, 24(man) next man, 8(house) next house), plus the
fields $34f2/$15282 test: side byte 5, flags byte 7 (bit6 group follower, bit7, bit4), mode 31 / arrival 30,
dwell 18, link46, cell.  Also the selected group's lead, men count and the lords' troops_field (8(lord)).
Repo root is derived from __file__; nothing here is machine specific."""
import struct, sys
R = open(sys.argv[1], 'rb').read()
w = lambda a: struct.unpack('>H', R[a:a+2])[0]
sw = lambda a: struct.unpack('>h', R[a:a+2])[0]
OBJ = 0x51b66


def man_line(off):
    r = OBJ + off
    return (f"man {off:#06x} (rec {off//50:3d}) side {R[r+5]} b7 {R[r+7]:#04x} mode {R[r+31]:#04x}/{R[r+30]:#04x} "
            f"dwell {w(r+18):#x} l46 {w(r+46):#x} grp42 {w(r+42):#x} home34 {w(r+34):#x} cell ({sw(r+8)>>8},{sw(r+10)>>8}) "
            f"tgt ({R[r+20]},{R[r+22]})")


def town(lord):
    L = 0x4e514 + 32*lord
    print(f"lord {lord} @{L:#x} side {R[L+5]} cell {(w(L+4)&63, (w(L+4)>>6)&127)} food {w(L+6)} troops_field(8) {w(L+8)} head house {w(L+2):#x}")
    h = w(L+2); n = 0; men = []
    while h and n < 50:
        A = 0x4f916 + h
        m = w(A+10); k = 0
        print(f"  house {h:#x} owner {R[A+5]} b6 {R[A+6]:#x} kind {R[A+7]} cell {(w(A+12)&63,(w(A+12)>>6)&127)} firstman {m:#x}")
        while m and k < 100:
            print("    " + man_line(m)); men.append(m); m = w(OBJ+m+24); k += 1
        h = w(A+8); n += 1
    return men


if __name__ == '__main__':
    lords = [int(x) for x in sys.argv[2:]] or [0, 1, 2]
    for l in lords:
        town(l)
    g = w(0x57fd2); A = 0x51538 + g
    print(f"sel group {g:#x} state {w(A)} men(-24) {w(A-24)} lead {w(A-12):#x} owner {sw(A-48)} tgt24 {w(A+24):#x} posture {w(A+60)} food {w(A+36)}")
    lead = OBJ + w(A-12)
    print(f"  lead rec: side {R[lead+5]} mode {R[lead+31]:#x}/{R[lead+30]:#x} dwell {w(lead+18):#x} l46 {w(lead+46):#x} cell ({sw(lead+8)>>8},{sw(lead+10)>>8})")
