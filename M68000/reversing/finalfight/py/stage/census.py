"""census.py [--stage=N] <log>... : match the spawn lines ("S" lines) of lua/stagebot.lua logs against the script entries of stage N (the stage byte 190(A5), default 0; py/ai_kind45/script.py).
An entry (tag, kind, +20, +21, level) is matched by the first unmatched spawn of the same pool, kind, character and entrance whose frame is later than
the previous matched entry of the same segment; level $ff and kind 6 (init overwrites +96) are matched without the level. Prints the entry table
with the frame, camera and script pointer of its spawn, then the spawns no entry explains (by pool).
Only the S lines of frames where the stage byte (the log's sa= field) equals N are used. usage: census.py out/boss.log out/stage1.log; census.py --stage=4 <s4.log>"""
import sys, os, re, collections
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '../ai_kind45'))
import script as S
POOL = {'2': 2, '6': 6, '4': 4, '8': 8, 'a': 0xa, '12': 0x12, '14': 0x14}
args = sys.argv[1:]
STAGE = 0
if args and args[0].startswith('--stage='): STAGE = int(args.pop(0).split('=')[1])
spawns = []
for p in args:
    cur = None; first = None; mine = []
    for ln in open(p):
        m = re.match(r'(\d+) sa=(\w\w)', ln)
        if m and int(m[1]) > 0: cur = int(m[2], 16)
        if cur is not None and cur != STAGE: continue
        m = re.match(r'S (\d+) pool=(\w+) rec=(\d+) (\w+) kind=(\w+) ch=(\w+) ent=(\w+) lvl=(\w+) x=(\w+) y=(\w+) hp=(\w+) cam=(\w+) scr=(\w+)', ln)
        if m:
            f, pool, rec, addr, kind, ch, ent, lvl, x, y, hp, cam, scr = m.groups()
            mine.append(dict(f=int(f), tag=POOL[pool], rec=int(rec), kind=int(kind, 16), ch=int(ch, 16), ent=int(ent, 16), lvl=int(lvl, 16), x=int(x, 16),
                             y=int(y, 16), hp=int(hp, 16), cam=int(cam, 16), scr=int(scr, 16), used=False))
    # a log that starts from a saved state lists every live record as new at its first frame: drop those a previous log already listed
    if mine:
        f0 = min(s['f'] for s in mine)
        old = {(s['tag'], s['rec'], s['kind'], s['ch'], s['ent']) for s in spawns}
        mine = [s for s in mine if not (s['f'] == f0 and (s['tag'], s['rec'], s['kind'], s['ch'], s['ent']) in old)]
    spawns += mine
tot = hit = 0
base = S.SETS[2]; p = S.l(base + 4 * STAGE); n = S.w(p) // 2
for area in range(n):
    a = p + S.w(p + 2 * area)
    print('== stage %d area %d script %x' % (STAGE, area, a))
    for it in S.parse(a):
        if it[0] != 'seg': continue
        seg = it[1]
        for e in seg['ents']:
            if e['p2']: continue
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
print('entries matched: %d of %d (one-player entries only)' % (hit, tot))
# then the placement lists ($6026, py/placement/placetab.py): type 2 (fighter) and 4 (boss) entries of the init list and the live trigger list ($6346) of each area,
# matched in list order to the first unmatched spawn of the same pool, kind, +20 and +21 later than the previous match of that list; a trigger-list entry also needs the camera
# within 16 px of its trigger word at the spawn (placement.md: mode 2 spawns came 1 to 3 px past the trigger; modes 0, 4, 6 compare camera y or the other direction, so they are not tested)
sys.path.insert(0, os.path.join(here, '../placement'))
import placetab as PT
ptot = phit = 0
for which, tab in (('init', 0x636e), ('trig', 0x6346)):
    for area, addr in enumerate(PT.areas(tab)[STAGE]):
        ents = PT.initlist(addr) if which == 'init' else [e for _, es in PT.trigmodes(addr)[0] for e in es]
        mode_of = {} if which == 'init' else {e['addr']: md for md, es in PT.trigmodes(addr)[0] for e in es}
        last = -1
        print('== stage %d area %d placement %s list %x' % (STAGE, area, which, addr))
        for e in ents:
            if e['sp'] not in (2, 4) or e['p2']: continue
            ptot += 1
            cand = [s for s in spawns if not s['used'] and s['tag'] == e['sp'] and s['kind'] == e['kind'] and s['ch'] == e['c20'] and s['ent'] == e['c21'] and s['f'] >= last
                    and (which == 'init' or mode_of.get(e['addr'], 2) != 2 or abs(s['cam'] - e['trig']) <= 16)]
            if cand:
                s = min(cand, key=lambda s: s['f']); s['used'] = True; phit += 1; last = s['f']
                print('  @%x type=%d kind=%2d +20=%02x +21=%02x trig=%04x x=%04x -> frame %5d cam=%04x x=%04x y=%04x lvl=%02x' % (e['addr'], e['sp'], e['kind'], e['c20'], e['c21'], e['trig'], e['x'], s['f'], s['cam'], s['x'], s['y'], s['lvl']))
            else:
                print('  @%x type=%d kind=%2d +20=%02x +21=%02x trig=%04x x=%04x -> not seen' % (e['addr'], e['sp'], e['kind'], e['c20'], e['c21'], e['trig'], e['x']))
print('placement entries (types 2 and 4, one-player) matched: %d of %d' % (phit, ptot))
un = collections.Counter((s['tag'], s['kind'], s['ch'], s['ent']) for s in spawns if not s['used'])
print('spawns with no script entry (pool, kind, ch, ent): count')
for k, c in sorted(un.items()): print('  tag %x kind %02x ch %02x ent %02x: %d' % (k[0], k[1], k[2], k[3], c))
