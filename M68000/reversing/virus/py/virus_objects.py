"""Model of Virus's object scatter: routine $236f8 (count D0+1, type D1) called nine times by the landscape
builder at $2336a, on the map $32a58 (one byte per terrain cell, low 5 bits = object type).
RNG ($2706e/$27072, 2x32 bit): a += b ; b = swap(old a); the random word is the high word of the old a.
Usage: python virus_objects.py <snap> <callcap.json> <level> [--break]
  snap: state the callcap was taken from (supplies the RNG state and $42a58); json: its memory delta
  (callcap of a stub  moveq #level,D0 / jsr $2336a / rts ); compares the map after the nine scatters.
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def find_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        d = os.path.dirname(d)
    return d

import virus_terrain as vt

SCATTER = [(0x120, 4), (0x80, 1), (0x100, 5), (0x300, 6), (0x180, 3), (0x100, 2), (0x70, 7), (0x60, 8), (0x50, 9)]

def main():
    snap, js, level = sys.argv[1], sys.argv[2], int(sys.argv[3])
    sys.path.insert(0, os.path.join(find_root(), 'tools'))
    import gfxview
    ram, _ = gfxview.load_ram(snap); r0 = bytes(ram)
    a, b = struct.unpack('>LL', r0[0x2706e:0x27076])
    S = list(struct.unpack('>1024h', r0[0xd0fa:0xd0fa + 2048]))
    v = vt.VARIANTS[level]
    edge = 0x900       # the scatter's own edge test; ($24756's patched #$a00 is not what decides it: 1778 vs 1777 on level 2)
    SC = list(SCATTER)
    if '--break-count' in sys.argv:       # control: first scatter one draw short (a metric on the set of cells is blind to a pure shift
        SC[0] = (SC[0][0] - 1, SC[0][1])   # except at the nine scatter boundaries)
    if '--break-order' in sys.argv:       # control: types 4 and 1 scattered in the other order
        SC[0], SC[1] = SC[1], SC[0]
    # height bytes as the builder wrote them
    H = {}
    def hbyte(cx, cy):
        m = vt.model_byte(cx << 8, cy << 8, S, v)
        return 0xd7 if m is None else m
    mp = bytearray(65536)
    for cnt, typ in SC:
        for _ in range(cnt + 1):
            r = a >> 16
            a, b = (a + b) & 0xffffffff, ((a >> 16) | ((a & 0xffff) << 16))
            y = r & 0xff00; x = (r & 0xff) << 8
            if x < edge and y < 0x900:
                d1 = 0x420
            else:
                d1 = ((hbyte(r & 0xff, r >> 8) << 3) + 0xfd68) & 0xffff
                if d1 & 0x8000: d1 -= 0x10000
            if d1 > 0x510 or d1 == 0x420:
                continue
            mp[r] = (mp[r] & 0xe0) | typ
    # RAM result: snapshot + callcap delta
    rr = bytearray(r0)
    for ad, _bf, af in json.load(open(js))['mem']:
        rr[ad] = af
    ram_map = rr[0x32a58:0x32a58 + 65536]
    both0 = sum(1 for i in range(65536) if mp[i] == 0 and ram_map[i] == 0)
    objs = [i for i in range(65536) if mp[i]]                        # model: cells holding a type 1..9
    rob = [i for i in range(65536) if 1 <= (ram_map[i] & 0x1f) <= 9]  # RAM: same (markers 10, 11, 12 excluded)
    same = sum(1 for i in objs if ram_map[i] == mp[i])
    print(f'level {level}: model object cells {len(objs)}, RAM object cells {len(rob)}, identical type at the same cell: {same}')
    print(' model-only cells', [hex(i) for i in objs if ram_map[i] != mp[i]][:8], ' RAM-only cells', [hex(i) for i in rob if mp[i] != ram_map[i]][:8])

main()
