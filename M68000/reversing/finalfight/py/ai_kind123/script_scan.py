"""script_scan.py [tablebase]: walk the stage spawn scripts ($5aea state machine, tables $5f5e / $5f7e) and list the spawn entries
(16 bytes: +0 delay, +2 track flag, +4 x, +6 y, +8 tag, +9 kind, +10 subtype word, +12 -> 54(rec), +13 -> 98(rec), +14 -> 96(rec), +15 flag).
Group header after a trigger word: w16, w12, w18, w, long(next stream).  Commands: $8000 mode w, $8002 pause, $8004 jump long."""
import os, sys
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
rw = lambda a: (rom[a] << 8) | rom[a + 1]
rl = lambda a: (rw(a) << 16) | rw(a + 2)
tb = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x5f5e
want = None
rows = []
for stage in range(8):
    base = rl(tb + 4 * stage)
    for area in range(rw(base) // 2):
        off = rw(base + 2 * area)
        A3 = base + off
        mode = rw(A3); A3 += 2
        seen = set(); n = 0
        while A3 not in seen and n < 400 and 0 < A3 < 0xfff00:
            seen.add(A3); n += 1
            d2 = rw(A3)
            if d2 & 0x8000:
                cmd = d2 & 0xfff
                if cmd == 0: mode = rw(A3 + 2); A3 += 4
                elif cmd == 2: A3 += 2; rows.append((stage, area, A3, 'PAUSE')); 
                elif cmd == 4: A3 = rl(A3 + 2)
                else: rows.append((stage, area, A3, 'cmd%x' % cmd)); break
                continue
            trig = d2; hdr = A3 + 2
            nxt = rl(hdr + 8)
            e = hdr + 12
            ents = []
            while e < 0x80000 and not (rw(e) & 0x8000):
                ents.append(e); e += 16
                if e >= nxt and nxt > e - 16 : break
            rows.append((stage, area, A3, 'TRIG mode%d x=%04x hdr=%04x %04x %04x %04x next=%06x' % (mode, trig, rw(hdr), rw(hdr + 2), rw(hdr + 4), rw(hdr + 6), nxt)))
            for e in ents:
                rows.append((stage, area, e, 'ENT delay=%04x trk=%04x x=%04x y=%04x tag=%02x kind=%02x sub=%04x b12=%02x b13=%02x b14=%02x b15=%02x' % (rw(e), rw(e + 2), rw(e + 4), rw(e + 6), rom[e + 8], rom[e + 9], rw(e + 10), rom[e + 12], rom[e + 13], rom[e + 14], rom[e + 15])))
            A3 = nxt if nxt > A3 else e
for r in rows: print('s%d a%d %06x %s' % r)
