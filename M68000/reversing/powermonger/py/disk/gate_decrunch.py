"""Differential gate for `decrunch` ($e2b8): decrunch_model.py vs the real 68000 through `callcap`.

    cd M68000 && uv run python reversing/powermonger/py/disk/gate_decrunch.py [synthetic|real|all]

Each input is poked (REPL `w`, big-endian longs) into free RAM ($c0000..$f0000 is zero in m1_win),
then `callcap e2b8 <steps> out.json A1=<base> D0=<packed length>` runs the real routine; the changed-memory
delta is applied to the poked image and compared byte for byte with the model's in-place result.
Also compared: the final registers D5 (checksum accumulator, must be 0) and A2 (must equal A1).
synthetic = 40 inputs from decrunch_model.corpus() (own encoder), real = packed files of the game disk.
"""
import json
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decrunch_model as M
ROOT, WORK = M.ROOT, M.WORK

SNAP = "scratchpad/pm123/win/m1_win.snap"
BASE = 0xc0000


def run(inputs, tag):
    """inputs: list of (name, packed bytes, unpacked size)"""
    cmds = []
    slots = []
    a = BASE
    for i, (name, pk, size) in enumerate(inputs):
        assert len(pk) % 4 == 0
        slots.append(a)
        for o in range(0, len(pk), 4):
            cmds.append("w %x %s" % (a + o, pk[o:o + 4].hex()))
        cmds.append("callcap e2b8 50000000 scratchpad/pm147/disk/out/%s_%d.json A1=%x D0=%x" % (tag, i, a, len(pk)))
        a += (max(size, len(pk)) + 0x20 + 0xff) & ~0xff
    assert a <= 0xf0000, hex(a)
    os.makedirs(os.path.join(WORK, "out"), exist_ok=True)
    script = os.path.join(WORK, "out/%s.cmds" % tag)
    open(script, "w").write("\n".join(cmds) + "\nq\n")
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", SNAP, "repl"],
                       stdin=open(script), capture_output=True, text=True, cwd=ROOT, env=env)
    ok = 0
    for i, (name, pk, size) in enumerate(inputs):
        base = slots[i]
        j = json.load(open(os.path.join(WORK, "out/%s_%d.json" % (tag, i))))
        n = max(size, len(pk)) + 0x20
        img = bytearray(n)
        img[:len(pk)] = pk
        exp = bytearray(img)
        M.decrunch(exp, len(pk))
        got = bytearray(img)
        stray = 0
        for addr, before, after in j["mem"]:
            if base <= addr < base + n:
                got[addr - base] = after
            elif not (j["entrySP"] - 64 <= addr <= j["entrySP"] + 16):
                stray += 1
        regN = dict(zip(["D%d" % k for k in range(8)] + ["A%d" % k for k in range(8)], j["regN"]))
        good = (got == exp and j["outcome"] == "returned" and regN["D5"] == 0 and regN["A2"] == base and stray == 0)
        ok += good
        print("%-14s packed %6d -> %6d  steps %8d  %s" % (name, len(pk), size, j["steps"], "match" if good else "MISMATCH"))
    print("%s: %d/%d match" % (tag, ok, len(inputs)))
    return ok, len(inputs)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    tot = [0, 0]
    if what in ("synthetic", "all"):
        ins = []
        for k, d in enumerate(M.corpus()[:40]):
            ins.append(("syn%02d" % k, M.pack(d), len(d)))
        r = run(ins, "syn")
        tot[0] += r[0]; tot[1] += r[1]
    if what in ("real", "all"):
        ins = []
        for f in ("TEXTURES", "SPRITE16", "SPRITE24", "SPRITE32", "SPRITE8", "CAPGRAPH", "WIN", "LOSE"):
            raw = open(os.path.join(M.disk_files(), "DATA", f + ".DAT"), "rb").read()
            ins.append((f, raw, struct.unpack(">I", raw[-4:])[0]))
        r = run(ins, "real")
        tot[0] += r[0]; tot[1] += r[1]
    print("TOTAL %d/%d" % tuple(tot))


if __name__ == "__main__":
    main()
