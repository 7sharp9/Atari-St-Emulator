"""Attack boxes of pool C hit objects: $69000[ctype] -> [state] -> [dir] -> [frame] -> 4 words (x0 x1 y0 y1, signed, relative to the object's x,y).
usage: cboxes.py <ctype> [state]   prints for dir 0 and 1 the frames with a non-zero box (frame count = pointers that stay in ROM data)"""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
R = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def L(a): return struct.unpack(">I", R[a:a+4])[0]
def S(a): return struct.unpack(">h", R[a:a+2])[0]
def ok(p): return 0x60000 <= p < 0x80000 and p % 2 == 0
def frames(ct, st, d):
    p = L(0x69000 + 4*ct); q = L(p + 4*st); r = L(q + 4*d)
    out = []
    for f in range(64):
        a = L(r + 4*f)
        if not ok(a): break
        out.append((S(a), S(a+2), S(a+4), S(a+6)))
    return out
if __name__ == "__main__":
    ct = int(sys.argv[1]); sts = [int(sys.argv[2])] if len(sys.argv) > 2 else range(0, 6)
    for st in sts:
        for d in (0, 1):
            try: fr = frames(ct, st, d)
            except Exception as e: continue
            if not fr: continue
            print("ctype %d state %d dir %d: %d frames; active:" % (ct, st, d, len(fr)), " ".join("%d:%s" % (i, b) for i, b in enumerate(fr) if any(b)))
