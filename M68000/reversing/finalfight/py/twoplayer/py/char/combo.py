"""combo.py <log> <ch> : every damage event on the dummy compared with the ROM (attack box id -> row -> damage byte at the player's +92, type, award)."""
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import charlib as C
log, ch = sys.argv[1], int(sys.argv[2])
p92 = C.state_p92(ch)
ok = tot = 0
for rel, d, id22, t63, r, ds in C.hits(log):
    if d > 0: continue   # dummy hp reset
    box = C.attack_box(ch, id22); exp = C.damage_byte(p92, box['off']); code, amt = C.hit_award(ch, box['off'])
    good = (-d == exp and t63 == box['hit']); tot += 1; ok += good
    print('rel %4d sub=%s ss=%s id %02x dmg %d (rom %d) type %d (rom %d) score +%s (rom %s) %s' % (rel, r['sub'], r['ss'], id22, -d, exp, t63, box['hit'], ds, amt, '' if good else 'MISMATCH'))
print('%s %d/%d' % (C.NAMES[ch], ok, tot))
