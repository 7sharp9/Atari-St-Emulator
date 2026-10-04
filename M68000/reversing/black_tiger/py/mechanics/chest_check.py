"""Chest contents (item kind $0a, handler $d38c): with one key the effect kind is 6 + rnd(3) ($d39e..$d3a6), $10b28 spawns it in the
effect table $31612 (14-byte records); at animation frame 3/3/4 kinds 6/7/8 allocate an item ($d490) of kind $b / $c / $d at the chest
(+16 y) (code at $10cc0 / $10d02 / $10d26); kind 6 also bursts four fire-column projectiles ($d40a -> $10e0c kind 3).
Live gate: poke a chest at the hero + one key + a seed, run 1.2M steps; the hero stands on the chest so the content is picked up at once
(kind 7: item $c -> vitality +1, kind 8: item $d -> zenny +50, kind 6: nothing but fire columns); every chest ends as item $b.
Usage: chest_check.py [N=30]"""
import os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
HX, HY = b.rw(ram, 0x1f014), b.rw(ram, 0x1f016)
SLOT = 0x1ff48
def lcg(s): return (((s * s) & 0xffff) * 0xc2 + s * 0x6eb + 0x3619) & 0xffff
random.seed(4)
ok = 0
for seed in [random.randrange(65536) for _ in range(N)]:
    kind = 6 + lcg(seed) % 3
    exp_item = {6: 0xb, 7: 0xc, 8: 0xd}[kind]
    lines = ["w 1f004 0001%s" % ram[0x1f006:0x1f008].hex(), "w 3195c %04x%s" % (seed, ram[0x3195e:0x31960].hex()),
             "w %x 000a%04x" % (SLOT, HX), "w %x %04x0000" % (SLOT + 4, HY), "s 1200000", "m 1f002 2", "m 1f006 2", "m 1f00e 2", "m 1f004 2", "m 1fb60 1640"]
    out = b.repl(snap, lines).splitlines()
    hexl = [l for l in out if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
    money, arm, vit, keys = (int(hexl[i].replace(" ", ""), 16) for i in range(4))
    items = bytes.fromhex("".join(hexl[4:]).replace(" ", ""))
    kinds = sorted({(items[i] << 8) | items[i + 1] for i in range(0, len(items), 10) if items[i:i + 6] != ram[0x1fb60 + i:0x1fb60 + i + 6] and (items[i] << 8 | items[i + 1])})
    d_vit = vit - 3; d_money = money - 200
    good = keys == 0 and kinds == [0xb] and ((kind == 7 and d_vit == 1 and d_money == 0) or (kind == 8 and d_money == 50 and d_vit == 0) or (kind == 6 and d_money == 0 and d_vit <= 0))
    ok += good
    print("seed %04x: effect kind %d -> items %s, zenny %+d, vitality %+d, armour %d, keys %d  %s" % (seed, kind, [hex(k) for k in kinds], d_money, d_vit, arm, keys, "OK" if good else "DIFF"))
print("chest contents model: %d/%d" % (ok, N))
