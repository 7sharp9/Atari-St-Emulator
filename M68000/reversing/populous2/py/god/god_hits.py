"""hits census of the computer god's stages in the side-1-computer arm (controller word poked, nothing else), with
the model's path counts over the same 1000 ticks as the cross-check, and $25652 itself as the positive control.

usage: uv run python reversing/populous2/py/god/god_hits.py <snap> [ticks]"""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, "tools", "rdis.py")):
    d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stclient import StServer
from god_model import God
import collections
snap = sys.argv[1]; ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
s = StServer(ROOT)
s("load", snapshot=snap); s("poke", addr=0x47118, width=2, value=4)
step0 = s("regs")["step"]
paths = collections.Counter()
for t in range(ticks):
    r = s("run", max_steps=3_000_000, until_pc=0x25652)
    ram = s.read(0, 0x48000); rg = s("regs")
    m = God(ram, int(rg["d4"].lstrip("$"), 16), int(rg["d5"].lstrip("$"), 16)); m.run()
    paths.update(m.paths)
    for x, n, p in m.log:
        if p: paths["post_" + n] += 1
N = r["step"] - step0 + 5000
s("load", snapshot=snap); s("poke", addr=0x47118, width=2, value=4)
names = {0x25652: "ai_run_sides (positive control)", 0x25770: "level", 0x259ba: "release", 0x25a32: "power", 0x25bf4: "magnet",
         0x25b5e: "power post", 0x25d08: "magnet cmd 8", 0x25dac: "mode byte post", 0x25a18: "release post", 0x25878: "level post",
         0x25756: "walker mailbox post", 0x25bf4 + 0: "magnet"}
h = s("hits", steps=N, addrs=list(names))
print(f"steps {N}; model path counts over the same {ticks} entries:")
rows = {k: v for k, v in sorted(paths.items())}
print(" ", rows)
print("hits (count of executions of the address):")
print(h)
s.close()
