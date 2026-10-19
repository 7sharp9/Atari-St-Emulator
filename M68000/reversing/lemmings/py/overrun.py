"""Walk off the end of the one-player levels (extras.md "Levels"): type the access code for level index N
(120..159 are the Mayhem 30 clone), start the level, force a win, and print the 50(A5) level counter and a
screenshot of each stage.
Run from M68000/:  uv run python reversing/lemmings/py/overrun.py [N=159] [OUTDIR]
Needs scratchpad/lemmings/interesting/menu.snap (the menu) and the disk image."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import codes
ROOT = os.getcwd()
DISK = os.path.expanduser("~/Library/CloudStorage/Dropbox/Daves/ST games/Lemmings (1990)(Psygnosis)[cr BBC][a].st")
MENU = "scratchpad/lemmings/interesting/menu.snap"
SC = dict(zip("QWERTYUIOP", range(0x10, 0x1a))); SC.update(zip("ASDFGHJKL", range(0x1e, 0x27))); SC.update(zip("ZXCVBNM", range(0x2c, 0x33)))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 159
OUT = sys.argv[2] if len(sys.argv) > 2 else "scratchpad/lemmings/overrun"
os.makedirs(OUT, exist_ok=True)

def step(src, dst, cmds):
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", src, "repl", "--disk-a", DISK],
                       input="\n".join(cmds + ["snap " + dst, "q"]) + "\n", capture_output=True, text=True, env=env)
    png = dst.replace(".snap", ".png")
    subprocess.run(["python3", "tools/snap_render.py", dst, png], capture_output=True)
    lvl = [l for l in p.stdout.splitlines() if l.strip() and all(len(t) == 2 for t in l.split())]
    return lvl

def click(): return ["mouse down l", "s 60000", "mouse up l"]
def mv(x, y):
    c = []
    for v, ax in ((x, 0), (y, 1)):
        while v > 0:
            d = min(v, 100); c += ["mouse move %d 0" % d if ax == 0 else "mouse move 0 %d" % d, "s 12000"]; v -= d
    return c

code = codes.gen(N)
print("n =", N, "code", code, codes.check(code))
typed = ["mouse move -127 -127", "s 30000"] * 3 + mv(160, 144) + ["s 60000"] + click() + ["s 3000000"]
for ch in code: typed += ["kbd %02x" % SC[ch], "s 30000", "kbd %02x" % (SC[ch] | 0x80), "s 30000"]
typed += ["s 3000000", "m 27306 2"]                       # 50(A5) = $27306 (A5 = $272d4)
print("typed", step(MENU, f"{OUT}/typed.snap", typed))
start = ["mouse move -127 0", "s 12000", "mouse move -50 0", "s 12000", "mouse move 30 0", "s 12000", "s 60000"] + click() + ["s 20000000"]
step(f"{OUT}/typed.snap", f"{OUT}/brief.snap", start)       # briefing of level N
play = click() + ["s 30000000", "w 2730a 00000000",         # 54(A5) saved %, 56(A5) required % := 0, so any end is a win
                  "kbd 01", "s 30000", "kbd 81", "s 30000", "s 3000000", "m 27306 2"]
print("after win", step(f"{OUT}/brief.snap", f"{OUT}/won.snap", play))   # result screen with the next code
nxt = click() + ["s 6000000"] + click() + ["s 20000000", "m 27306 2"]
print("next briefing", step(f"{OUT}/won.snap", f"{OUT}/next.snap", nxt))
