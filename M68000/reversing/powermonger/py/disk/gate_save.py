"""Save-game layer check (callcap needs the vsync patch below; WITHOUT it callcap ends in "Loop detected at PC=$1876").

LIMIT: `diskio` $d9fc calls the vsync wait `$1870` (`tst.w $2df8c / beq $1870`); callcap masks interrupts, so the
VBL handler never sets $2df8c and the loop never ends (poking $2df8c does not help: it is cleared first). The
harness patches the wait out, `w 1874 df8c4e71` (the `beq` at $1876 becomes a nop); that changes timing only.
With the patch `callcap 1bd52` (sector 0 read + 'POWE' compare) returns (D0 = 0, 120,954 steps), but `callcap 1bd70` / `1bdfe`
still do not return: they hit the step cap in the game main loop (PC $88b0 / $12ccc) after about 5-8 KB of the first
transfer changed, i.e. the multi-sector read fails past the first track and falls into the retry/requester loop
(`$1bef8` ERROR READING, then `bra $1bd74`). Cause not found (the natural FDC path loads the game disk fine, so it is
probably a seek/step wait that needs interrupts or timer time). This script therefore PROVES NOTHING about the
198-sector slot read or write; it is kept to document the limit and as the starting point for a natural-run drive.

Save-game layer check: callcap `$1bd70` (load slot) and `$1bdfe` (save slot) against a synthetic save disk.

    cd M68000 && uv run python reversing/powermonger/py/disk/gate_save.py

The disk (out/save.st) is built here from the sector-0 header the game itself carries at $1bb0e (512 bytes,
slot-used flags at +$ec), 819200 bytes, slot k = sectors 198k+1..198k+198 filled with a position-dependent pattern.
Load of slot C (poke $e296 = 'C'): RAM $3f768.. must equal the 198 sectors (101376 bytes = to $58368).
Save of slot B (unused flag): RAM $3f768.. must appear in sectors 199..396 of the image and the flag byte
+$ec+1 of sector 0 must become non-zero. Whether the image file is written is part of what is reported.
"""
import json, os, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decrunch_model as M
ROOT, WORK = M.ROOT, M.WORK
SNAP = "scratchpad/pm123/win/m1_win.snap"
ram = open(os.path.join(ROOT, "scratchpad/pm123/win/m1_win.ram"), "rb").read()
img = bytearray(819200)
img[0:512] = ram[0x1bb0e:0x1bb0e + 512]
for k in range(26):
    img[0xec + k] = 0
img[0xec + 0] = 1; img[0xec + 2] = 1          # slots A and C used
def pat(sec, i): return (sec * 13 + i * 7 + (i >> 8)) & 0xff
for s in range(1, 793):
    img[s * 512:(s + 1) * 512] = bytes(pat(s, i) for i in range(512))
out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
open(os.path.join(out, "save.st"), "wb").write(img)
def repl(cmds, tag):
    p = os.path.join(out, tag + ".cmds"); open(p, "w").write("\n".join(cmds) + "\nq\n")
    return subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", SNAP, "repl"], stdin=open(p),
                          capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
r = repl(["disk scratchpad/pm147/disk/out/save.st", "w 1874 df8c4e71", "w e296 432e4741",
          "callcap 1bd70 60000000 scratchpad/pm147/disk/out/sv_load.json"], "sv_load")
j = json.load(open(os.path.join(out, "sv_load.json")))
got = bytearray(ram[0x3f768:0x3f768 + 198 * 512])
for a, b, c in j["mem"]:
    if 0x3f768 <= a < 0x3f768 + 198 * 512: got[a - 0x3f768] = c
exp = b"".join(bytes(pat(397 + s, i) for i in range(512)) for s in range(198))   # slot C = sectors 397..594
print("load slot C:", j["outcome"], "steps", j["steps"], "match" if bytes(got) == exp else "MISMATCH",
      "bytes changed", len(j["mem"]))
# save slot B
r = repl(["disk scratchpad/pm147/disk/out/save.st", "w 1874 df8c4e71", "w e296 422e4741",
          "callcap 1bdfe 60000000 scratchpad/pm147/disk/out/sv_save.json"], "sv_save")
j = json.load(open(os.path.join(out, "sv_save.json")))
after = open(os.path.join(out, "save.st"), "rb").read()
want = ram[0x3f768:0x3f768 + 198 * 512]
print("save slot B:", j["outcome"], "steps", j["steps"], "regdelta D0..", j["regN"][:1])
print("image file changed on disk:", after != bytes(img), " slot B sectors == RAM:", after[199 * 512:397 * 512] == want,
      " flag B:", after[0xec + 1])
print(r.stdout[-300:] if r.returncode else "")
