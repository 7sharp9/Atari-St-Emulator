"""Shared helpers for the Black Tiger mechanics agent (repo root from __file__, BT_WORK override)."""
import os, struct, subprocess, sys, re

ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))   # M68000/
WORK = os.environ.get("BT_WORK") or os.path.join(ROOT, "scratchpad", "black_tiger")
OUT = os.path.join(WORK, "agents", "mechanics")
os.makedirs(os.path.join(OUT, "snaps"), exist_ok=True)
DLL = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
DISK = os.path.join(WORK, "bt_auto.st")
FILES = os.path.join(WORK, "files")


def ram_from_snap(path):
    s = open(path, "rb").read()
    ver = s[4]
    n = 19 if ver >= 5 else 18
    off = 5 + n * 4 + 2
    ln = struct.unpack_from("<i", s, off)[0]
    return s[off + 4: off + 4 + ln]


def regs_from_snap(path):
    s = open(path, "rb").read()
    ver = s[4]
    n = 19 if ver >= 5 else 18
    vals = struct.unpack_from(f"<{n}i", s, 5)
    names = ["d%d" % i for i in range(8)] + ["a%d" % i for i in range(8)] + ["usp", "ssp", "pc"][: n - 16]
    return {k: v & 0xFFFFFFFF for k, v in zip(names, vals)}


def repl(snap, lines, maxout=None):
    """Run REPL script lines on a snapshot; return combined stdout+stderr text."""
    env = dict(os.environ, ATARI_NOTRACE="1")
    script = "\n".join(lines) + "\nq\n"
    p = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl", "--disk-a", DISK],
                       input=script, capture_output=True, text=True, cwd=ROOT, env=env)
    return p.stdout + p.stderr


def rw(ram, a): return (ram[a] << 8) | ram[a + 1]
def rl(ram, a): return struct.unpack_from(">I", ram, a)[0]
