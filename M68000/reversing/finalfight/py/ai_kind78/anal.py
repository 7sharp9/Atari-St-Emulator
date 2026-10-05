#!/usr/bin/env python3
"""anal.py <log> [kind] : parse a spawn.lua log; print per-frame state of records of the given kind (default all pool-2)
and run-length-encode the (2,3,4,5) state tuples with frames, hp, x, y, anim."""
import sys, re
log = sys.argv[1]; kind = int(sys.argv[2]) if len(sys.argv) > 2 else None
frames = []
cur = None
for l in open(log):
    if l.startswith('F '):
        m = re.match(r'F (\d+) rel=(\d+) cam=(\w+),(\w+)', l); cur = {'f': int(m.group(1)), 'rel': int(m.group(2)), 'cam': int(m.group(3), 16), 'recs': {}, 'c': None, 'p6': {}, 'p4': {}, 'p8': {}, 'pa': {}}
        frames.append(cur)
    elif l.startswith('C2 '):
        cur['c2'] = bytes.fromhex(l[3:].strip())
    elif l.startswith('C '):
        cur['c'] = bytes.fromhex(l[2:].strip())
    elif l.split()[0] in ('R','P6','P4','P8','PA'):
        t = l.split(); b = bytes.fromhex(t[2])
        {'R': cur['recs'], 'P6': cur['p6'], 'P4': cur['p4'], 'P8': cur['p8'], 'PA': cur['pa']}[t[0]][int(t[1], 16)] = b
    elif l.startswith('S '): cur['s'] = bytes.fromhex(l[2:].strip())
    elif l.startswith('SPAWN'): print(l.strip())
w = lambda b, o: int.from_bytes(b[o:o+2], 'big')
sw = lambda b, o: (w(b, o) ^ 0x8000) - 0x8000
def desc(b):
    return dict(st=(b[2], b[3], b[4], b[5]), hp=w(b, 24), x=w(b, 6), y=w(b, 10), gy=w(b, 14), fr=b[54], a45=b[45], a44=b[44], fc=b[46], r22=b[22], r63=b[63],
                t30=b[30], t31=b[31], t23=b[23])
if __name__ == '__main__':
    last = {}
    for fr in frames:
        for a, b in fr['recs'].items():
            if kind is not None and b[19] != kind: continue
            d = desc(b); key = (a, d['st'], b[64], b[66], b[67])
            if last.get(a) != key:
                print('f=%d rel=%d rec=%x kind=%d st=%s hp=%d x=%04x y=%04x gy=%04x fr=%d a45=%02x a44=%02x face=%d r22=%d r63=%d t30=%d t31=%d t23=%d b64=%02x b66=%02x b67=%02x' % (
                    fr['f'], fr['rel'], a, b[19], d['st'], d['hp'], d['x'], d['y'], d['gy'], d['fr'], d['a45'], d['a44'], d['fc'], d['r22'], d['r63'], d['t30'], d['t31'], d['t23'], b[64], b[66], b[67]))
                last[a] = key
