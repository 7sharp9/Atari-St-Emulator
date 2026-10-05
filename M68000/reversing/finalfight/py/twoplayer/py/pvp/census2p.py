"""census2p.py [--p2] <log>... (copy of py/stage/census.py with --p2: the entries with byte 15 set (two-player only) are included).
census.py <log>... : match the spawn lines ("S" lines) of lua/stagebot.lua logs against the stage 0 script entries (py/ai_kind45/script.py).
An entry (tag, kind, +20, +21, level) is matched by the first unmatched spawn of the same pool, kind, character and entrance whose frame is later than
the previous matched entry of the same segment; level $ff and kind 6 (init overwrites +96) are matched without the level. Prints the entry table
with the frame, camera and script pointer of its spawn, then the spawns no entry explains (by pool).
usage: census.py out/boss.log out/stage1.log"""
import sys, os, re, collections
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '../ai_kind45'))
_d = here
while _d != '/' and not os.path.exists(os.path.join(_d, 'reversing/finalfight/py/ai_kind45/script.py')): _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'reversing/finalfight/py/ai_kind45'))
import script as S
INC2P = '--p2' in sys.argv
sys.argv = [a for a in sys.argv if a != '--p2']
POOL = {'2': 2, '6': 6, '4': 4, '8': 8, 'a': 0xa, '12': 0x12, '14': 0x14}
spawns = []
for p in sys.argv[1:]:
    for ln in open(p):
        m = re.match(r'S (\d+) pool=(\w+) rec=(\d+) (\w+) kind=(\w+) ch=(\w+) ent=(\w+) lvl=(\w+) x=(\w+) y=(\w+) hp=(\w+) cam=(\w+) scr=(\w+)', ln)
        if m:
            f, pool, rec, addr, kind, ch, ent, lvl, x, y, hp, cam, scr = m.groups()
            spawns.append(dict(f=int(f), tag=POOL[pool], rec=int(rec), kind=int(kind, 16), ch=int(ch, 16), ent=int(ent, 16), lvl=int(lvl, 16), x=int(x, 16),
                               y=int(y, 16), hp=int(hp, 16), cam=int(cam, 16), scr=int(scr, 16), used=False))
# the logs of the second step restart with every live record as "new" at its first frame: drop those whose address+kind was already live
seen = set(); uniq = []
for s in spawns:
    k = (s['tag'], s['rec'], s['kind'], s['ch'], s['ent'], s['x'], s['y'])
    if s['f'] > 0 and k in seen and s['f'] == min(t['f'] for t in spawns if t['f'] > 8298 and True): pass
    uniq.append(s)
spawns = uniq
tot = hit = 0
for area in range(3):
    base = S.SETS[2]; p = S.l(base); n = S.w(p) // 2
    a = p + S.w(p + 2 * area)
    print('== stage 0 area %d script %x' % (area, a))
    for it in S.parse(a):
        if it[0] != 'seg': continue
        seg = it[1]
        for e in seg['ents']:
            if e['p2'] and not INC2P: continue
            tot += 1
            lvl_free = e['lvl'] == 0xff or (e['tag'] == 2 and e['kind'] == 6)
            cand = [s for s in spawns if not s['used'] and s['tag'] == e['tag'] and s['kind'] == e['kind'] and s['ch'] == (e['w20'] >> 8) and s['ent'] == (e['w20'] & 255)
                    and (lvl_free or s['lvl'] == e['lvl'])]
            # the entry fires while the script pointer is inside its segment: the spawn's scr is the pointer after the entry
            cand = [s for s in cand if seg['at'] <= s['scr'] <= e['addr'] + 0x30 or s['scr'] >= seg['at']]
            if cand:
                s = min(cand, key=lambda s: s['f']); s['used'] = True; hit += 1
                print('  @%x tag=%x kind=%2d +20=%02x +21=%02x lvl=%02x -> frame %5d cam=%04x scr=%06x x=%04x y=%04x lvl=%02x hp=%04x' % (e['addr'], e['tag'], e['kind'], e['w20'] >> 8, e['w20'] & 255, e['lvl'], s['f'], s['cam'], s['scr'], s['x'], s['y'], s['lvl'], s['hp']))
            else:
                print('  @%x tag=%x kind=%2d +20=%02x +21=%02x lvl=%02x -> not seen' % (e['addr'], e['tag'], e['kind'], e['w20'] >> 8, e['w20'] & 255, e['lvl']))
print('entries matched: %d of %d (%s)' % (hit, tot, 'including two-player entries' if INC2P else 'one-player entries only'))
un = collections.Counter((s['tag'], s['kind'], s['ch'], s['ent']) for s in spawns if not s['used'])
print('spawns with no script entry (pool, kind, ch, ent): count')
for k, c in sorted(un.items()): print('  tag %x kind %02x ch %02x ent %02x: %d' % (k[0], k[1], k[2], k[3], c))
