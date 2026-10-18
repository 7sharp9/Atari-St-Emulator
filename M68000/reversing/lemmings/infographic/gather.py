import json, re, sys
B = 'scratchpad/lemmings/blk/'
runs = {  # key: (dir, x0, y0, max frames)
 'climber': ('climb', 688, 40, 45), 'floater': ('float', 688, 56, 70), 'floater_ctl': ('ctl', 688, 56, 70),
 'bomber': ('bomb', 768, 66, 56), 'builder': ('build', 688, 56, 51), 'basher': ('bashw', 688, 56, 41),
 'miner': ('mine', 688, 56, 51), 'digger': ('dig', 688, 60, 61)}
out = {}
for k, (d, x0, y0, nmax) in runs.items():
    fr = []; cur = None
    for l in open(B + d + '/frames.txt'):
        if l.startswith('=='):
            m = re.search(r't\+(\d+)|pre-click', l); t = int(m.group(1)) if m.group(1) else -1
            mm = re.search(r'x=(\d+) y=(\d+) dir=(-?\d+) state=([0-9a-f]+)', l)
            cur = {'t': t, 'x': int(mm[1]), 'y': int(mm[2]), 'd': int(mm[3]), 's': int(mm[4], 16), 'rows': []}; fr.append(cur)
        elif l.strip() and cur is not None:
            cur['rows'].append(l.rstrip('\n')[4:])
    base = fr[0]['rows']; H = len(base); W = len(base[0])
    step = max(1, (len(fr) - 1 + nmax - 2) // (nmax - 1))
    pick = [0] + list(range(1, len(fr), step))
    frames = []
    for i in pick:
        f = fr[i]
        diff = []
        for r in range(H):
            a, b = base[r], f['rows'][r]
            if a != b:
                for c in range(W):
                    if a[c] != b[c]: diff.append([c, r, 1 if b[c] == '#' else 0])
        frames.append({'tick': round(max(f['t'], 0) / 36000, 1), 'x': f['x'], 'y': f['y'], 'd': f['d'], 's': f['s'], 'diff': diff})
    out[k] = {'x0': x0, 'y0': y0, 'W': W, 'H': H, 'base': base, 'frames': frames}
    print(k, len(frames), 'frames', H, 'rows', sum(len(f['diff']) for f in frames), 'diff px')
json.dump(out, open('scratchpad/lemmings/info/data.json', 'w'), separators=(',', ':'))

# blocker trajectories (60,000 steps a sample, lemmings 1 and 5)
import struct
bl = {}
for arm, f in (('blocker', 'outB.txt'), ('control', 'outC.txt')):
    L1, L5, L0 = [], [], []
    for l in open(B + f):
        b = bytes(int(x, 16) for x in l.split())
        xs = [struct.unpack('>H', b[i * 44:i * 44 + 2])[0] for i in range(10)]
        L1.append(xs[1]); L5.append(xs[5]); L0.append(xs[0])
    bl[arm] = {'l1': L1, 'l5': L5}
out['blocker'] = bl
json.dump(out, open('scratchpad/lemmings/info/data.json', 'w'), separators=(',', ':'))
print('blocker', len(bl['blocker']['l1']))
