"""hitcheck.py <htap.txt>: replay the $7932 overlap formula on the logged operands and compare with the game.
 x axis passes iff ((dx + s) & 0xffff) <= (2*s & 0xffff), s = hw1 + hw2; the game wrote the y word (a Y line follows) iff x passed.
 y axis likewise with dy, hh1+hh2.  A call 'hit' iff x and y pass; compare with a write to the victim's +60 word in the same frame
 by a handler (PC list printed) after the call (the next X/Y line belongs to the next call)."""
import sys, re, collections
lines = [l.split() for l in open(sys.argv[1])]
def kv(p): return {k: v for k, v in (t.split("=", 1) for t in p[1:] if "=" in t)}
calls = []; cur = None
events = []  # (index in lines, kind, dict)
for n, p in enumerate(lines):
    d = kv(p)
    if p[0] == "X": cur = {"x": d, "y": None, "n": n, "w": []}; calls.append(cur)
    elif p[0] == "Y" and cur is not None and cur["y"] is None and d["f"] == cur["x"]["f"]: cur["y"] = d
    elif p[0] == "V" and cur is not None and d["f"] == cur["x"]["f"] and not cur["x"]["i3"].isdigit():
        base = int(cur["x"]["i3"], 16)
        if int(d["a"], 16) == base + 60 and d["d"] != "0000": cur["w"].append({"i": cur["x"]["i3"], "pc": d["pc"], "d": d["d"]})
    elif p[0] == "W" and d["o"] == "60" and cur is not None and d["f"] == cur["x"]["f"] and d["d"] != "0000": cur["w"].append(d)
    elif p[0] == "W" and d["o"] == "64" and cur is not None and d["f"] == cur["x"]["f"] and d["pc"] in ("00754e", "007750"): cur["g"] = cur.get("g", []) + [d]
def ps(dx, s): return ((dx + s) & 0xffff) <= ((2 * s) & 0xffff)
tot = xok = xmis = ymis = hits = hitw = hitmis = 0
byc = collections.Counter()
bad = []
for c in calls:
    x = c["x"]; tot += 1
    s = int(x["hw1"]) + int(x["hw2"]); px = ps(int(x["dx"]), s)
    gotY = c["y"] is not None
    if px != gotY: xmis += 1; bad.append(("xy", x)); continue
    if not px: continue
    y = c["y"]; s2 = int(y["hh1"]) + int(y["hh2"]); py = ps(int(y["dy"]), s2)
    # observed: a +60 write for this victim index, same frame, in the lines between this call and the next X
    grab = bool(int(x["att45"], 16) & 0x80)
    # a grab attempt (attack id bit 7) completes by writing the attacker's +64 byte at $754e (pool 2/4) or $7750 (player vs player)
    obs = bool(c.get("g")) if grab else any(w["i"] == x["i3"] for w in c["w"])
    pred = px and py
    hits += pred; hitw += obs
    if pred != obs: hitmis += 1; bad.append(("hit pred=%s obs=%s" % (pred, obs), x, y))
    byc[(x["vic18"], x["att18"], "grab" if int(x["att45"],16) & 0x80 else "hit", pred, obs)] += 1
print("calls %d; y-word written iff x predicted to pass: %d/%d agree" % (tot, tot - xmis, tot))
print("calls with x pass (so a y test): %d; predicted full overlap %d; observed victim +60 write %d; pred!=obs %d" % (sum(1 for c in calls if c['y']), hits, hitw, hitmis))
for k, v in sorted(byc.items(), key=str): print("  victim tag %s attacker tag %s %s: overlap pred=%s, +60 written=%s : %d" % (k[0], k[1], k[2], k[3], k[4], v))
for b in bad[:8]: print("BAD", b)
