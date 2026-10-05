"""Decode the longword state tables inside pool A type handlers.
For every `lea N(PC),A0 / movea.l 0(A0,D0.w),A0 / jsr (A0)` (D0 = state << 2) in a handler range, reads the table at the lea target:
entries are 32-bit code addresses; the table ends at the lowest entry value that lies after the table start (code follows the table).
usage: handler_tables.py <handler_lo> <handler_hi>   (hex)   prints table address, entry index -> target"""
import os, sys, re
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
lin = {}
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lin[int(a[1:], 16)] = ins
def l(a): return int.from_bytes(rom[a:a+4], "big")
def tables(lo, hi):
    out = []
    for a in sorted(k for k in lin if lo <= k < hi):
        m = re.match(r"lea (-?\d+)\(PC\) == \$([0-9a-f]+),A0", lin[a])
        if not m: continue
        # next instruction(s): movea.l 0(A0,D0.w),A0
        nxt = [lin.get(a + 4), lin.get(a + 6)]
        if any(n and n.startswith("movea.l 0(A0,D0.w),A0") for n in nxt):
            t = int(m.group(2), 16)
            ents = []
            lowest = 1 << 30
            p = t
            while p < lowest and p + 4 <= len(rom):
                v = l(p)
                if not (0x400 <= v < 0x2c000 and v % 2 == 0): break
                ents.append(v); p += 4
                if v > t: lowest = min(lowest, v)
            out.append((a, t, ents))
    return out
if __name__ == "__main__":
    lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
    for a, t, ents in tables(lo, hi):
        print(f"dispatch at ${a:06x}: table ${t:06x} ({len(ents)} entries)")
        for i, e in enumerate(ents): print(f"   [{i:02x}] ${e:06x}")
