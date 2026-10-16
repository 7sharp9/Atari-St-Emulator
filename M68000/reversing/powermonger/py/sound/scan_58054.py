"""scan_58054.py [listing]: whole-image scan for every instruction that can reach the word $58054.

1. direct absolute operands in [$57f00, $58080) (any instruction, any operand position);
2. register-based accesses: for each instruction that uses (An), (An)+, -(An), d(An) or d(An,Xn), walk back up to
   40 instructions to the last load of An (lea/movea.l/move.l of an absolute or immediate constant, or adda/addi to it)
   and report it when the loaded base lies in [$57000, $58055] (a base at or below $58054 that an offset or index
   could carry to it), with the displacement printed so a reader can see the reach;
3. immediate longword constants (#$xxxxx) in the same range (address arithmetic such as addi.l #$58016,D0).
The listing is the shared whole-image listing (py/aggr/scan_block_writers.py's listing(), $PM_WORK/aggr/pm_all.asm);
the text segment is $10a6..$1c48a (py/text_segment.py)."""
import os, re, sys
from pathlib import Path

def root():
    p = Path(os.environ["M68000_ROOT"]) if "M68000_ROOT" in os.environ else Path(__file__).resolve()
    while not (p / "tools" / "rdis.py").exists():
        p = p.parent
    return p

ROOT = root()
LST = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "scratchpad" / "pmwork" / "aggr" / "pm_all.asm")
TEXT_LO, TEXT_HI = 0x10a6, 0x1c48a
ins = []
for line in open(LST):
    m = re.match(r"\s+\$([0-9a-f]+): (.*)$", line)
    if m:
        a = int(m.group(1), 16)
        if TEXT_LO <= a < TEXT_HI:
            ins.append((a, m.group(2).strip()))
print("listing %s: %d instructions $%x..$%x" % (LST, len(ins), ins[0][0], ins[-1][0]))

print("== 1. absolute operands in [$57f00,$58080)")
for a, t in ins:
    for v in re.findall(r"(?<![#\w])\$([0-9a-f]{5})(?:\.l)?", t):
        if 0x57f00 <= int(v, 16) < 0x58080:
            print("  $%06x %s" % (a, t))
            break

print("== 3. immediate constants in [$57000,$58080)")
for a, t in ins:
    for v in re.findall(r"#\$([0-9a-f]{5})", t):
        if 0x57000 <= int(v, 16) < 0x58080:
            print("  $%06x %s" % (a, t))

print("== 2. register-based accesses whose base was loaded with a constant in [$57000,$58055]")
for i, (a, t) in enumerate(ins):
    for m in re.finditer(r"(-?\d+)?\((A[0-6])(,[AD]\d\.[wl])?\)(\+)?|-\((A[0-6])\)", t):
        reg = m.group(2) or m.group(5)
        if t.startswith("lea") and m.start() == t.index(" ") + 1 and "," in t[m.end():m.end()+1] and False:
            pass
        for j in range(i - 1, max(-1, i - 40), -1):
            b = ins[j][1]
            mm = re.match(r"(lea|movea\.l|move\.l) #?\$([0-9a-f]+)(\.l)?,%s$" % reg, b)
            if mm:
                v = int(mm.group(2), 16)
                if 0x57000 <= v <= 0x58054:
                    print("  $%06x %-34s base $%x from $%06x (%s)" % (a, t, v, ins[j][0], b))
                break
            if re.search(r",%s$" % reg, b) and not b.startswith(("cmp", "tst")):
                break
            if re.match(r"(bra|jmp|rts|rte)\b", b):
                break
