"""Parse level scripts $6c000 (list A) and $6d000 (list B) of the cbuster program image; print per-level entries and per-type counts.
usage: scripts.py [list A|B] [--census]"""
import os, struct, sys, collections
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
ROM = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def w(a): return struct.unpack(">H", ROM[a:a+2])[0]
def l(a): return struct.unpack(">I", ROM[a:a+4])[0]
def parse(base):
    out = []
    for lv in range(6):
        p = l(base + 4*lv); es = []
        while w(p) != 0xffff:
            trig = w(p); ty = ROM[p+2]; var = ROM[p+3]; x = w(p+4); y = w(p+6)
            es.append(dict(trig=trig, type=ty, var=var, x=x, y=y, addr=p)); p += 8
        out.append(es)
    return out
A = parse(0x6c000); B = parse(0x6d000)
if __name__ == "__main__":
    for name, T in (("A", A), ("B", B)):
        for lv in range(3):
            print("list", name, "level", lv, "entries", len(T[lv]))
            for e in T[lv]:
                print("  %05x trig=%04x type=%2d var=%02x x=%04x y=%04x" % (e["addr"], e["trig"], e["type"], e["var"], e["x"], e["y"]))
