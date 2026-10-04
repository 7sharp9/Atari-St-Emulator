"""Shared paths and a tiny REPL runner for the Black Tiger systems scripts.
ROOT = M68000/ (derived from this file, override with M68000_ROOT); WORK = $BT_WORK (default
M68000/scratchpad/black_tiger); OUT = $WORK/agents/systems (scripts write their data there)."""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
WORK = os.environ.get("BT_WORK") or os.path.join(ROOT, "scratchpad", "black_tiger")
OUT = os.path.join(WORK, "agents", "systems")
DLL = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
DISK = os.path.join(WORK, "bt_auto.st")
sys.path.insert(0, os.path.join(ROOT, "tools"))

def run_repl(snap, script, env_extra=None, log=None):
    """`resume <snap> repl` with `script` on stdin (ATARI_NOTRACE=1 always); returns stdout+stderr."""
    env = dict(os.environ, ATARI_NOTRACE="1")
    if env_extra: env.update(env_extra)
    p = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl", "--disk-a", DISK],
                       input=script, text=True, capture_output=True, env=env, cwd=ROOT)
    out = p.stdout + p.stderr
    if log:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "w") as f: f.write(out)
    return out

def ram_from_snap(path):
    from disassemble import ram_from_snap as r
    return r(path)

def level_snap(level):
    """Start snapshot for level index 0..7: play_start.snap, or agents/systems/lvl<k>.snap
    (made by drive_levels.py with the built-in level skip, 6M steps after the level load)."""
    return os.path.join(WORK, "play_start.snap") if level == 0 else os.path.join(OUT, f"lvl{level}.snap")

def exits():
    """Level-exit cells (map object kind $20) from agents/mechanics/special_items.txt: {level_index: (x, y)}."""
    res, lvl = {}, None
    for l in open(os.path.join(WORK, "agents", "mechanics", "special_items.txt")):
        m = re.match(r"level (\d+)", l)
        if m: lvl = int(m.group(1)) - 1
        m = re.match(r"\s+item 20 x1\s+\((\d+),(\d+)\)", l)
        if m: res[lvl] = (int(m.group(1)), int(m.group(2)))
    return res

def shops():
    res, lvl = {}, None
    for l in open(os.path.join(WORK, "agents", "mechanics", "special_items.txt")):
        m = re.match(r"level (\d+)", l)
        if m: lvl = int(m.group(1)) - 1
        m = re.match(r"\s+item 11 x\d+\s+(.*)", l)
        if m: res[lvl] = [tuple(map(int, c.split(","))) for c in re.findall(r"\((\d+,\d+)\)", m.group(1))]
    return res
