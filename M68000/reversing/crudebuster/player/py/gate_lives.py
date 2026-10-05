"""gate_lives.py <cont_run_dir> <cont_continue_dir>: lives, continue countdown, game over from two lua/contlab.lua runs.
   dir1 (no usable press): P1 dies three times (spare lives 2 -> 1 -> 0, third death -> mode 1), continue countdown 9..0 in 126-frame steps, game over, attract.
   dir2 (start pressed at digit 5): continue taken: credit-1, lives back to the DIP value, health $38, score 0."""
import sys, re
def ev(path):
    out = []
    for ln in open(path):
        m = re.match(r"(\d+) (\S+) ([0-9a-f]{2})>([0-9a-f]{2})", ln)
        if m: out.append((int(m.group(1)), m.group(2), int(m.group(3), 16), int(m.group(4), 16)))
    return out
e1 = ev(sys.argv[1] + "/cont.txt"); e2 = ev(sys.argv[2] + "/cont.txt")
ok = n = 0
def chk(name, cond, detail=""):
    global ok, n
    n += 1; ok += bool(cond); print("%-70s %s %s" % (name, "PASS" if cond else "FAIL", detail))
life = [(f, a, b) for f, k, a, b in e1 if k == "P1life"]
cont = [f for f, k, a, b in e1 if k == "P1mode" and b == 0xd9]
chk("spare lives: 2 at start, 1 after death 1, 0 after death 2; death 3 takes it to -1 -> clamped to 0 and sets mode 1 (continue)",
    [x[2] for x in life] == [0, 2, 1, 0] and len(cont) == 1, str([(f, "%x" % b) for f, a, b in life]) + " continue at %s" % cont)
dig = [(f, b) for f, k, a, b in e1 if k == "P1d"]
steps = [dig[i + 1][0] - dig[i][0] for i in range(1, len(dig) - 2) if dig[i][1] <= 9 and dig[i + 1][1] == dig[i][1] - 1]
chk("continue digit 9..0 steps every 126 frames (63 logic steps of 2 VBL)", steps and all(s == 126 for s in steps), "%d steps, e.g. %s" % (len(steps), steps[:3]))
mode0 = [f for f, k, a, b in e1 if k == "P1mode" and b == 0]
f40 = [(f, b) for f, k, a, b in e1 if k == "f40"]
chk("end of countdown: P1 record cleared (+0 = 0), then $80040 bit 5 (game over), 461 frames later attract", bool(mode0) and any(b == 0xa0 for f, b in f40) and any(b == 0 for f, b in f40),
    "mode0 at %s, f40 %s" % (mode0[:1], [(f, "%02x" % b) for f, b in f40[-3:]]))
cred = [(f, b) for f, k, a, b in e2 if k == "credit"]
chk("credits 3 coins -> 3, start -> 2, continue -> 1", [b for f, b in cred if f > 0] == [1, 2, 3, 2, 1], str([b for f, b in cred if f > 0]))
c = [f for f, k, a, b in e2 if k == "credit" and b == 1 and f > 3000]
hp = [(f, b) for f, k, a, b in e2 if k == "P1hp" and f > 3000 and b == 0x38]
sc = [(f, b) for f, k, a, b in e2 if k == "P1score3" and f > 3000 and b == 0]
lf = [(f, b) for f, k, a, b in e2 if k == "P1life" and f > 3000]
chk("continue: credit, lives (2), health ($38), score low byte (0) all change in the same frame", bool(c) and (c[0], 2) in lf and hp and hp[0][0] == c[0] and sc and sc[0][0] == c[0], "frame %s" % c[:1])
print("%d of %d" % (ok, n))
