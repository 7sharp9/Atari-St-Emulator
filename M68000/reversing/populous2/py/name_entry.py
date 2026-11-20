"""Populous II: reach a conquest battle the game's own way, by typing its world name on the briefing.

Route (read from $15480's dispatch $1561a and $16430, README "Conquest battles"): a left click on the name field
(briefing text row 0, columns 12..22, so pixels x 104..183, y 0..7) makes $165b8 return region 1, which clears the
buffer $1572e and runs the line editor $16430. The editor polls $22036: the make code the IKBD handler $1c42 leaves
in $392ec, cleared on read, mapped through the scancode table $2208a (UK layout, +$80 while $3932a or $3931e is set). Return
($1c) ends the edit; $15632 then compares the buffer with each battle's name (`$2222c`, 0..999), sets $473a0 and
reruns $22e8c and the briefing.

The scancodes are read from the game's own table at $2208a, so any name in its alphabet can be typed.

usage (from anywhere):
  uv run python reversing/populous2/py/name_entry.py NAME <out dir> [--to-start]
    writes <out>/name_<NAME>.snap (the briefing after Return) and prints the buffer and $473a0;
    --to-start drives PROCEED and the Zeus question's OK with drive.txt's clicks and steps to
    <out>/name_<NAME>_start.snap, the battle's first play frame (battle_census.sh's b<N>_start equivalent).
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(__file__)
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

DLL = os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll")
BRIEF = os.path.join(ROOT, "scratchpad/populous2/anchors/p2_briefing.snap")
IMAGE = os.path.join(ROOT, "scratchpad/populous2/pop2_1770.bin")
TABLE = 0x2208A - 0x1770
HOLD = 150000  # steps per key level: far longer than the editor's poll loop


def scancodes(name):
    t = open(IMAGE, "rb").read()[TABLE:TABLE + 128]
    out = []
    for ch in name.upper():
        if ch.encode("latin1") not in t:
            sys.exit(f"'{ch}' is not in the unshifted half of the table at $2208a")
        out.append(t.index(ch.encode("latin1")))
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name, out = sys.argv[1].upper(), os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    snap = os.path.join(out, f"name_{name}.snap")
    # p2_briefing leaves the pointer at (140,98); the field is at x 104..183, y 0..7
    lines = ["mouse move -20 -94", "s 300000", "mouse down l", "s 60000", "mouse up l", "s 300000"]
    for k in scancodes(name) + [0x1C]:
        lines += [f"kbd {k:02x}", f"s {HOLD}", f"kbd {k | 0x80:02x}", f"s {HOLD}"]
    lines += ["s 3000000", f"snap {snap}"]
    if "--to-start" in sys.argv:
        start = os.path.join(out, f"name_{name}_start.snap")
        # pointer now at (120,4): PROCEED (50,192), then the Zeus question's OK (150,180), as in drive.txt
        lines += ["mouse move -70 188", "s 300000", "mouse down l", "s 60000", "mouse up l", "s 30000000",
                  "mouse move 100 -12", "s 300000", "mouse down l", "s 60000", "mouse up l", "s 40000000",
                  f"snap {start}"]
    lines.append("q")
    r = subprocess.run(["dotnet", "exec", DLL, "resume", BRIEF, "repl"], input="\n".join(lines) + "\n",
                       capture_output=True, text=True, cwd=ROOT, env={**os.environ, "ATARI_NOTRACE": "1"})
    if not os.path.exists(snap):
        sys.exit(f"no snapshot written\n{r.stdout[-1500:]}{r.stderr[-500:]}")
    m, _ = load_ram(snap)
    buf = bytes(m[0x1572E:0x1572E + 16]).split(b"\0")[0].decode("latin1")
    print(f"{name}: buffer $1572e '{buf}', battle $473a0 = {(m[0x473A0] << 8) | m[0x473A1]}")


if __name__ == "__main__":
    main()
