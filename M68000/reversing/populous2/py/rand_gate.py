"""Populous II rand $215dc against its model, under callcap, from one snapshot.

Model (read from $215dc/$21608): seed = long $47382, 0 replaced by $bc614e;
seed' = seed * $bb40e62d mod 2^32 (the 32x32 low-half multiply $21608); store seed';
D0 = (seed' >> 8) & $7fff. Each case pokes a seed with `w 47382 <seed>` and callcaps.
The control drops the zero-seed substitution.

usage: uv run python reversing/populous2/py/rand_gate.py <snap> [n]
"""
import os, random, re, subprocess, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, "tools", "rdis.py")):
    d = os.path.dirname(d)
ROOT = os.environ.get("M68000_ROOT", d)


def model(seed, zero_rule=True):
    if seed == 0 and zero_rule:
        seed = 0xBC614E
    s = (seed * 0xBB40E62D) & 0xFFFFFFFF
    return s, (s >> 8) & 0x7FFF


snap = os.path.abspath(sys.argv[1])
n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
random.seed(3)
seeds = [0, 1, 0xFFFFFFFF] + [random.getrandbits(32) for _ in range(n - 3)]
script = "".join(f"w 47382 {s:08x}\ncallcap 215dc 2000\n" for s in seeds)
out = subprocess.run(["dotnet", "exec", os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll"),
                      "resume", snap, "repl"], input=script, capture_output=True, text=True,
                     cwd=ROOT).stdout
blocks = out.split("--- callcap")[1:]
assert len(blocks) == len(seeds), out[-1500:]
ok = ctl = 0
for s, blk in zip(seeds, blocks):
    d0 = int(re.search(r"D0 \$[0-9a-f]+->\$([0-9a-f]+)", blk).group(1), 16)
    mem = {int(a, 16): int(v, 16) for a, v in re.findall(r"mem \$([0-9a-f]+) \$[0-9a-f]+->\$([0-9a-f]+)", blk)}
    new = s
    for i in range(4):
        if 0x47382 + i in mem:
            sh = 24 - 8 * i
            new = (new & ~(0xFF << sh)) | (mem[0x47382 + i] << sh)
    ok += model(s) == (new, d0)
    ctl += model(s, zero_rule=False) == (new, d0)
print(f"rand $215dc: {ok}/{len(seeds)} (seed and D0); control without the zero-seed rule {ctl}/{len(seeds)}")
