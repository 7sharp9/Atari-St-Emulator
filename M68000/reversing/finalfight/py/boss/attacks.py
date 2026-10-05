"""attacks.py <dump>...: DAMND's attack picks. For each attack episode (+3 = 2 with +4 = 2: $3db98 has just run) read 153 (script id), 148 (angry flag) and the step ids 152 executed, and compare with the ROM script table
$3dc1a / pick table $3dbda; also the damage rows (attack box ids seen during the episode) and the cooldown 150."""
import sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
rw = lambda a: int.from_bytes(rom[a:a+2], 'big')
def script(i):
    a = 0x3dc1a + rw(0x3dc1a + 2 * i); s = []
    while rom[a] < 0x80: s.append(rom[a]); a += 1
    return s
pick = {0: list(rom[0x3dbda:0x3dbda + 32]), 1: list(rom[0x3dbda + 32:0x3dbda + 64])}
tot = collections.Counter(); ok = bad = 0
for path in sys.argv[1:]:
    D = Dump(path); fr = D.frames()
    ep = None
    for i in range(D.n):
        if not D.u8(i, BOSS): continue
        st3, st4 = D.u8(i, BOSS + 3), D.u8(i, BOSS + 4)
        if st3 == 2 and st4 == 2 and (ep is None or ep['closed']):
            ep = dict(f=int(fr[i]), ang=D.u8(i, BOSS + 148), sid=D.u8(i, BOSS + 153), steps=[], atk=set(), closed=False, cool=D.u16(i, BOSS + 150), ptr=D.u32(i, BOSS + 154) & 0xffffff)
            ep['lst'] = ep['ptr']
            tot[(ep['ang'], ep['sid'])] += 1
            ep['rec'] = []
            eps = globals().setdefault('EPS', []); eps.append(ep)
        if ep and not ep['closed']:
            if st3 == 2 and st4 in (4, 6):
                s = D.u8(i, BOSS + 152)
                if st4 == 6 and (not ep['steps'] or ep['steps'][-1][1] != D.u32(i, BOSS + 154)) and D.u8(i, BOSS + 5) == 0:
                    ep['steps'].append((s, D.u32(i, BOSS + 154)))
                ep['atk'].add(D.u8(i, BOSS + 45) & 0x7f)
            elif st3 != 2 or (st4 == 0):
                if st3 != 2 or st4 == 0: ep['closed'] = True
res = globals().get('EPS', [])
print('episodes', len(res))
print('(angry, script id) counts:', dict(sorted(tot.items())))
for ang in (0, 1):
    n = sum(v for (a, s), v in tot.items() if a == ang)
    if not n: continue
    print(' angry=%d: %d picks' % (ang, n), ' '.join('script%d:%d (table %d/32)' % (s, tot[(ang, s)], pick[ang].count(s)) for s in range(6)))
for e in res[:12]:
    print(' ', e['f'], 'angry', e['ang'], 'script', e['sid'], 'ROM', script(e['sid']) if e['sid'] < 6 else '?', 'steps', [x[0] for x in e['steps']], 'boxes', sorted(e['atk']), 'cool', e['cool'])
