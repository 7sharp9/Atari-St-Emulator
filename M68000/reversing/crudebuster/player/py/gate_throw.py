"""gate_throw.py <hit.txt from hitlab with CB_BTN=b3>: a grabbed-and-thrown pool A enemy goes state $17 (carried, +17=2) -> 3 (flying) -> 4 (dead) and loses 4 health ($22dac: subq.b #4,5(A6)),
   so HP 2 -> $fe and HP 3 -> $ff (byte wrap); one score award of the 'thrown' amount (checked by gate_score.py thrown)."""
import sys, collections
tr = collections.OrderedDict()
for ln in open(sys.argv[1]):
    f = ln.split(); trial, t, tt, field, ch = int(f[0]), int(f[1], 16), int(f[2]), f[3], [int(x, 16) for x in f[4].split(">")]
    tr.setdefault(trial, []).append((tt, field, ch, t))
ok = n = 0
for k, ev in tr.items():
    sts = [e[2][1] for e in ev if e[1] == "st"]
    if 0x17 not in sts: print("trial %d type %02x: never grabbed (not grabbable or out of reach)" % (k, ev[0][3])); continue
    hp0 = [e[2][1] for e in ev if e[1] == "hp"][0]; hpt = [e[2][1] for e in ev if e[1] == "hp" and e[0] > 1][0]
    seq = [s for s in sts if s in (0x17, 3, 4)]
    good = seq == [0x17, 3, 4] and hpt == (hp0 - 4) & 0xff
    n += 1; ok += good
    print("trial %d type %02x: states %s, hp %d -> %02x (expected %02x) %s" % (k, ev[0][3], ["%x" % s for s in seq], hp0, hpt, (hp0 - 4) & 0xff, "OK" if good else "MISMATCH"))
print("%d of %d grabbed enemies follow carried -> flying -> dead with HP-4" % (ok, n))
