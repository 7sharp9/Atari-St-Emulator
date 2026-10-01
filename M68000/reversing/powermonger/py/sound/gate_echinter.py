"""Gate: `EchInter` ($1b77e), the per-VBL sequencer, against a Python model, by `callcap` from a start snapshot.

State: $2c992 active, $2c993 sample-busy, $2c994 loop, $2c996 pair index, $2cba2 sequence pointer, $2c998 sample id,
$2c99a Timer-A data (rate), $1af3a stream pointer (immediate operand of the Timer A ISR).
Model:  if active and not busy:
            (s, r) = seq[2*idx], seq[2*idx+1]
            if s == $ff: if loop: idx = 0; (s, r) = seq[0], seq[1]  else: active = 0; return
            idx += 1; $2c998 = s; $2c99a = r; $1af3a = start of sample s (record $2cba6 + 12*s); busy = $ff   (PlayEch $1ae5c)

    cd M68000 && .venv/bin/python reversing/powermonger/py/sound/gate_echinter.py [snap]
Expected (m1_s0): matched N/N
"""
import itertools
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/sound"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
snap = sys.argv[1] if len(sys.argv) > 1 else "scratchpad/pm123/win/m1_s0.snap"
ram = ram_from_snap(ROOT / snap)
u16 = lambda a: struct.unpack_from(">H", ram, a)[0]
u32 = lambda a: struct.unpack_from(">I", ram, a)[0]
nseq = u16(0x2C99C)
seqptr = [u32(0x2C9A0 + 4 * i) for i in range(nseq)]
seqlen = []
for p in seqptr:
    n = 0
    while ram[p + 2 * n] != 0xFF:
        n += 1
    seqlen.append(n)


def model(st):
    st = dict(st)
    if not st["active"] or st["busy"]:
        return st
    p = st["ptr"]
    s, r = ram[p + 2 * st["idx"]], ram[p + 2 * st["idx"] + 1]
    if s == 0xFF:
        if not st["loop"]:
            st["active"] = 0
            return st
        st["idx"] = 0
        s, r = ram[p], ram[p + 1]
    st["idx"] += 1
    st["sid"], st["rate"] = s, r
    st["stream"] = u32(0x2CBA6 + 12 * s)
    st["busy"] = 0xFF
    return st


cases = []
for i in range(nseq):
    n = seqlen[i]
    for idx, loop in itertools.product(sorted({0, n - 1, n}), (0, 1)):
        cases.append(dict(active=1, busy=0, loop=loop, idx=idx, ptr=seqptr[i], sid=0, rate=0, stream=0x5C6DA, seq=i))
for i in range(0, nseq, 7):
    cases.append(dict(active=0, busy=0, loop=0, idx=0, ptr=seqptr[i], sid=0, rate=0, stream=0x5C6DA, seq=i))
    cases.append(dict(active=1, busy=1, loop=0, idx=1, ptr=seqptr[i], sid=0, rate=0, stream=0x5C6DA, seq=i))
cmds = []
for c in cases:
    cmds.append(f"w 2c992 {c['active']:02x}{c['busy']:02x}{c['loop']:02x}00")
    cmds.append(f"w 2c996 {c['idx']:04x}0000")
    cmds.append(f"w 2c99a {c['rate']:04x}0000")
    cmds.append(f"w 2cba2 {c['ptr']:08x}")
    cmds.append(f"w 1af3a {c['stream']:08x}")
    cmds.append("callcap 1b77e 3000")
(DATA / "gate_echinter.cmds").write_text("\n".join(cmds) + "\n")
res = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"],
                     input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
blocks = res.stdout.split("--- callcap $01b77e:")[1:]
good = 0
bad = []
for c, blk in zip(cases, blocks):
    mem = {}
    for m in re.finditer(r"mem \$([0-9a-f]{6}) \$[0-9a-f]{2}->\$([0-9a-f]{2})", blk):
        mem[int(m.group(1), 16)] = int(m.group(2), 16)
    img = bytearray(ram)

    def put(a, n, v):
        img[a:a + n] = v.to_bytes(n, "big")
    put(0x2C992, 1, c["active"]); put(0x2C993, 1, c["busy"]); put(0x2C994, 1, c["loop"]); put(0x2C996, 2, c["idx"])
    put(0x2C998, 2, 0); put(0x2C99A, 2, c["rate"]); put(0x2CBA2, 4, c["ptr"]); put(0x1AF3A, 4, c["stream"])
    for a, v in mem.items():
        img[a] = v
    got = dict(active=img[0x2C992], busy=img[0x2C993], loop=img[0x2C994], idx=struct.unpack_from(">H", img, 0x2C996)[0],
               ptr=struct.unpack_from(">I", img, 0x2CBA2)[0], sid=struct.unpack_from(">H", img, 0x2C998)[0],
               rate=struct.unpack_from(">H", img, 0x2C99A)[0], stream=struct.unpack_from(">I", img, 0x1AF3A)[0])
    want = model({k: v for k, v in c.items() if k != "seq"})
    want.pop("seq", None)
    if got == want:
        good += 1
    else:
        bad.append((c, got, want))
print(f"matched {good}/{len(cases)} (callcap blocks parsed: {len(blocks)})")
for b in bad[:3]:
    print("MISMATCH", b)
