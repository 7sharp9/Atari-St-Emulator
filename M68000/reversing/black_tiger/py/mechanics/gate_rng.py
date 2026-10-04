"""Gate: the game's RNG $00cb6a -> $00fe1c(n): seed($3195c) := (lo16(seed*seed)*$c2 + seed*$6eb + $3619) mod 2^16 ; result := seed mod n.
Model vs callcap over 300 random (seed, n) pairs.  The C argument is the word at the entry stack top ($1ee50 for $fe1c)."""
import os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
low = ram[0x1ee52:0x1ee54].hex()
random.seed(3)
def model(seed, n):
    s = (((seed * seed) & 0xffff) * 0xc2 + seed * 0x6eb + 0x3619) & 0xffff
    return s, s % n
cases = [(random.randrange(65536), random.choice((2, 3, 4, 5, 8, 10, 16, 20, 36, 44, 100, 1000, random.randrange(1, 65535)))) for _ in range(300)]
lines = []
for seed, n in cases:
    lines += ["w 3195c %04x%s" % (seed, ram[0x3195e:0x31960].hex()), "w 1ee50 %04x%s" % (n, low), "callcap fe1c 100000"]
out = b.repl(snap, lines)
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
ok = 0
for (seed, n), blk in zip(cases, blocks):
    ns, res = model(seed, n)
    d0 = int(re.search(r"D0 \$[0-9a-f]+->\$([0-9a-f]+)", blk).group(1), 16) if re.search(r"D0 \$[0-9a-f]+->\$([0-9a-f]+)", blk) else None
    m = re.findall(r"^mem \$03195([cd]) \$[0-9a-f]+->\$([0-9a-f]+)", blk, re.M)
    mem = bytearray(ram); mem[0x3195c:0x3195e] = seed.to_bytes(2, "big")
    for a, v in m: mem[0x3195c + (1 if a == "d" else 0)] = int(v, 16)
    got_seed = (mem[0x3195c] << 8) | mem[0x3195d]
    ok += (got_seed == ns and d0 is not None and (d0 & 0xffff) == res)
print("RNG model vs callcap: %d/%d" % (ok, len(cases)))
