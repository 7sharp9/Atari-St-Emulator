"""Gate: the falling-infection record kind (handler $205be, Infection_DropFall) predicted tick by tick.

    uv run python gate_infection_fall.py <pool_capture.json> [--break-gravity] [--break-ground] [--break-cell]

Model of one walker pass ($1fa72) over a record (x, y, z, vx, vy, vz, life, handler):
  life -= 1; life < 0 -> removed;  else pos += vel;  vy += gravity $32a3a;  h = ground height under (x, z)
  ($24754: pad cell $420 when x and z < $900, else height map byte * 8 + $fd68);  h - y < 0 (signed word, the
  handler's `cmp.w D5,D1 / bpl`) -> lands: water (h >= $560, type 8) splashes, otherwise Infection_Plant ($205f6)
  sets bit 5 of the object-map cell ((x + $80) >> 8, (z + $80) >> 8) when the ground at the next cell corner
  ((x & $ff00) + $100, (z & $ff00) + $100) is land (<= $510, not $420).  The record is then removed.
Checks, over the capture (records with the handler at frame k, successor looked for at frame k+1):
  survive : the model says it stays; the exact 18 bytes are in frame k+1's pool.
  vanish  : the model says it is removed (life or landing); no record in frame k+1 is the predicted one.
  plant   : on a predicted land plant, bit 5 of the model cell is set in the reconstructed map at frame k+1;
            on a predicted no-plant landing, the cell's bit 5 did not change.
Controls: --break-gravity (gravity + 1), --break-ground (ground height + $20), --break-cell (the cell one column over).
"""
import json, struct, sys

H = 0x205be


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def height(hmap, x, z):
    x &= 0xffff; z &= 0xffff
    if x < 0x900 and z < 0x900:
        return 0x420
    return s16(hmap[(x >> 8) + (z & 0xff00)] * 8 + 0xfd68)


def main():
    cap = json.load(open(sys.argv[1]))
    bg = '--break-gravity' in sys.argv
    bgr = '--break-ground' in sys.argv
    bc = '--break-cell' in sys.argv
    hmap = bytes.fromhex(cap['hmap'])
    rows = cap['rows']
    mp = bytearray(bytes.fromhex(cap['map0']))
    maps = []                     # map before frame k's walker (= after frame k-1's), reconstructed
    for r in rows:
        for i, v in r['mapdiff']:
            mp[i] = v
        maps.append(bytes(mp))
    n_s = ok_s = n_v = ok_v = n_pl = ok_pl = n_np = ok_np = n_life = n_water = 0
    land_h = []
    first_life = {}
    for k in range(len(rows) - 1):
        a, b = rows[k], rows[k + 1]
        g = s16(int(a['g'], 16)) + (1 if bg else 0)
        pa = bytes.fromhex(a['pool']); pb = bytes.fromhex(b['pool'])
        nxt = {pb[18 * i:18 * i + 18] for i in range(b['n'])}
        for i in range(a['n']):
            rec = pa[18 * i:18 * i + 18]
            x, y, z, vx, vy, vz, life = struct.unpack('>7h', rec[:14])
            if struct.unpack('>I', rec[14:])[0] != H:
                continue
            life -= 1
            if life < 0:
                n_life += 1                             # removed by the walker before the handler runs
            else:
                x2, y2, z2 = (x + vx) & 0xffff, (y + vy) & 0xffff, (z + vz) & 0xffff
                vy2 = (vy + g) & 0xffff
                h = height(hmap, x2, z2) + (0x20 if bgr else 0)
                new = struct.pack('>7h', *map(s16, (x2, y2, z2, vx, vy2, vz, life))) + rec[14:]
                lands = s16(h - s16(y2)) < 0
                if not lands:
                    n_s += 1; ok_s += new in nxt
                else:
                    n_v += 1; ok_v += new not in nxt
                    water = h >= 0x560
                    n_water += water
                    if not water:
                        cx = ((x2 + 0x80) & 0xffff) >> 8; cz = (z2 + 0x80) & 0xff00
                        if bc: cx = (cx + 1) & 0xff
                        cell = cx + cz
                        h2 = height(hmap, (x2 & 0xff00) + 0x100, (z2 & 0xff00) + 0x100)
                        plant = not (h2 > 0x510 or h2 == 0x420)
                        before = maps[k][cell] & 0x20; after = maps[k + 1][cell] & 0x20
                        if plant:
                            n_pl += 1; ok_pl += after != 0
                        else:
                            n_np += 1; ok_np += after == before
                        land_h.append((k, x2, z2, h, plant, before, after))
    # life-expiry removals: a record whose life hit 0 (pool walker removes it before the handler)
    print(f'records by life expiry (not scored): {n_life}; landings on water (splash, no plant): {n_water}')
    print(f'survive: {ok_s}/{n_s}   vanish (landing): {ok_v}/{n_v}   plant set: {ok_pl}/{n_pl}   '
          f'no-plant unchanged: {ok_np}/{n_np}')
    new_bits = sum(1 for l in land_h if l[4] and l[5] == 0)
    print(f'  of the {n_pl} planting landings, {new_bits} found the cell clear before (bit 5 newly set: {sum(1 for l in land_h if l[4] and l[5]==0 and l[6])}/{new_bits})')
main()
