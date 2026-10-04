"""RIDER 3b: a from-disassembly reconstruction of PowerMonger's grid-corner
projector $fecc / $ff7c / $fe8e, for differential testing against the real 68000
via the emulator's `callcap` primitive.

Transcribed line-for-line from the disasm (pm78_settle.ram, base 0):
  $fecc  outer/inner double loop over the (2*half+1)^2 vertex grid
  $fe8e  HBIAS = min control-plane byte over the window  -> word[$fec4]
  $ff7c  perspective divide (integer muls/divs, EYE/HORIZON constants)

All inputs are read from the RAM image exactly where the ROM reads them, so the
only "reconstruction" is the arithmetic, not the data.
"""
import struct, sys, json

def s16(b): return b - 0x10000 if b >= 0x8000 else b
def s32(b): return b - 0x100000000 if b >= 0x80000000 else b

class Ram:
    def __init__(s, path): s.r = bytearray(open(path, 'rb').read())
    def bu(s, a): return s.r[a]
    def bs(s, a): return s16(s.r[a] << 8) >> 8 if s.r[a] >= 0x80 else s.r[a]
    def wu(s, a): return struct.unpack_from('>H', s.r, a)[0]
    def ws(s, a): return struct.unpack_from('>h', s.r, a)[0]
    def poke_w(s, a, v): struct.pack_into('>H', s.r, a, v & 0xFFFF)

def muls(a, b):
    """68k MULS: signed 16x16 -> 32."""
    return s32((s16(a & 0xFFFF) * s16(b & 0xFFFF)) & 0xFFFFFFFF)

def divs_w(dividend32, divisor16):
    """68k DIVS: 32/16 -> 16q:16r. Round toward zero (C semantics)."""
    d = s16(divisor16 & 0xFFFF)
    n = s32(dividend32 & 0xFFFFFFFF)
    if d == 0: raise ZeroDivisionError
    q = int(n / d)                       # trunc toward zero
    return s16(q & 0xFFFF)               # (overflow wraps; not expected here)

def hbias(ram, a1, half, strideA1):
    """$fe8e"""
    d3 = 127
    for _r in range(-half, half + 1):
        p = a1
        for _c in range(-half, half + 1):
            d0 = ram.bu(p); p += 1
            if d0 < d3: d3 = d0
        a1 += (2 * half + 1) + strideA1     # adda.w $fdee after each row  (=64 - width... see note)
    return d3

def ff7c(rx, ry, z, eye, horizon):
    """$ff7c: in D0=rx D2=ry D1=z ; out (sx, sy) words"""
    d3 = eye
    d4 = eye
    d3 = s16((d3 - ry) & 0xFFFF)            # sub.w D2,D3   -> depth
    d0 = muls(d4, rx)                       # muls D4,D0
    d0 = divs_w(d0, d3)                     # divs D3,D0    -> sx
    d1 = s16((z - horizon) & 0xFFFF)        # sub.w $ff96,D1
    d1 = muls(d4, d1)                       # muls D4,D1
    d1 = divs_w(d1, d3)                     # divs D3,D1
    d1 = s16((d1 + horizon) & 0xFFFF)       # add.w $ff96,D1 -> sy
    return d0, d1

def project(ram, cam_x=None, cam_y=None):
    yaw   = ram.wu(0xff9a)
    zoom  = ram.ws(0xff9c)
    half  = ram.ws(0xfdec)
    strA1 = ram.ws(0xfdee)
    strA0 = ram.ws(0xfdea)
    off   = ram.ws(0x57ffc)
    eye   = ram.ws(0xff98)
    horiz = ram.ws(0xff96)
    if cam_x is None: cam_x = ram.wu(0x4bb3a)
    if cam_y is None: cam_y = ram.wu(0x4bb3c)

    s1 = ram.ws(0x13f8a + (yaw * 2))            # D7 hi  (sin term)
    s2 = ram.ws(0x13f8a + 128 + (yaw * 2))      # D7 lo  (cos term)

    # A1 = $3f86c + camX - off + (camY - off)*64   (control plane, stride 64)
    a1_base = 0x3f86c + (cam_x - off) + ((cam_y - off) << 6)

    # HBIAS over the window
    hb = 127
    for gr in range(2 * half + 1):
        row = a1_base + gr * 64
        for gc in range(2 * half + 1):
            v = ram.bu(row + gc)
            if v < hb: hb = v

    out = {}                                    # (gr,gc) -> (X, Y)
    for gr in range(2 * half + 1):
        d6 = gr - half                          # row
        a1 = a1_base + gr * 64
        for gc in range(2 * half + 1):
            d5 = gc - half                      # col
            wx = muls(d5, zoom)                 # col*zoom
            wy = muls(d6, zoom)                 # row*zoom
            h = ram.bu(a1 + gc)                 # ext.w (A1)+  (heights are 0..255, unsigned here)
            z = s16(((muls(s16((h - hb) & 0xFFFF), zoom)) & 0xFFFF)) >> 4   # lsr.w #4 on low word
            # rotate
            d3 = muls(wx, s1)
            d4 = muls(wy, s1)
            d0 = muls(wx, s2)
            d2 = muls(wy, s2)
            d0 = s32((d0 - d4) & 0xFFFFFFFF)
            d2 = s32((d2 + d3) & 0xFFFFFFFF)
            d0 = s32((d0 * 2) & 0xFFFFFFFF)     # add.l D0,D0
            d2 = s32((d2 * 2) & 0xFFFFFFFF)
            rx = s16((d0 >> 16) & 0xFFFF)       # swap D0 -> high word
            ry = s16((d2 >> 16) & 0xFFFF)
            sx, sy = ff7c(rx, ry, z & 0xFFFF, eye, horiz)
            X = s16((sx + 0x80) & 0xFFFF)       # addi.w #$80
            Y = s16((-sy + 0x7c) & 0xFFFF)      # neg.w D1 ; addi.w #$7c
            out[(gr, gc)] = (X & 0xFFFF, Y & 0xFFFF)
    return out, half

def stored_corners(ram, half):
    """Read $3f364: word pairs (X,Y), row stride 64 bytes."""
    out = {}
    for gr in range(2 * half + 1):
        base = 0x3f364 + gr * 64
        for gc in range(2 * half + 1):
            X = ram.wu(base + gc * 4)
            Y = ram.wu(base + gc * 4 + 2)
            out[(gr, gc)] = (X, Y)
    return out

if __name__ == '__main__':
    path = sys.argv[1]
    cx = int(sys.argv[2]) if len(sys.argv) > 2 else None
    cy = int(sys.argv[3]) if len(sys.argv) > 3 else None
    ram = Ram(path)
    recon, half = project(ram, cx, cy)
    if cx is None:
        stored = stored_corners(ram, half)
        bad = [(k, recon[k], stored[k]) for k in recon if recon[k] != stored[k]]
        print(f"{path}: {len(recon)} vertices, {len(bad)} mismatch vs stored $3f364")
        for k, rc, st in bad[:12]:
            print("   ", k, "recon", rc, "stored", st)
    else:
        print(json.dumps({f"{gr},{gc}": list(v) for (gr, gc), v in recon.items()}))
