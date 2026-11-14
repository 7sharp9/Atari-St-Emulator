"""Virus landscape renderer, stage 1: the visible 11x10 vertex grid built by $24098 (the 'grid builder').
Model of the first block ($240c0..$24164): for each of 10 rows (depth step $100) and 11 columns (cell
width $100) around the camera it looks the height up ($24754), subtracts the camera height and
projects  sx = (dx<<8)/dz + $a0,  sy = (dy<<8)/dz + $46  (one divs each, no reciprocal table), writing
(sx,sy) at -(A6) from $2758c (52 bytes per row) and the colour/type word at -(A3) from $276e0 (26 per row).
Usage: python virus_grid.py <snap> <callcap.json> [--break]
  callcap.json: memory delta of  callcap 24098  from the snapshot.  --break: use $e00 -> $f00 as the first row's depth.
"""
import json, os, struct, sys

def find_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        d = os.path.dirname(d)
    return d

def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

def divs(num32, den):
    """68000 DIVS.W: 32-bit dividend / 16-bit divisor; returns the new low word of D (overflow leaves the dividend)."""
    num32 = struct.unpack('>l', struct.pack('>L', num32 & 0xffffffff))[0]
    den = s16(den)
    q = abs(num32) // abs(den)
    if (num32 < 0) != (den < 0): q = -q
    if q > 32767 or q < -32768:
        return num32 & 0xffff
    return q & 0xffff

def main():
    root = find_root(); sys.path.insert(0, os.path.join(root, 'tools'))
    import gfxview
    ram, _ = gfxview.load_ram(sys.argv[1]); r = bytearray(ram)
    r0 = bytes(r)
    for a, _b, af in json.load(open(sys.argv[2]))['mem']:
        r[a] = af
    brk = '--break' in sys.argv
    camx, camy, camz = struct.unpack('>3h', r0[0x270ce:0x270d4])
    lvl = struct.unpack('>H', r0[0x32a4e:0x32a50])[0]
    edge = 0x900 if lvl == 0 else 0xa00
    tbl = r0[0x246ba:0x246ba + 0x100]

    def lookup(x, z):                       # $24754: (D1 height, D3 type); x<edge and z<$900 = launch-pad table
        if x < edge and z < 0x900:
            return 0x420, tbl[((((z << 3) & 0xfc00) + x) & 0xffff) >> 8]
        b = r0[0x42a58 + (x >> 8) + (z & 0xff00)]
        d1 = s16((b << 3) + 0xfd68)
        if d1 <= 0x510: d3 = ((d1 >> 3) & 3) + 9
        elif d1 >= 0x560: d3 = 8
        else: d3 = 7
        return d1, d3

    d6 = (camx - 0x480) & 0xff00; d7 = (camz - 0x400) & 0xff00
    d0r = s16(-(camx - d6)); d2 = s16(-(camz - d7) + (0xf00 if brk else 0xe00))
    objmap = lambda x, z: r0[0x32a58 + (((x >> 8) + z) & 0xffff)]  # as the code: (D6>>8)+D7, D7 = z (already multiple of $100)
    a6 = 0x2758c; a3 = 0x276e0
    exp = {}
    for row in range(10):
        d0 = d0r; x6 = d6
        for col in range(11):
            h, typ = lookup(x6, d7)
            a3 -= 2; exp[a3] = typ                     # move.w D3,-(A3)
            ob = objmap(x6, d7)
            if ob & 0x20:                              # flagged cell: colour word from the $244b0 table by height
                exp[a3] = struct.unpack('>H', r0[0x244b0 + ((h >> 2) & 0xe):][:2])[0]
            dy = s16(h - camy)
            sx = (s16(divs(s16(d0) << 8, d2)) + 0xa0) & 0xffff
            sy = (s16(divs(dy << 8, d2)) + 0x46) & 0xffff
            a6 -= 4; exp[a6] = sx; exp[a6 + 2] = sy
            d0 = s16(d0 + 0x100); x6 = (x6 + 0x100) & 0xffff
        a6 -= 8; a3 -= 4
        d2 = s16(d2 + 0x100); d7 = (d7 + 0x100) & 0xffff
    ok = bad = 0; badl = []
    for a, v in sorted(exp.items()):
        got = struct.unpack('>H', bytes(r[a:a + 2]))[0]
        if got == v: ok += 1
        else: bad += 1; badl.append((hex(a), v, got))
    if os.environ.get('GRIDDBG'):
        for a,v,g in badl[:20]: print(a,v,g)
    print(f'camera x,y,z = {camx},{camy},{camz}  level {lvl}: grid words (110 vertices x2 + 110 type words) match {ok}/{ok+bad}', len(badl))

main()
