"""p2_entries.py <log1p> <log2p> : for every stage 0 script entry with byte 15 set (two-player only, py/ai_kind45/script.py) whose segment trigger the camera reached in the logs, count the pool-2 spawns that
carry its (kind, +20, +21, x, y) in a one-player log and in a two-player log (S lines of lua/bot2p.lua / stagebot.lua). Also lists, for the segments that contain such an entry, how many of the entries
without the flag spawned in each log (same identity), so the flag, not the segment, is what differs."""
import sys, os, re, collections
here = os.path.dirname(os.path.abspath(__file__))
_d = here
while _d != '/' and not os.path.exists(os.path.join(_d, 'reversing/finalfight/py/ai_kind45/script.py')): _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'reversing/finalfight/py/ai_kind45'))
import script as S
def spawns(path):
    out = []
    cam = 0
    for ln in open(path):
        m = re.match(r'S (\d+) pool=2 rec=(\d+) (\w+) kind=(\w+) ch=(\w+) ent=(\w+) lvl=(\w+) x=(\w+) y=(\w+) hp=(\w+) cam=(\w+) scr=(\w+)', ln)
        if m:
            f, rec, addr, kind, ch, ent, lvl, x, y, hp, c, scr = m.groups()
            out.append(dict(f=int(f), kind=int(kind, 16), ch=int(ch, 16), ent=int(ent, 16), x=int(x, 16), y=int(y, 16), cam=int(c, 16)))
        m = re.match(r'\d+ sa=\w+ cam=(\w+)', ln)
        if m: cam = max(cam, int(m.group(1), 16))
    return out, cam
logs = [spawns(p) for p in sys.argv[1:3]]
base = S.SETS[2]; p = S.l(base)
print('log                 max camera x seen')
for n, (s, cam) in zip(sys.argv[1:3], logs): print('%-40s %04x' % (os.path.basename(n), cam))
tot = [0, 0]
for area in range(3):
    a = p + S.w(p + 2 * area)
    for it in S.parse(a):
        if it[0] != 'seg': continue
        seg = it[1]
        if not any(e['p2'] for e in seg['ents']): continue
        print('stage 0 area %d segment @%x trigger camera %04x' % (area, seg['at'], seg['trigger']))
        for e in seg['ents']:
            row = []
            for (s, cam) in logs:
                if cam < seg['trigger']: row.append('trigger not reached'); continue
                n = sum(1 for q in s if q['kind'] == e['kind'] and q['ch'] == e['w20'] >> 8 and q['ent'] == (e['w20'] & 255) and q['x'] == (e['x'] & 0xffff) and abs(q['y'] - e['y']) <= 16)
                row.append(str(n))
            print('   @%x kind %d +20=%02x +21=%02x x=%d y=%d two-player flag %d : spawns one-player log %s, two-player log %s' % (e['addr'], e['kind'], e['w20'] >> 8, e['w20'] & 255, e['x'], e['y'], e['p2'], row[0], row[1]))
