"""Shared helpers for the Black Tiger SECRETS scripts.
ROOT = M68000/ (from __file__, override M68000_ROOT); WORK = $BT_WORK (default
M68000/scratchpad/black_tiger); OUT = $WORK/agents/secrets."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def _root():
    d = HERE
    while d != os.path.dirname(d):
        if os.path.basename(d) == "M68000": return d
        d = os.path.dirname(d)
    return os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ROOT = os.environ.get("M68000_ROOT") or _root()
WORK = os.environ.get("BT_WORK") or os.path.join(ROOT, "scratchpad", "black_tiger")
OUT = os.path.join(WORK, "agents", "secrets")
DLL = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
DISK = os.path.join(WORK, "bt_auto.st")
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.makedirs(OUT, exist_ok=True)

def run_repl(snap, script, log=None):
    """resume <snap> repl with script on stdin. ATARI_NOTRACE=1 always."""
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl", "--disk-a", DISK],
                       input=script, text=True, capture_output=True, env=env, cwd=ROOT)
    out = p.stdout + p.stderr
    if log:
        with open(log, "w") as f: f.write(out)
    return out

def ram(path):
    from disassemble import ram_from_snap
    return ram_from_snap(path)

def strings(mem, lo, hi, minlen=4):
    out=[]; cur=bytearray(); start=lo
    for a in range(lo,hi):
        b=mem[a]
        if 32<=b<127 or b in (10,13,9):
            if not cur: start=a
            cur.append(b)
        else:
            if len(cur)>=minlen: out.append((start,bytes(cur).decode('latin1')))
            cur=bytearray()
    return out

def render_buffer(snap, out_png, base=None):
    """Render screen buffer `base` (default: the live shifter base) of a .snap with the live palette."""
    from gfxview import load_ram, load_video_regs
    from PIL import Image
    ram_, _ = load_ram(snap); regs = load_video_regs(snap)
    b = regs["base"] if base is None else base
    pal = [((w >> 8 & 7) * 36, (w >> 4 & 7) * 36, (w & 7) * 36) for w in regs["palette_words"]]
    img = Image.new("RGB", (320, 200)); px = img.load()
    for y in range(200):
        for xg in range(20):
            a = b + y * 160 + xg * 8
            ws = [(ram_[a + 2 * i] << 8) | ram_[a + 2 * i + 1] for i in range(4)]
            for bit in range(16):
                c = 0
                for p in range(4): c |= ((ws[p] >> (15 - bit)) & 1) << p
                px[xg * 16 + bit, y] = pal[c]
    img.save(out_png)
    return b
