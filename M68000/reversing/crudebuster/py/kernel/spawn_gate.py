"""Gate: the two level-script lists ($6c000 enemies, $6d000 props) spawn exactly their ROM entries.

Input: a spawnlog.txt from lua/spawnlog.lua and the decrypted program ROM dump.
For every advance of a script pointer ($81e06 list A, $81e0a list B) it takes the 8-byte ROM entries the pointer
passed over, and finds, among the slots that became active in the same frame, one whose
record bytes {+2 type, +16 variant, +8 x word, +12 y word} equal the entry's {type, variant, x, y}
(list B clears bit 7 of the entry's type byte first: `andi.b #$7f`, and its slot pool starts at 0 or $18).
Prints the match count; entries that found no new slot are listed (pool full: the pointer still advances).
usage: spawn_gate.py <spawnlog.txt> [rom.bin]
"""
import re, sys, os, collections

root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
frames = collections.defaultdict(lambda: {"A": [], "B": [], "S": []})
pa = pb = None
events = []
for line in open(sys.argv[1]):
    p = line.split()
    if p[0] == "P":
        f = int(p[1]); a = int(p[2][2:], 16); b = int(p[3][2:], 16)
        events.append(("P", f, a, b))
    elif p[0] == "S":
        f = int(p[1]); slot = int(p[2][5:]); rec = bytes.fromhex(p[3])
        events.append(("S", f, slot, rec))
# first pointer values: the lists start when the level loads; entries before the first logged pointer are unseen
cur = {"A": None, "B": None}
spawns_by_frame = collections.defaultdict(list)
for e in events:
    if e[0] == "S": spawns_by_frame[e[1]].append(e)
total = matched = 0
unmatched = []
for e in events:
    if e[0] != "P": continue
    _, f, a, b = e
    for lst, new in (("A", a), ("B", b)):
        old = cur[lst]
        cur[lst] = new
        if old is None or new == old or new < old: continue
        for ent in range(old, new, 8):
            t, v = rom[ent + 2], rom[ent + 3]
            if lst == "B": t &= 0x7f
            x = int.from_bytes(rom[ent + 4:ent + 6], "big"); y = int.from_bytes(rom[ent + 6:ent + 8], "big")
            total += 1
            ok = False
            for s in spawns_by_frame[f]:
                rec = s[3]
                if rec[2] == t and rec[16] == v and int.from_bytes(rec[8:10], "big") == x and int.from_bytes(rec[12:14], "big") == y:
                    ok = True; break
            if ok: matched += 1
            else: unmatched.append((f, lst, hex(ent), rom[ent:ent + 8].hex()))
print("script entries consumed: %d, matched to a new slot in the same frame: %d" % (total, matched))
for u in unmatched[:40]: print("  unmatched", u)
