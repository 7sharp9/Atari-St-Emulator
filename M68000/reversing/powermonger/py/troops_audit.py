"""troops_audit.py <snap>... : per lord compare leader.troops_field ($4e514+32*i+8) with the live men whose home
settlement (word 34(man) -> $4f916 record, +14 = lord byte offset, as $1b8c reads it) is that lord, split by flag bit 6 of byte 7."""
import os, sys, struct, collections
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap
W = lambda r, a: struct.unpack('>H', r[a:a+2])[0]
for p in sys.argv[1:]:
    r = ram_from_snap(p if os.path.isabs(p) else os.path.join(ROOT, p))
    men = collections.defaultdict(list)
    for i in range(512):
        a = 0x51b66 + 50*i
        if r[a+5] == 0 or r[a+5] > 127 or r[a+6] != 0: continue
        s = W(r, a+34)
        sa = 0x4f916 + s
        lo = W(r, sa+14)
        men[lo].append((r[a+7] & 0x40 != 0, r[a+7] & 0x10 != 0, r[a+7] & 0xf, r[a+31], r[a+5], a))
    n = eq = w1 = 0; rows = []
    eqall = 0; eq3 = w13 = 0; bad3 = []; eq_leaders = 0; sumtf = sumclr = sumset = 0
    for li in range(64):
        b = 0x4e514 + 32*li
        if r[b] == 0 and W(r, b+4) == 0: continue
        tf = W(r, b+8); L = men.get(32*li, [])
        clr = sum(1 for m in L if not m[0]); st = len(L) - clr
        # clear without leader-flag entities
        clr_nl = sum(1 for m in L if not m[0] and not m[1])
        lead8a = sum(1 for m in L if not m[0] and m[1] and m[3]==0x8a)
        rule3 = clr_nl + (lead8a if clr_nl > 0 else 0)
        eq3 += tf == rule3; w13 += abs(tf-rule3) <= 1
        if tf != rule3: bad3.append((li, tf, rule3))
        n += 1; eq += tf == clr_nl; w1 += abs(tf-clr_nl) <= 1; eqall += tf == clr; eq_leaders += 0
        sumtf += tf; sumclr += clr; sumset += st
        rows.append((li, r[b], tf, clr, st, clr_nl))
    print(os.path.basename(p), 'lords', n, 'exact(bit6 clear, no leader-flag man)', eq, 'within1', w1, 'exact(bit6 clear incl leader)', eqall, ' sum tf', sumtf, 'sum clr', sumclr, 'sum inarmy', sumset)
    print('   rule3 (bit6 clear, non-leader, plus a mode-$8a leader when the lord has non-leader men home): exact', eq3, 'within1', w13, 'misses', bad3)
    if '-v' in os.environ.get('V',''):
        for row in rows: print('  lord %2d side %d tf %3d clr %3d inarmy %3d clr_noleaderflag %3d' % row)
    orph = [k for k in men if k % 32 or k//32 >= 64]
    if orph: print('  men owned by non-lord offsets', {k: len(men[k]) for k in orph})
