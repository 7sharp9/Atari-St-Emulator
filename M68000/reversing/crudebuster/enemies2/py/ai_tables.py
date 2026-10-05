"""Dump the attack-choice tables of `$2438a` (the shared fighter AI chooser) for a pool A type.
`$2438a` (read): refreshes the target copy (+42 x, +44 y, +46/+47 target state) via `$22bd0`, then by the y relation of enemy (+12) to the target:
   enemy.y >  target.y + $60  -> table T2 at $24644 : [type] -> [dx>>4 bucket] -> routine             (enemy much lower than the target)
   enemy.y >  target.y - $20  -> table T1 at $24508 : [type] -> [dx>>4] -> [target+46 & $f] -> [target+47] -> routine   (same level)
   otherwise                  -> table T3 at $24780 : [type] -> [dx>>4] -> routine                    (enemy above the target)
dx >= $100 sends the enemy to state 7 (walk). Output: for each bucket the distinct routines (T1: keyed by target state).
usage: ai_tables.py <type hex> [T1|T2|T3|all]"""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
def ok(a): return 0x400 <= a < 0x2c000
T = {"T1": 0x24508, "T2": 0x24644, "T3": 0x24780}
def dump(ty, name):
    base = T[name]
    p1 = l(base + 4 * ty)
    print(f"== type {ty:02x} {name}: table ${p1:06x}")
    for b in range(16):
        p2 = l(p1 + 4 * b)
        if name == "T1":
            rows = {}
            for s in range(16):
                p3 = l(p2 + 4 * s)
                # +47 sub-table: length unknown; read entries until non-code
                subs = []
                for k in range(16):
                    t = l(p3 + 4 * k)
                    if not ok(t): break
                    subs.append(t)
                rows[s] = subs
            groups = {}
            for s, subs in rows.items(): groups.setdefault(tuple(subs), []).append(s)
            for subs, ss in groups.items():
                print(f"  dx>>4={b:x} target46&f in {[hex(x) for x in ss]}: " + " ".join(f"{t:06x}" for t in subs[:8]))
        else:
            print(f"  dx>>4={b:x}: ${p2:06x}")
if __name__ == "__main__":
    ty = int(sys.argv[1], 16)
    which = sys.argv[2] if len(sys.argv) > 2 else "all"
    for n in (T if which == "all" else [which]): dump(ty, n)
