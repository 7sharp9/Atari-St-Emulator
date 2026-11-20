"""analyze.py <capture.json> ...   Gate for the Virus depth buckets (README 'The renderer'), from capture.py output.
For every captured frame it
  1. parses the ten bucket lists as they stand at the painter's entry $24098 (record size from the draw routine's long)
     and checks the parse ends exactly on each list's end pointer;
  2. predicts the object-pool dot records: every post-walk object inside the window (x - (camx-$580)) & $ffff < $b00,
     (z - (camz-$500)) & $ffff < $a00, camera = $270ce at the walker's entry, goes to bucket (z-camz+$500)>>8 with
     sx = ((x-camx)<<8)/(z-camz+$e00)+$a0, sy = ((y-camy)<<8)/depth+$46, as one record or a shadow+sprite pair
     (the shadow record $16fb4 first) -- and walks each bucket's dot records against that list in pool order;
  3. does the same with a wrong bucket rule (control) and prints the counts.
"""
import json, struct, sys, collections

DOTS = {0x16fb4, 0x16ff4, 0x17044, 0x1709c, 0x170f4, 0x1714c, 0x171a4, 0x171fc, 0x17254, 0x172ac, 0x17304, 0x1735c, 0x173b4}
SIZE = {0x26222: 32, 0x261d2: 32, 0x26278: 14, 0x2620e: 4, 0x22a64: 16}
SHADOW = 0x16fb4
MODEL_OBJ = {0x2097a, 0x20882, 0x208f4}      # object handlers whose tail is the 32-byte model record ($1fbbc), not a dot
MODEL_ROUTINES = {0x26222, 0x261d2}

def s16(v): return v - 0x10000 if v & 0x8000 else v

def divs(a, b):                      # 68000 divs: truncates toward zero
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q

def parse(hexs):
    bb = bytes.fromhex(hexs); p = 0; recs = []
    while p < len(bb):
        r = struct.unpack('>L', bb[p:p + 4])[0]
        sz = 8 if r in DOTS else SIZE.get(r)
        if sz is None or p + sz > len(bb): return recs, False
        recs.append((r, bb[p:p + sz])); p += sz
    return recs, True

def pool(hexs, size):
    bb = bytes.fromhex(hexs)
    return [bb[i:i + size] for i in range(0, len(bb), size)]

def project(x, y, z, cam, kind):
    cx, cy, cz = cam
    dx = s16((x - cx) & 0xffff); dy = s16((y - cy) & 0xffff)
    depth = s16((z - cz + 0xe00) & 0xffff)
    return dx, dy, depth

def predict(frame, rule):
    cx, cy, cz = frame['cam_obj']
    out = []                         # (bucket, sx, sy, obj index)
    for i, r in enumerate(pool(frame['obj_walked'], 18)):
        x, y, z = struct.unpack('>3h', r[:6])
        if ((x - (cx - 0x580)) & 0xffff) >= 0xb00: continue
        d2 = (z - (cz - 0x500)) & 0xffff
        if d2 >= 0xa00: continue
        depth = (d2 + 0x900) & 0xffff
        dx = s16((x - cx) & 0xffff) - 0x580 + 0x580   # D0 - A0 - $580 = x - camx
        dx = s16((x - cx) & 0xffff); dy = s16((y - cy) & 0xffff)
        sx = divs(dx << 8, depth) + 0xa0; sy = divs(dy << 8, depth) + 0x46
        if struct.unpack('>L', r[14:18])[0] in MODEL_OBJ: continue
        out.append((rule(d2), s16(sx & 0xffff), s16(sy & 0xffff), i, struct.unpack('>L', r[14:18])[0]))
    return out

RULES = {
    'true  (z-camz+$500)>>8': lambda d2: d2 >> 8,
    'ctl A shifted by $100':   lambda d2: ((d2 + 0x100) >> 8),
    'ctl B reversed 9-b':      lambda d2: 9 - (d2 >> 8),
    'ctl C (>>9, half width)': lambda d2: d2 >> 9,
}


def clamp_bucket(depth):
    """The model records' rule ($1fbe0, $2165e, $258be, $23d6a): ((depth - $900) >> 5) & $fff8, then 0 if negative or $48 if >= $50."""
    d5 = (s16((depth - 0x900) & 0xffff) >> 5) & 0xfff8
    if d5 < 0x50: return d5 >> 3
    return 0 if d5 & 0x8000 else 9

def model_checks(fr, tot):
    """Every 32-byte model record's bucket follows its own depth word (+30) by the clamp; every object model record
    (handlers in MODEL_OBJ) and every in-window actor has a record with its (dx, dy, depth)."""
    cx, cy, cz = fr['cam']; recs32 = []
    for b in range(10):
        recs, _ = parse(fr['buckets'][b])
        for r, raw in recs:
            if r in MODEL_ROUTINES:
                dx, dy, dp = struct.unpack('>3h', raw[26:32]); recs32.append((b, r, struct.unpack('>L', raw[4:8])[0], dx, dy, dp))
    tot['model_records'] += len(recs32)
    tot['model_bucket_by_clamp'] += sum(clamp_bucket(x[5]) == x[0] for x in recs32)
    tot['model_bucket_ctl_noclamp_skipped'] += sum(((x[5] - 0x900) >> 8) == x[0] for x in recs32)
    tot['ship_records'] += sum(x[2] == 0xab62 for x in recs32)
    # object models: the walker's camera
    ocx, ocy, ocz = fr['cam_obj']; have = collections.Counter((x[3], x[4], x[5]) for x in recs32)
    for i, r in enumerate(pool(fr['obj_walked'], 18)):
        if struct.unpack('>L', r[14:18])[0] not in MODEL_OBJ: continue
        x, y, z = struct.unpack('>3h', r[:6])
        if ((x - (ocx - 0x580)) & 0xffff) >= 0xb00 or ((z - (ocz - 0x500)) & 0xffff) >= 0xa00: continue
        tot['objmodel_pred'] += 1
        trip = (s16((x - ocx) & 0xffff), s16((y - ocy) & 0xffff), s16((z - ocz + 0xe00) & 0xffff))
        if have[trip]: have[trip] -= 1; tot['objmodel_found'] += 1
    # actors: window of the actor walker ($215ea) with the camera at the painter's entry; kinds that draw reach the tail
    for i, r in enumerate(pool(fr['act'], 20)):
        x, y, z = struct.unpack('>3h', r[:6])
        if ((x - (cx - 0x680)) & 0xffff) >= 0xd00 or ((z - (cz - 0x600)) & 0xffff) >= 0xc00: continue
        trip = (s16((x - cx) & 0xffff), s16((y - cy) & 0xffff), s16((z - cz + 0xe00) & 0xffff))
        tot['actor_in_window'] += 1
        if have[trip]: have[trip] -= 1; tot['actor_found'] += 1

def main():
    tot = collections.Counter()
    for fn in sys.argv[1:]:
        frames = json.load(open(fn))
        for fr in frames:
            parsed = [parse(b) for b in fr['buckets']]
            tot['frames'] += 1
            tot['buckets'] += 10
            tot['parse_ok'] += sum(ok for _, ok in parsed)
            for _, ok in parsed:
                pass
            model_checks(fr, tot)
            obs = [[r for r in recs if r[0] in DOTS] for recs, _ in parsed]
            tot['dot_records'] += sum(len(o) for o in obs)
            for name, rule in RULES.items():
                pred = predict(fr, rule)
                per = collections.defaultdict(list)
                for b, sx, sy, i, h in pred: per[b].append((sx, sy, i))
                okframe = True; matched_obj = 0
                for b in range(10):
                    o = obs[b]; k = 0; exp = per.get(b, [])
                    for sx, sy, i in exp:
                        def rec(j):
                            _, raw = o[j]; return struct.unpack('>2h', raw[4:8])
                        if k + 1 < len(o) and o[k][0] == SHADOW and rec(k)[0] == sx and rec(k + 1)[0] == sx and rec(k + 1)[1] == sy:
                            k += 2; matched_obj += 1          # shadow record, then the sprite record
                        elif k < len(o) and rec(k)[0] == sx and (rec(k)[1] == sy):
                            k += 1; matched_obj += 1          # single record (sprite at the object's y)
                        else:
                            okframe = False
                            break
                    if k != len(o): okframe = False
                tot[name + ' frames_exact'] += okframe
                tot[name + ' objects'] += len(pred)
                tot[name + ' objects_matched'] += matched_obj
    for k, v in sorted(tot.items()): print(f'{k:50s} {v}')

if __name__ == '__main__': main()
