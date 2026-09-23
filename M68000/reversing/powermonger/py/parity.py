"""pm_render_ref's inline frame vs the F# port (score.fsx PORT_OUT, screen space, 255 = not drawn)."""
import sys, io, contextlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
import pm_render_ref as pr
with contextlib.redirect_stdout(io.StringIO()):
    idx, cov, ref, R = pr.render_faithful(Path(sys.argv[1]), None)
port = open(sys.argv[2], 'rb').read()
both = same = only_py = only_fs = 0
for i in range(320 * 200):
    a, b = cov[i], port[i] != 255
    if a and b:
        both += 1; same += idx[i] == port[i]
    elif a: only_py += 1
    elif b: only_fs += 1
print(f"covered by both {both}, identical {same}; only python {only_py}, only F# {only_fs}")
