"""panel_rank_check.py: live check that the aggression word is read only for display: for rank values 0..7 poke side-2 group-1's word 148+2, set the flag word $9218 := 0
(non-first group), `callcap $90de` with A3 = the group's record-view pointer and read the string A5 returns from the call's regdelta; expect the `$9530` table entry
(`$9530 + 8 + byte[$9530 + rank]`).  Prints rank -> string.  Run from M68000/."""
import json, os, re, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap
SNAP = "scratchpad/pm142/rand1.snap"
G = 0x51538
A3 = G + 2 * 0x13c + 2          # side 2, group 1 (record view: word k at base + 2k)
r = ram_from_snap(ROOT / SNAP)
ok = 0
for rank in range(8):
    WORKD = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "aggr"
    WORKD.mkdir(parents=True, exist_ok=True)
    out = str(WORKD / ("c90de_%d.json" % rank))
    base = G + 2 * 0x13c + 148   # side 2 words 0 and 1 of the aggression array; keep word 0, set word 1 (the checked group) to the rank
    cmds = ["w %x %08x" % (base, (r[base] << 24) | (r[base + 1] << 16) | rank),
            "w 9216 00000000", "callcap 90de 200 %s A3=%x" % (out, A3), "q"]
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", SNAP, "repl", "--disk-a", "scratchpad/powermonger.st"],
                       input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
    m = re.search(r"regdelta.*A5 \$[0-9a-f]+->\$([0-9a-f]+)", p.stdout + p.stderr)
    a5 = int(m.group(1), 16) if m else None
    s = ""
    if a5:
        s = bytes(r[a5:a5 + 14]).split(b"\0")[0].decode("latin1")
    want = 0x9530 + 8 + r[0x9530 + rank]
    ws = bytes(r[want:want + 14]).split(b"\0")[0].decode("latin1")
    print("rank %d: A5=%s string %r expected $%x %r %s" % (rank, "%x" % a5 if a5 else None, s, want, ws, "OK" if a5 == want else "MISMATCH"))
    ok += a5 == want
print("%d/8 match" % ok)
sys.exit(0 if ok == 8 else 1)
