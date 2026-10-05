"""dump_states.py: one fresh dump (gfxdump.lua, 1 frame: gfx RAM, work RAM, CPS regs, live palette, screenshot) for
every distinct saved-state name found under scratchpad/finalfight (not under stage/, which a bot run was using).
Each state is copied into run/sta/ffightuc/ first (the run dir of ffrun.sh).  Dumps: scratchpad/finalfight/gfx/dump/
st_<name>_1_*.bin.  About 4 s per state."""
import glob, os, shutil, subprocess, sys
from cpsgfx import SCR, ROOT

seen = {}
for p in sorted(glob.glob(os.path.join(SCR, "**", "*.sta"), recursive=True)):
    rel = os.path.relpath(p, SCR)
    if rel.startswith("stage" + os.sep) or rel.startswith("run" + os.sep + "sta"):
        continue
    seen.setdefault(os.path.basename(p)[:-4], p)
dst = os.path.join(SCR, "run", "sta", "ffightuc")
os.makedirs(dst, exist_ok=True)
sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_dump.sh")
only = sys.argv[1:]
for name, p in sorted(seen.items()):
    if only and name not in only:
        continue
    out = os.path.join(SCR, "gfx", "dump", "st_%s_1_ram.bin" % name)
    if os.path.exists(out):
        continue
    shutil.copy(p, os.path.join(dst, name + ".sta"))
    r = subprocess.run(["sh", sh, name, "st_" + name, "1", "600"], capture_output=True, text=True)
    print(name, "ok" if os.path.exists(out) else "FAILED " + r.stdout[-200:] + r.stderr[-200:])
