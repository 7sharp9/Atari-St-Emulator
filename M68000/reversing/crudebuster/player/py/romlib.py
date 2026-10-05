"""Small helpers over the decrypted cbuster program image."""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
ROM = os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin")
_d = open(ROM, "rb").read()
def b(a): return _d[a]
def w(a): return struct.unpack(">H", _d[a:a+2])[0]
def sw(a): return struct.unpack(">h", _d[a:a+2])[0]
def l(a): return struct.unpack(">I", _d[a:a+4])[0]
def sb(a): return struct.unpack(">b", _d[a:a+1])[0]
if __name__ == "__main__":
    a = int(sys.argv[1], 16); n = int(sys.argv[2]); k = sys.argv[3] if len(sys.argv) > 3 else "l"
    for i in range(n):
        if k == "l": print("%06x: %08x" % (a+4*i, l(a+4*i)))
        elif k == "w": print("%06x: %04x" % (a+2*i, w(a+2*i)))
        else: print("%06x: %02x" % (a+i, b(a+i)))

def ptr_array(a):
    """Read a contiguous longword pointer array at a; its length is inferred as (smallest target seen - a)/4 (arrays are laid out right before their targets)."""
    out = []; mn = 1 << 32; i = 0
    while a + 4 * i < mn and i < 64:
        t = l(a + 4 * i)
        if t >= len(_d) or t < 0x1000: break
        out.append(t); mn = min(mn, t); i += 1
    return out
