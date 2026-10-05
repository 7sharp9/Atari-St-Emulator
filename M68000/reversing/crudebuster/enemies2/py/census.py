"""Census of one objlog.txt (lua/objlog.lua): pool A activations vs the static script, flag/scroll-lock events.
usage: census.py <objlog.txt> <level> [rom.bin]
 - activations: a pool A record whose +0 bit 7 went 0 -> 1 between two frames, with the 64 bytes at that frame: (frame, scroll x/y, slot, type, variant, x, y)
 - script match: each script entry (type, variant, x, y) must find an activation with the same type and variant and x, y within 2 (a handler's first run, or the vertical scroll step `$23fc8` in the same frame, moves the record by one pixel); reports matched/total and the unmatched entries
   (dynamic spawns by handlers: activations with no script entry)
 - events: every frame where $80040 / $80041 / $80400 (CB_X first three cells must be 80040? no: F-line fields f40, f41) change"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from scripts_dump import entries, rom as ROM
def main(path, level):
    ent = entries(0x6c000, level)
    last = {}; acts = []; events = []; prev = (None, None); sc = {}
    pf = {}
    for line in open(path):
        p = line.split()
        if p[0] == "F":
            f = int(p[1]); sc[f] = (int(p[3], 16), int(p[4], 16), int(p[5], 16), int(p[6], 16), p[7]); cur = (p[8], p[9])
            if cur != prev: events.append((f, int(p[3], 16), int(p[4], 16), p[8], p[9], p[11:])); prev = cur
        elif p[0] == "A":
            f = int(p[1]); s = int(p[2]); r = bytes.fromhex(p[3])
            key = (f, s)
            pf.setdefault(f, {})[s] = r
    seen = {}
    for f in sorted(pf):
        for s, r in pf[f].items():
            was = pf.get(f - 1, {}).get(s)
            if was is None or r[2] != was[2]:
                # new activation (slot empty last frame, or re-used with another type)
                acts.append((f, s, r))
    out = []
    used = set()
    matched = 0; unm = []
    for (p, trig, ty, var, x, y) in ent:
        hit = None
        for i, (f, s, r) in enumerate(acts):
            if i in used: continue
            if r[2] == ty and r[16] == var and abs(int.from_bytes(r[8:10], "big") - x) <= 2 and abs(int.from_bytes(r[12:14], "big") - y) <= 2:
                hit = i; break
        if hit is None: unm.append((p, trig, ty, var, x, y))
        else: used.add(hit); matched += 1
    print(f"level {level}: {len(ent)} script entries, {matched} matched by an activation with the same type/variant and x, y within 2 (the handler's first run or a scroll step shifts the position by 1); {len(acts)} activations in the log")
    for i, (f, s, r) in enumerate(acts):
        scx, scy = sc[f][0], sc[f][1]
        tag = "script" if i in used else "dynamic"
        print(f"  frame {f:5d} scroll x={scx:04x} y={scy:04x} slot {s:2d} type {r[2]:02x} var {r[16]:02x} x={int.from_bytes(r[8:10],'big'):04x} y={int.from_bytes(r[12:14],'big'):04x} hp={r[5]:2d} {tag}")
    print("unmatched script entries:", [(f"{p:06x}", f"{t:04x}", f"{ty:02x}/{v:02x}") for p, t, ty, v, x, y in unm])
    print("flag events ($80040 $80041 + extra cells):")
    for e in events: print("  frame %d scroll x=%04x y=%04x f40=%s f41=%s %s" % e)
if __name__ == "__main__": main(sys.argv[1], int(sys.argv[2]))
