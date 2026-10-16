"""census54.py [snap-glob ...]: static census of every man in mode $54 (merchant start of trip, handler $15ad2).

Per man: home lord offset (settlement 34(A1) -> word 14 of the settlement record $4f916), A4 offset = word $4f914,
nation byte 0 of the home lord and of leader 0, 14(A1)&7, dwell 18(A1).  Classifies which branch of the $15b00 loop the
man would take when its dwell expires: 'home' (nation != 0, home != A4 or D2 <= 1), 'wrap' (home == A4: A3 wraps to
leader 0 at $15b14 if D2 >= 2), 'hang' (nation 0 and home != A4: the loop never decrements D2 and never exits).
Skips pm148 chunks whose commander AI is frozen (py/arms/stuck_classes.frozen)."""
import collections, glob, sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
from disassemble import ram_from_snap
from stuck_classes import frozen
OBJ, LEADER, SETTL = 0x51b66, 0x4e514, 0x4f916
def w(r, a): return (r[a] << 8) | r[a + 1]
def s16(v): return v - 0x10000 if v & 0x8000 else v
globs = sys.argv[1:] or ['scratchpad/pm142/rand1.snap', 'scratchpad/pm148/arms/long/*_c*.snap']
tot = collections.Counter(); a4s = collections.Counter(); nsn = 0; skipped = 0
for g in globs:
    for s in sorted(glob.glob(str(ROOT / g))):
        p = Path(s)
        if '_c' in p.name and frozen(p) == 'frozen': skipped += 1; continue
        r = ram_from_snap(str(p)); nsn += 1
        A4 = w(r, 0x4f914); a4s[A4] += 1
        for k in range(1, 512):
            a = OBJ + 50 * k
            if s16(r[a + 5] if r[a+5] < 128 else r[a+5]-256) <= 0 or r[a + 31] != 0x54: continue
            home = w(r, SETTL + w(r, a + 34) + 14)
            nat = r[LEADER + home]; d2 = r[a + 14] & 7
            if nat == 0: cls = 'wrap-from-empty' if home == A4 else 'hang'
            elif home == A4: cls = 'wrap' if d2 >= 2 else 'last,home'
            else: cls = 'home'
            tot[cls] += 1
            if cls not in ('home',):
                print(p.name, f'slot {k} home ${home:x} A4 ${A4:x} nat {nat} lord0 nat {r[LEADER]} d2 {d2} dwell {s16(w(r,a+18))} -> {cls}')
print(f'snapshots {nsn} (frozen skipped {skipped}); classes {dict(tot)}; A4 values {dict(a4s)}')
