"""Python half of the real-record entity cross-check: pm_render_ref.draw_entities
on the same frame RAM as ent_fs.fsx, all ported byte6 categories (cats=None),
covered entity pixels in $XCHECK_OUT/ent_py.txt.
    python ent_py.py [frame.ram]"""
import os, sys
from pathlib import Path
_here = Path(__file__).resolve().parent
_root = next(p for p in _here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(_root / "tools"))
OUT = Path(os.environ.get("XCHECK_OUT", "."))
import pm_render_ref as PR
from pathlib import Path

W, H = 320, 200
PR.W, PR.H = W, H
R = PR.load_ram(Path(sys.argv[1]) if len(sys.argv) > 1 else _root / "scratchpad/pm88_f1.ram")
idx = bytearray(W * H); cov = bytearray(W * H); ecov = bytearray(W * H)
PR.draw_entities(idx, cov, R, ecov, cats=None)
with open(OUT / "ent_py.txt", "w") as f:
    for i in range(W * H):
        if ecov[i]:
            f.write(f"{i%W},{i//W},{idx[i]}\n")
print("PY:", sum(ecov), "covered entity px, inset", R["x_inset"], "cam", R["cam"])
