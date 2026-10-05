"""Experiment E: score per hit / knock-down / kill.  From the expB lab logs: P1's score (BCD longword at $8013c) change in the 8 frames after each hit poke,
grouped by (type, var, strength, outcome) and compared with the table at $24952 (score index per type: [hurt, knocked, killed, sound]) and the BCD table at $4012+4*i.
usage: expE.py"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames
import expB_kd
ROM = open(os.path.join(os.path.dirname(__file__), "../../../../scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def bcd(b): return int(b.hex())
def pts(i): return bcd(ROM[0x4012 + 4*i: 0x4016 + 4*i]) if i else 0
agg = collections.defaultdict(collections.Counter)
for d in sorted(glob.glob("out/expB/*")):
    tag = os.path.basename(d); t, v, V = tag.split("_"); t = int(t)
    if V != "80": continue
    p = os.path.join(d, "enemylog.txt")
    if not os.path.exists(p): continue
    fr = list(frames(p)); byf = {f["f"]: f for f in fr}; off = fr[0]["f"]
    for l in open(p):
        if not (l.startswith("E ") and " hit " in l): continue
        h = int(l.split()[1]) + off
        a, b = byf.get(h), byf.get(h + 8)
        if a is None or b is None or 0 not in a["R"]: continue
        r0 = a["R"][0]
        ds = bcd(b["P"][0x3c:0x40]) - bcd(a["P"][0x3c:0x40])
        hp1 = byf.get(h + 3)
        hp1 = hp1["R"][0][5] if hp1 and 0 in hp1["R"] else None
        agg[(t, v)][(("hit" if hp1 is not None and hp1 < r0[5] else "no-hit"), ds)] += 1
for k in sorted(agg):
    ti = ROM[0x24952 + 4*k[0]: 0x24952 + 4*k[0] + 4]
    print(k, "table idx hurt/knock/kill/snd", list(ti), "-> points hurt %d knock %d kill %d" % (pts(ti[0]), pts(ti[1]), pts(ti[2])), dict(agg[k]))
