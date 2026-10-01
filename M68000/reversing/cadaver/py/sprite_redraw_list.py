"""sprite_redraw_list.py - live check of the overlap list `$00d856` builds (graphics.md 5k).

At `$00d8b6` the list at 340(A5) must equal [A0] + [B in table-index order : B live and drawn, B not in row[A0]
(68(A5), see sprite_depth_graph.py), the second redraw pass (2454(A5) = 0) takes any B while the first takes only
B with state byte 42 = 5, and the screen rectangles (x 18/46, y 20/23) of A0 and B overlap].

Needs the existing DLL (ATARI_NOTRACE=1 is set by Repl).  From M68000/ with .venv:
    python reversing/cadaver/py/sprite_redraw_list.py scratchpad/cadaver/gameplay_empire.snap 04:25,02:40,08:25 100000
Args: snapshot, `bits:hits` phases (joystick bits 01 up 02 down 04 left 08 right; hits = $d8b6 hits per phase),
steps to settle after each joystick change.  CAVERN run (hero walking left, down, right): 90/90 lists match,
40 with more than one entry, 4 where a row excluded a screen-overlapping entity.
"""
import os, re, sys
ROOT = os.environ.get("M68000_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
sys.path.insert(0, os.path.join(ROOT, "reversing", "cadaver", "py", "secrets"))
from repl import Repl, A5  # noqa: E402

snap = sys.argv[1]
seq = [(int(a, 16), int(b)) for a, b in (x.split(":") for x in sys.argv[2].split(","))]
settle = int(sys.argv[3])
r = Repl(snap)
tab, occ, n = r.l(A5 + 56), r.l(A5 + 68), r.w(A5 + 1152)


def reg(name):
    for line in r.cmd("r"):
        for m in re.finditer(r"([DA]\d):\s*([0-9A-Fa-f]{8})", line):
            if m.group(1) == name: return int(m.group(2), 16)


def state():
    t, o = r.mem(tab, 0x46 * n), r.mem(occ, 16 * n)
    E, rows = [], []
    for i in range(n):
        e = t[0x46 * i:0x46 * i + 0x46]
        sx = int.from_bytes(e[18:20], "big")
        E.append(dict(i=i, live=not (e[0] == 0xFF and e[1] == 0xFF) and e[:4] != b"\xff\xff\xff\xfe", sx=sx,
                      ex=int.from_bytes(e[46:48], "big"), sy=e[20], ey=e[23], st=e[42], drawn=sx < 0x8000))
        row = o[16 * i:16 * i + 16]
        rows.append({k for k in range(96) if row[4 + k // 8] >> (k % 8) & 1})
    return E, rows


tot = match = multi = excl = 0
for bits, hits in seq:
    r.joy(bits); r.cmd(f"s {settle}")
    for _ in range(hits):
        r.cmd("bpc d8b6 1 600000")
        if r.pc() != 0xD8B6: print("no hit"); break
        E, rows = state()
        i0 = (reg("A0") - tab) // 0x46
        flag = r.b(A5 + 2454)
        lst, p = [], r.l(A5 + 340)
        while (v := r.l(p)) != 0xFFFFFFFF:
            lst.append((v - tab) // 0x46); p += 4
        A = E[i0]
        ovl = lambda B: A["sy"] < B["ey"] and B["sy"] < A["ey"] and A["sx"] < B["ex"] and B["sx"] < A["ex"]
        cand = [B for B in E if B["i"] != i0 and B["live"] and B["drawn"] and ovl(B)]
        exp = [i0] + [B["i"] for B in cand if B["i"] not in rows[i0] and not (flag and B["st"] != 5)]
        tot += 1; multi += len(lst) > 1; excl += any(B["i"] in rows[i0] for B in cand)
        if exp == lst: match += 1
        else: print(f"MISMATCH A0={i0} flag2454={flag} live={lst} expected={exp}")
print(f"lists with >1 entry {multi}; lists where a row excluded a screen-overlapping entity {excl}")
print(f"list rule matches {match}/{tot}")
r.close()
