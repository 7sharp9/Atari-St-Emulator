"""Gate for the whole file path `$df52(index)` -> `$def0` -> `$d4d2` -> `$d574` (FAT12 reader, `$d9fc` FDC DMA) -> `$e2b8`.

    cd M68000 && uv run python reversing/powermonger/py/disk/gate_load.py

callcap `$df52` from m1_win with the game disk mounted and the index poked at the entry stack argument
(entrySP, found from a first callcap). Expected result: the resource's file from the disk image (own FAT12
walk below, not the game's), run through decrunch_model.decrunch, equals RAM at the table's destination, the
table's +8 length field becomes the file length, and the cache slot `$e040+4*i` is filled.
"""
import json, os, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decrunch_model as M
ROOT, WORK = M.ROOT, M.WORK
SNAP = "scratchpad/pm123/win/m1_win.snap"
ram = open(os.path.join(ROOT, "scratchpad/pm123/win/m1_win.ram"), "rb").read()
L = lambda a: struct.unpack(">I", ram[a:a+4])[0]
names = {}
idxs = [0, 2, 3, 4, 5, 9]
cmds = ["disk scratchpad/powermonger.st", "callcap df52 1000 scratchpad/pm147/disk/out/probe.json"]
os.makedirs(os.path.join(WORK, "out"), exist_ok=True)
def runrepl(cmds, tag):
    p = os.path.join(WORK, "out/%s.cmds" % tag)
    open(p, "w").write("\n".join(cmds) + "\nq\n")
    return subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", SNAP, "repl"], stdin=open(p),
                          capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
runrepl(cmds, "probe")
sp = json.load(open(os.path.join(WORK, "out/probe.json")))["entrySP"]
cmds = ["disk scratchpad/powermonger.st"]
for i in idxs:
    cmds += ["w %x %04x0000" % (sp, i), "callcap df52 60000000 scratchpad/pm147/disk/out/load_%d.json" % i]
r = runrepl(cmds, "load")
ok = 0
for i in idxs:
    j = json.load(open(os.path.join(WORK, "out/load_%d.json" % i)))
    nm = ram[L(0xe0c4 + 12 * i):L(0xe0c4 + 12 * i) + 24].split(b"\0")[0].decode()
    dest = L(0xe0c4 + 12 * i + 4)
    raw = open(os.path.join(M.disk_files(), nm.replace("\\", "/")), "rb").read()
    size = L(0xe084 + 4 * i)
    buf = bytearray(max(size, len(raw)) + 8); buf[:len(raw)] = raw
    M.decrunch(buf, len(raw))
    img = bytearray(ram)
    for a, b, c in j["mem"]:
        img[a] = c
    flen = struct.unpack(">I", img[0xe0c4 + 12 * i + 8:0xe0c4 + 12 * i + 12])[0]
    cache = struct.unpack(">I", img[0xe040 + 4 * i:0xe040 + 4 * i + 4])[0]
    good = bytes(img[dest:dest + size]) == bytes(buf[:size]) and flen == len(raw) and cache != 0 and j["outcome"] == "returned"
    ok += good
    print("idx %2d %-18s dest $%x packed %6d -> %6d  steps %9d  len field %d  cache $%x  %s" % (
        i, nm, dest, len(raw), size, j["steps"], flen, cache, "match" if good else "MISMATCH"))
print("%d/%d" % (ok, len(idxs)))
