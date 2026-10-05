# gate: damage dealt to Cody by kind-0 fighters == byte[char data base + $60 + attack-box +8 word + variant (96(A6))]
# usage: dmgcheck.py <rec.bin>...   (poolrec.lua output)
import rec, collections, sys, anims as A
ok = bad = 0; seen = collections.Counter(); badl = []
for fn in sys.argv[1:]:
    fs = rec.load(fn)[1:]
    for a, b in zip(fs, fs[1:]):
        h0 = rec.u16(a.pl[0], 24); h1 = rec.u16(b.pl[0], 24)
        if not (0 < h1 < h0 <= 144): continue
        c = set()
        for fr in (a, b):
            for r in fr.p2:
                if r[0] and r[19] == 0 and (r[45] & 0x7f) != 0 and r[20] < 4: c.add((r[20], r[45] & 0x7f, r[96]))
        if len(c) != 1: continue
        ch, atk, v = next(iter(c))
        name, boxbase, dat = A.CHARS[ch]
        box = boxbase + (atk & 0x7f) * 16 + A.w(boxbase)
        row = A.w(box + 8)
        pred = A.rom[dat + 0x60 + row + v]
        seen[(ch, atk, v, pred)] += 1
        if pred == h0 - h1: ok += 1
        else: bad += 1; badl.append((a.f, ch, atk, v, pred, h0 - h1))
print('predicted == observed:', ok, 'of', ok + bad, 'single-attacker damage events;', 'mismatches', badl[:5])
for k, v in sorted(seen.items()): print('  char %d atk %d v %d pred %d : %d events' % (k[0], k[1], k[2], k[3], v))
