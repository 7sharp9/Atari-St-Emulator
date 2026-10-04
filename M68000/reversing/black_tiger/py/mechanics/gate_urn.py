"""Gate: breaking an urn (item type 1) with a melee hit inside $00d4ae -> contents drawn as
  seed := lcg(seed) ; idx := seed mod (4*level+16) ; v := byte[$17784+idx]
  v < $80  -> the slot becomes item type v (0 = empty) ; v >= $80 -> slot cleared and actor(s) of type v&$7f spawn ($f spawns 3).
Labelled pokes: urn record in slot 100 ($1ff48) at hero x+16 / hero y, reach $1781e=4, $1eeb4 = y-2, facing 0, seed at $3195c.
Run for 120 random seeds on level 1 plus 40 with level index forced to 7 ($17846)."""
import os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
HX, HY = b.rw(ram, 0x1f014), b.rw(ram, 0x1f016)
SLOT = 0x1ff48
tbl = ram[0x17784:0x17784 + 0x31]
random.seed(9)
def lcg(s): return (((s * s) & 0xffff) * 0xc2 + s * 0x6eb + 0x3619) & 0xffff
cases = [(random.randrange(65536), 0) for _ in range(120)] + [(random.randrange(65536), 7) for _ in range(40)]
lines = ["w 1781e 00040000", "w 1f010 ff000000"]
for seed, lv in cases:
    lines += ["w 17846 %04x%s" % (lv, ram[0x17848:0x1784a].hex()), "w 3195c %04x%s" % (seed, ram[0x3195e:0x31960].hex()),
              "w %x 0001%04x" % (SLOT, HX + 16), "w %x %04x0000" % (SLOT + 4, HY), "w 1eeb4 %04x%s" % (HY - 2, ram[0x1eeb6:0x1eeb8].hex()),
              "callcap d4ae 3000000"]
out = b.repl(snap, lines)
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
assert len(blocks) == len(cases)
ok = 0; kinds = {}
for (seed, lv), blk in zip(cases, blocks):
    s1 = lcg(seed); idx = s1 % (4 * lv + 16); v = tbl[idx]
    mem = bytearray(ram)
    mem[SLOT:SLOT + 2] = b"\x00\x01"
    for a, nv in re.findall(r"^mem \$([0-9a-f]+) \$[0-9a-f]+->\$([0-9a-f]+)", blk, re.M):
        mem[int(a, 16)] = int(nv, 16)
    item = (mem[SLOT] << 8) | mem[SLOT + 1]
    new_actors = sorted(mem[a] for a in range(0x1f030, 0x1fb50, 16) if mem[a] != ram[a])
    exp_item = v if v < 0x80 else 0
    exp_act = [] if v < 0x80 else sorted([v & 0x7f] * (3 if (v & 0x7f) == 0xf else 1))
    good = item == exp_item and new_actors == exp_act
    ok += good
    kinds[v] = kinds.get(v, 0) + 1
    if not good: print("MISMATCH seed %04x lv %d idx %d v %02x: item %04x actors %s (expected %04x %s)" % (seed, lv, idx, v, item, new_actors, exp_item, exp_act))
print("urn contents model vs callcap: %d/%d; outcomes seen %s" % (ok, len(cases), {("%02x" % k): n for k, n in sorted(kinds.items())}))
