"""Gate: level-clear bonus $01025c(level): money += word[$17aa2 + 2*level].  callcap with the C stack argument
poked at $1ee50 (entry SP; labelled poke).  Prints match count over levels 0..7."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
low = ram[0x1ee52:0x1ee54].hex()
lines = []
for lv in range(8):
    lines += ["w 1ee50 %04x%s" % (lv, low), "callcap 1025c 3000000"]
out = b.repl(snap, lines)
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
ok = 0
for lv, blk in zip(range(8), blocks):
    money0 = b.rw(ram, 0x1f002)
    m = re.search(r"^mem \$01f003 \$([0-9a-f]+)->\$([0-9a-f]+)", blk, re.M)
    m2 = re.search(r"^mem \$01f002 \$([0-9a-f]+)->\$([0-9a-f]+)", blk, re.M)
    new = ((int(m2.group(2), 16) if m2 else ram[0x1f002]) << 8) | (int(m.group(2), 16) if m else ram[0x1f003])
    exp = b.rw(ram, 0x17aa2 + 2 * lv)
    good = (new - money0) == exp
    ok += good
    print("level %d: money %d -> %d (delta %d) table[%d]=%d  %s" % (lv + 1, money0, new, new - money0, lv, exp, "MATCH" if good else "differs"))
print("matches %d/8  (returned: %s)" % (ok, "returned" in blocks[0]))
