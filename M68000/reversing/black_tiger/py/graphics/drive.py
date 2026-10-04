"""drive.py - run REPL scripts against the existing emulator DLL (no build) for the graphics agent.

  run_repl(snap, lines, log=None) -> stdout text
  start_level(level, out_snap, steps=...) : resume play_start.snap, jump the main loop back to the
      level-start entry $c50e with $17846 = level (a labelled poke, see notes.md sec 9), run until the
      level is playing and save a snapshot at a frame boundary (entry of the page-flip trap fn1, $aad8).
"""
import os
import subprocess
import sys

from bt_common import ROOT, WORK, OUT, snap_path

DLL = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
DISK = os.path.join(WORK, "bt_auto.st")
SNAPDIR = os.path.join(OUT, "snaps")
os.makedirs(SNAPDIR, exist_ok=True)


def run_repl(snap, lines, log=None):
    env = dict(os.environ, ATARI_NOTRACE="1")
    script = "\n".join(lines) + "\nq\n"
    p = subprocess.run(["dotnet", "exec", DLL, "resume", snap_path(snap), "repl", "--disk-a", DISK],
                       input=script, text=True, capture_output=True, env=env, cwd=ROOT)
    out = p.stdout + p.stderr
    if log:
        open(log, "w").write(out)
    return out


def jump_to_level_start(level):
    """REPL lines: run to the main-loop top $c574, patch a one-shot jmp $c50e, step it, restore."""
    return [
        "bp c574 2000000",
        "w 17846 %04x0000" % level,
        "w c574 4ef90000",
        "w c578 c50e0001",
        "s 1",
        "w c574 6100038a",
        "w c578 4a390001",
    ]


def start_level(level, out_name, run_steps=3000000, frames_after=3):
    lines = jump_to_level_start(level) + ["s %d" % run_steps]
    out = run_repl("play_start.snap", lines + ["r"])
    return out


if __name__ == "__main__":
    print(start_level(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "x"))
