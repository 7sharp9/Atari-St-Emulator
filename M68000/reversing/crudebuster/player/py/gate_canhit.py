"""gate_canhit.py <taps.txt>: a thrown can (pool B type $0a, byte 0 $cb) hitting a grunt: the writer $fa04 sets the enemy's +6 to $88 (strong hit) and the enemy handler $22c8c takes 4 HP (2 -> $fe).
   taps.txt (lua/reclog.lua CB_TAPS=81005:2,81006:1): frame pc addr old new."""
import sys
ev = [ln.split() for ln in open(sys.argv[1])]
hit = [e for e in ev if e[1] == "00fa04" and e[2] == "081006" and e[4] == "88"]
hp = [e for e in ev if e[1] == "022c8c" and e[2] == "081005"]
ok = bool(hit) and bool(hp) and int(hp[0][4], 16) == (int(hp[0][3], 16) - 4) & 0xff and int(hp[0][0]) - int(hit[0][0]) == 1
print("thrown can: enemy +6 := $88 at frame %s (pc $fa04), HP %s -> %s one frame later (pc $22c8c, -4): %s" % (hit[0][0] if hit else "-", hp[0][3] if hp else "-", hp[0][4] if hp else "-", "PASS" if ok else "FAIL"))
