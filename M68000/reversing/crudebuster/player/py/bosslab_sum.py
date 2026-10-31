"""Summarise a bosslab.lua log: boss hp over the run, every entry into a boss state with the player's pose, variant and action on the same
frame (the player is updated first), and the test of the grab rule of the brain leaf $26d7a (enemies1.md 4.3): an entry into state b needs |dx| < $40, the player's
pose (+24) & 15 in 0-3, 5, 6 (the brain masks it: the rising pose $13 counts as 3) and its variant (+25) below 4; a state f entry is the same leaf's fallback (or another leaf's jump attack).
usage: bosslab_sum.py <bosslab.txt> [...]"""
import collections, sys

GRAB_POSES = {0, 1, 2, 3, 5, 6}

def rows(path):
    for ln in open(path):
        a, b, c = ln.split("|")
        d, px, py, act, sub, pose, var, p88, php = a.split()
        bt, bs, bx, by, bhp, b1 = b.split()
        b1 = None if b1 == "-" else int(b1, 16)
        c = c.split(); f40 = int(c[1], 16) if len(c) > 1 else None
        yield dict(d=int(d), px=int(px), py=int(py), act=int(act, 16), sub=int(sub), pose=int(pose, 16), var=int(var), p88=int(p88, 16),
                   bt=bt, bs=bs, bx=None if bx == "-" else int(bx), by=None if by == "-" else int(by), bhp=None if bhp == "-" else int(bhp), b1=b1, dx=int(c[0]), f40=f40)

def main(path):
    R = list(rows(path))
    print(path)
    hp = [(r["d"], r["bt"], r["bhp"]) for i, r in enumerate(R) if i == 0 or (r["bhp"], r["bt"]) != (R[i - 1]["bhp"], R[i - 1]["bt"])]
    print(" boss hp:", " ".join("%d:%s/%s" % h for h in hp))
    ent = collections.Counter()
    grab_ok = grab_bad = 0
    for i in range(1, len(R)):
        r, q = R[i], R[i - 1]
        if r["bs"] != q["bs"] and r["bt"] == q["bt"]:
            ent[r["bs"]] += 1
            if r["bs"] == "b":
                # the player's record is updated before the pool A handlers in a frame: the brain sees this frame's pose (row r), not the previous row
                ok = abs(r["dx"]) < 0x40 and r["pose"] in GRAB_POSES and r["var"] < 4
                grab_ok += ok; grab_bad += not ok
                print("  %5d b  pose %x var %d act %x sub %d dx %d dy %d%s" % (r["d"], r["pose"], r["var"], r["act"], r["sub"], r["dx"], (r["by"] or 0) - r["py"], "" if ok else "  <- rule violated"))
    pred = hit = 0
    for i in range(1, len(R)):
        r, q = R[i], R[i - 1]
        if q["bs"] == "6" and r["bt"] == q["bt"] and q["b1"] is not None and q["b1"] & 0x80 and abs(r["dx"]) < 0x40 and r["pose"] in GRAB_POSES and r["var"] < 4 \
           and r["p88"] & 0x90 == 0 and r["py"] + 0x10 >= r["by"] and r["py"] - 0x20 < r["by"] <= r["py"] + 0x60:
            pred += 1; hit += r["bs"] == "b"
            if r["bs"] != "b": print("  %5d predicted b, got %s (pose %x var %d dx %d)" % (r["d"], r["bs"], r["pose"], r["var"], r["dx"]))
    print(" frames predicting a grab: %d, followed by state b: %d" % (pred, hit))
    fl = [(r["d"], r["f40"]) for i, r in enumerate(R) if r["f40"] is not None and (i == 0 or r["f40"] != R[i - 1]["f40"])]
    if fl: print(" $80040:", " ".join("%d:%02x" % x for x in fl))
    held = sum(1 for r in R if r["act"] in (0xb, 0xc, 0xd))
    poses = collections.Counter(r["pose"] for r in R)
    print(" boss state entries:", dict(sorted(ent.items())))
    print(" grab entries matching the rule: %d, violating: %d" % (grab_ok, grab_bad))
    print(" frames with P1 in action b/c/d (thrown, rising, held): %d of %d" % (held, len(R)))
    print(" P1 pose histogram:", dict(sorted(poses.items())))

if __name__ == "__main__":
    for p in sys.argv[1:]: main(p)
