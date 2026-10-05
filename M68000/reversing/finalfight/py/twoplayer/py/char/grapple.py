"""grapple.py <ch> [prefix=ch<ch>_g2] : the grapple logs g2a..g2e: dummy hp changes with the player's sub/m66, score deltas, compared with the ROM tables
(strikes $db6e, awards $d86e, thrown-landing rule $3f7a/$3fd8)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charlib as C
ch = int(sys.argv[1]); pre = sys.argv[2] if len(sys.argv) > 2 else 'ch%d_g2' % ch
print(C.NAMES[ch], 'strike dmg (ROM $db6e, steps 0,2,4,6):', [C.strike_damage(ch, s) for s in (0, 2, 4, 6)])
for v in 'abcde':
    n = pre + v
    try: rows, ev = C.load(n)
    except Exception as e: print(n, 'missing'); continue
    print('==', n, 'player subs/m66 timeline:', end=' ')
    last = None; seq = []
    for r in rows:
        k = (r['st'], r['sub'], r['m66'])
        if k != last: seq.append('%d:%s/%s/m%s' % (r['rel'], r['st'], r['sub'], r['m66'])); last = k
    print(' '.join(seq[:24]))
    for rel, d, id22, t63, r, ds in C.hits(n):
        print('   hit rel %d dhp %d victim id22=%02x type63=%d player sub=%s ss=%s m66=%s score +%s' % (rel, d, id22, t63, r['sub'], r['ss'], r['m66'], ds))
