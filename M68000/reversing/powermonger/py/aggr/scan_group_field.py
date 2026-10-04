"""Whole-image scan for every instruction that can touch the group aggression word (record +148+2k,
group view 72) in PowerMonger's group table $51538 (5 records of $13c bytes).

Method (static, flow-insensitive within a routine):
  1. the listing is a fresh `disassemble.py --snap <snap> --all 1000 1c600` (the text segment ends at
     $1c488; the last routine $1c3e6 is inside the listing).
  2. a light abstract interpreter tracks address and data registers derived from the table base:
        ('G', k)   = $51538 + k          (lea $51538.l / move.l #$51538 / lea d(An) / addq / adda #imm)
        ('GI', k)  = $51538 + k + unknown index (adda.w Dn, lea d(An,Dn))
     state is reset at every routine start (names from powermonger.sym + powermonger_orig.sym) and
     registers are overwritten by any other write to them.
  3. every memory operand d(An)/d(An,Xn) with An in the family gives e = k + d, reported with its
     instruction and routine; operands with a literal displacement 72/73 or 148/149 on ANY base are
     reported separately (covers a group pointer received in a register from a caller).
  4. other forms that can touch the table without a displacement literal: absolute operands inside
     [$515cc, $5ff..] windows of the table, post-increment/pre-decrement/(An) on a derived register,
     and movem/clr loops over the table.

LIMIT (found the hard way): this scan names the table only through its base $51538 and the displacements 72/148. A block clear or copy that covers
the table from a lower base (`_clear_a` $10768: `lea $3f364.l,A0 ... clr.l (A0)+` up to #$57ff8, run by the land build) is invisible to it;
`scan_block_writers.py` lists those, and the disk save/load (`_dda_loa`/`_dda_sav`, FDC DMA of $3f768..$58368) moves the table as raw sectors.

Usage: python3 scan_group_field.py [listing]   (default: $PM_WORK/aggr/pm_all.asm, regenerated from scratchpad/pm123/win/m1_ready.snap when missing)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "aggr"
SNAP = ROOT / "scratchpad" / "pm123" / "win" / "m1_ready.snap"


def listing(arg=None):
    """The whole-image listing: the argument if given, else $PM_WORK/aggr/pm_all.asm, regenerated (about a second) from m1_ready.snap when missing.
    The text segment ends at $1c488 (`_set_ser` $1c3e6 and its table); the listing runs to $1c600."""
    if arg:
        return arg
    out = WORK / "pm_all.asm"
    if not out.exists():
        WORK.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            subprocess.run([sys.executable, str(ROOT / "tools" / "disassemble.py"), "--snap", str(SNAP), "--all", "1000", "1c600"], stdout=f, check=True, cwd=ROOT)
    return str(out)
LST = listing(sys.argv[1] if len(sys.argv) > 1 else None)
G = 0x51538
REC = 0x13c

# routine starts from both symbol files
starts = set()
for fn in ("powermonger.sym", "powermonger_orig.sym"):
    p = os.path.join(str(ROOT), "reversing", "powermonger", fn)
    for line in open(p):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and "# D" not in line and "# B" not in line:
            try:
                starts.add(int(parts[0], 16))
            except ValueError:
                pass

insns = []
for line in open(LST):
    m = re.match(r"\s+\$([0-9a-f]+): (.*)$", line)
    if m:
        insns.append((int(m.group(1), 16), m.group(2).strip()))

EA_DISP = re.compile(r"(-?\d+)\((A[0-7])(?:,([AD][0-7])\.[wl])?\)")
reg_state = {}


def setreg(r, v):
    if v is None:
        reg_state.pop(r, None)
    else:
        reg_state[r] = v


def split_ops(s):
    # split on commas not inside parentheses
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def num(t):
    t = t.strip().lstrip("#")
    neg = t.startswith("-")
    t = t.lstrip("-")
    v = int(t[1:], 16) if t.startswith("$") else int(t)
    return -v if neg else v


rows = []  # (addr, routine, text, e, kind, note)
lit = []   # literal 72/73/148/149 displacement on any base
other = []
routine = None
for addr, text in insns:
    if addr in starts:
        routine = addr
        reg_state.clear()
    mnem, _, rest = text.partition(" ")
    ops = split_ops(rest) if rest else []

    # literal displacements on any base
    for m in EA_DISP.finditer(text):
        d = int(m.group(1))
        if d in (72, 73, 148, 149):
            lit.append((addr, routine, text))

    # absolute operands in the table
    for m in re.finditer(r"\$([0-9a-f]{5,6})\.[lw]", text):
        a = int(m.group(1), 16)
        if G <= a < G + 5 * REC and "lea" not in mnem:
            other.append((addr, routine, text, "absolute inside table"))
    if re.search(r"#\$5[0-9a-f]{4}\b", text) and "lea" not in mnem:
        for m in re.finditer(r"#\$(5[0-9a-f]{4})\b", text):
            a = int(m.group(1), 16)
            if G - 4 <= a < G + 5 * REC:
                other.append((addr, routine, text, "immediate inside table"))

    # memory operand through the family
    for m in EA_DISP.finditer(text):
        d, an, ix = int(m.group(1)), m.group(2), m.group(3)
        v = reg_state.get(an)
        if v:
            kind, k = v
            if ix:
                kind = "GI"
            rows.append((addr, routine, text, k + d, kind))
    for an in set(re.findall(r"\((A[0-7])\)\+|-\((A[0-7])\)", text)):
        for a in an:
            if a and a in reg_state:
                other.append((addr, routine, text, f"auto-inc/dec on {a} = {reg_state[a]}"))
    for an in re.findall(r"(?<![-\d(])\((A[0-7])\)(?!\+)", text):
        if an in reg_state:
            rows.append((addr, routine, text, reg_state[an][1], reg_state[an][0]))

    # state updates
    def val(op):
        op = op.strip()
        return reg_state.get(op)

    if mnem in ("lea",) and len(ops) == 2:
        dst = ops[1].strip()
        src = ops[0].strip()
        if src == "$51538.l":
            setreg(dst, ("G", 0))
        else:
            m = EA_DISP.fullmatch(src)
            if m and m.group(2) in reg_state:
                kind, k = reg_state[m.group(2)]
                setreg(dst, ("GI" if m.group(3) else kind, k + int(m.group(1))))
            else:
                setreg(dst, None)
    elif mnem in ("move.l", "movea.l") and len(ops) == 2:
        dst = ops[1].strip()
        src = ops[0].strip()
        if src == "#$51538":
            setreg(dst, ("G", 0))
        elif src in reg_state and re.fullmatch(r"[AD][0-7]", dst):
            setreg(dst, reg_state[src])
        elif re.fullmatch(r"[AD][0-7]", dst):
            setreg(dst, None)
    elif mnem in ("adda.w", "adda.l", "add.w", "add.l", "addi.w", "addi.l", "addq.w", "addq.l") and len(ops) == 2:
        dst = ops[1].strip()
        src = ops[0].strip()
        if dst in reg_state:
            kind, k = reg_state[dst]
            if src.startswith("#"):
                try:
                    setreg(dst, (kind, k + num(src)))
                except ValueError:
                    setreg(dst, ("GI", k))
            else:
                setreg(dst, ("GI", k))
    elif mnem in ("subq.w", "subq.l", "subi.w", "subi.l", "suba.w", "suba.l") and len(ops) == 2:
        dst = ops[1].strip()
        src = ops[0].strip()
        if dst in reg_state:
            kind, k = reg_state[dst]
            if src.startswith("#"):
                if src.lstrip("#") == "$51538":
                    setreg(dst, None)
                else:
                    setreg(dst, (kind, k - num(src)))
            else:
                setreg(dst, ("GI", k))
    elif mnem.startswith(("move", "clr", "ext", "mulu", "muls", "divu", "and", "or", "eor", "lsl", "lsr", "asl", "asr", "swap",
                          "moveq", "neg", "not", "sub")) and ops:
        dst = ops[-1].strip()
        if re.fullmatch(r"[AD][0-7]", dst) and dst in reg_state:
            if mnem.startswith("move.w") or mnem.startswith("moveq") or mnem.startswith("clr") or mnem.startswith("mulu") or mnem.startswith("divu") or mnem.startswith("and"):
                setreg(dst, None)
    elif mnem in ("jsr", "bsr"):
        # callee may clobber; keep A2-A6/D3-D7 (movem-saved), drop scratch D0-D2/A0-A1
        for r in ("D0", "D1", "D2", "A0", "A1"):
            reg_state.pop(r, None)

# ---- report
print(f"instructions: {len(insns)}  from ${insns[0][0]:x} to ${insns[-1][0]:x}")
print("\n== literal displacement 72/73/148/149 on ANY address register ==")
for a, r, t in lit:
    print(f"  ${a:06x} (in ${r:06x}) {t}" if r else f"  ${a:06x} {t}")
print("\n== absolute / immediate operands inside the table ==")
for a, r, t, n in other:
    print(f"  ${a:06x} (in ${r:06x}) {t}   [{n}]" if r else f"  ${a:06x} {t} [{n}]")
print("\n== family accesses with e = k + d in the aggression windows (72..83 group view, 148..159 record view) ==")
for a, r, t, e, kind in rows:
    if 72 <= e <= 83 or 148 <= e <= 159:
        print(f"  ${a:06x} (in ${r:06x}) {t}   e={e} {kind}")
print("\n== histogram of e for all family accesses (kind G exact / GI indexed) ==")
from collections import Counter
c = Counter((kind, e) for _, _, _, e, kind in rows)
for (kind, e), n in sorted(c.items(), key=lambda x: (x[0][0], x[0][1])):
    print(f"  {kind:2s} e={e:5d}  n={n}")
