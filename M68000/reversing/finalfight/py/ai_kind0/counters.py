# gates over poolrec.lua dumps (run_rec.sh): counters and flags the kind-0 code maintains
#  alive   : byte $ff1154 == number of in-use records of kinds 0,1,2          (spawn gate $3e88 increments, $21fd6 decrements)
#  tokens  : word $ff115a == number of kind 0/2 records with +136 != 0        (attack tokens, $27c08 / $27c20)
#  vis     : 1(A6) == window test of $3264 (x-cam+$30 <= $1e0, y-camy+$80 <= $180) for live, non-held kind-0 records
#  box     : 44/45(A6) == bytes +4/+5 of the animation frame record at 36(A6) ($3b10/$3b3c copy them)
#  frame   : 166(A5) word +1 per frame
#  diff    : 168(A5) word changes
import rec, sys
import anims as A
alive = tok = tot = fr = frok = vt = vok = bt = bok = 0
dif = {}
for fn in sys.argv[1:]:
    fs = rec.load(fn)[1:]
    for a, b in list(zip(fs, fs[1:]))[1:]:
        fr += 1; frok += ((b.a(166, 2) - a.a(166, 2)) & 0xffff) == 1
    prev = None
    for f in fs:
        tot += 1
        alive += f.l(0xff1154) == sum(1 for r in f.p2 if r[0] and r[19] in (0, 1, 2))
        tok += f.l(0xff115a, 2) == sum(1 for r in f.p2 if r[0] and r[19] in (0, 2) and r[136] != 0)
        cx, cy = f.a(1042, 2), f.a(1046, 2)
        for r in f.p2:
            if r[0] and r[19] == 0 and r[2] in (2, 4) and r[64] == 0:
                pred = ((rec.u16(r, 6) - cx + 0x30) & 0xffff) <= 0x1e0 and ((rec.u16(r, 10) - cy + 0x80) & 0xffff) <= 0x180
                vt += 1; vok += pred == bool(r[1])
                p = rec.u32(r, 36) & 0xffffff
                if 0x20000 < p < 0x40000 and r[3] != 0:
                    bt += 1; bok += (A.rom[p + 4], A.rom[p + 5]) == (r[44], r[45])
        v = f.a(168, 2)
        if prev is not None and v != prev: dif.setdefault(fn, []).append((f.f, prev, v))
        prev = v
print('frames', tot)
print('alive counter $ff1154 == in-use kind 0/1/2 records: %d of %d' % (alive, tot))
print('token counter $ff115a == kind 0/2 records with +136 != 0: %d of %d' % (tok, tot))
print('visibility flag 1(A6) == $3264 window test: %d of %d (the rest are spawn frames)' % (vok, vt))
print('44/45(A6) == frame record +4/+5: %d of %d' % (bok, bt))
print('166(A5) +1 per frame: %d of %d' % (frok, fr))
for k, v in dif.items(): print('168(A5) changes in', k, '(frame, old, new):', v)
