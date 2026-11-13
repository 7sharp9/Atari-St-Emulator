"""Populous II: raise and lower driven by a real mouse click, against a no-click control.

From p2_game_60m the pointer is moved onto the land (dx 50, dy -70: screen (200,110), cursor cell
(11,30) with the raise/lower power $47372 = 2 selected), then three runs of the same length:
no click, a left click, a right click. For each click run the corner grid (corners.py) is compared
with the control's and with the raise_gate.py model of raise_point / lower_point applied to the
control's grid at the cursor corner, and the command the main loop writes into the local
player's record ($473c4 -> $473b0: +1 command, +2 x, +3 y) is read from a watch.

usage: uv run python reversing/populous2/py/click_ab.py [outdir]
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from corners import ROOT, corner_grid  # noqa: E402
from raise_gate import model  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

SNAP = "scratchpad/populous2/anchors/p2_game_60m.snap"
CLICKS = {"ctl": "s 60000", "left": "mouse down l\ns 60000\nmouse up l", "right": "mouse down r\ns 60000\nmouse up r"}


def drive(name, click, out):
    snap = f"{out}/{name}.snap"
    script = (f"mouse move 50 -70\ns 200000\nwatch 473b0 10\n{click}\ns 400000\nunwatch\n"
              f"snap {snap}\nq\n")
    dll = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
    r = subprocess.run(["dotnet", "exec", dll, "resume", SNAP, "repl"], input=script,
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0 or not os.path.exists(os.path.join(ROOT, snap)):
        sys.exit(f"{name}: run failed\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    cmds = re.findall(r"pc=\$(01320c|013208|013210|01332e|013332|013336) WriteByte \$(\w+) <- \$(\w+)", r.stderr)
    ram, _ = load_ram(os.path.join(ROOT, snap))
    return ram, cmds


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "scratchpad/populous2/click_ab"
    os.makedirs(os.path.join(ROOT, out), exist_ok=True)
    for f in ("ctl", "left", "right"):
        p = os.path.join(ROOT, out, f + ".snap")
        if os.path.exists(p):
            os.remove(p)
    rc, c0 = drive("ctl", CLICKS["ctl"], out)
    Hc, dis, _ = corner_grid(rc)
    mana = lambda r: int.from_bytes(r[0x470FE:0x47102], "big")  # side 1 record long +0
    print(f"control: command writes {c0}; corner disagreements {dis}")
    for name, up in (("left", True), ("right", False)):
        rk, cmds = drive(name, CLICKS[name], out)
        Hk, dis, _ = corner_grid(rk)
        vals = {a: int(v, 16) for _pc, a, v in cmds}
        cmd, x, y = vals.get("000473b1"), vals.get("000473b2"), vals.get("000473b3")
        changed = sum(Hc[k] != Hk[k] for k in Hc)
        Hm, _ = model(Hc, x, y, up) if x is not None else (None, 0)
        neigh = sum(model(Hc, x + dx, y + dy, up)[0] == Hk for dx, dy in ((1, 0), (0, 1), (1, 1)))
        print(f"{name}: command {cmd} at ({x},{y}) from {sorted({p for p, _, _ in cmds})}; "
              f"corners changed vs control {changed}; model at the cursor corner equal {Hm == Hk}; "
              f"control models at (x+1,y),(x,y+1),(x+1,y+1) equal {neigh}/3; "
              f"mana {mana(rc) - mana(rk)} below control (20 per corner = {20 * changed})")


if __name__ == "__main__":
    main()
