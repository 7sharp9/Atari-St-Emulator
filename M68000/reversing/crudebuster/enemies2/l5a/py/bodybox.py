"""Body (contact) hit boxes: `$f6c4` reads the box of a pool A record from table $6b000 [type] -> [state +3] -> 4 words (x1, x2, y1, y2 relative to the record x/y;
in `$f700` D0/D1 = x edges (facing right uses D0), D2/D3 = y edges). `$f690` tests it against the player hurt box (+64..+70) and `$f700` takes health
byte `$f78e[type]` (1; 0 for types $3d and $4d) from the player (+19), reaction code `$f7de[type]` to +23, hit spark pool B type $2b.
usage: bodybox.py <type hex> ...   prints per state the box words (signed) or '-' when the pointer is not a plausible box"""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
def s16(a):
    v = int.from_bytes(rom[a:a+2], "big"); return v - 65536 if v >= 32768 else v
for t in [int(x, 16) for x in sys.argv[1:]]:
    p = l(0x6b000 + 4 * t)
    print(f"type {t:02x}: state table ${p:06x}  contact damage byte {rom[0xf78e+t]}  react {rom[0xf7de+t]:02x}")
    seen = {}
    for st in range(0x18):
        b = l(p + 4 * st)
        seen.setdefault(b, []).append(st)
    for b, sts in seen.items():
        if 0x60000 <= b < 0x80000:
            print("   states", ",".join("%x" % s for s in sts), f"box ${b:06x}:", [s16(b + 2 * i) for i in range(4)])
        else:
            print("   states", ",".join("%x" % s for s in sts), f"ptr ${b:08x} (not a box)")
