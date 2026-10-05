"""Attack boxes of pool C types from the table $69000 [ctype][state][facing][frame] -> 4 signed words (x1, x2, y1, y2) relative to the owner x/y
(fbdc: x1 = x+w0, x2 = x+w1, y1 = y+w2, y2 = y+w3; the box is tested against the player's hurt box +64..+70).
usage: boxes.py <ctype hex> [...]   (state 0 only unless the handler copies the owner state: types 0x1d)"""
import os, sys, struct
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
def sw(a): return struct.unpack(">h", rom[a:a+2])[0]
def ok(a): return 0x69000 <= a < 0x80000
def boxes(ct, states=(0,)):
    out = {}
    t = l(0x69000 + 4 * ct)
    for s in states:
        ps = l(t + 4 * s)
        for face in (0, 1):
            pf = l(ps + 4 * face)
            frames = []
            for fr in range(64):
                pb = l(pf + 4 * fr)
                if not ok(pb): break
                frames.append(tuple(sw(pb + 2 * k) for k in range(4)))
            out[(s, face)] = frames
    return out
if __name__ == "__main__":
    for a in sys.argv[1:]:
        ct = int(a, 16)
        for (s, f), fr in boxes(ct).items():
            print(f"ctype {ct:02x} state {s} facing {f}: {len(fr)} frames")
            for i, b in enumerate(fr): print(f"   frame {i}: x {b[0]:5d}..{b[1]:5d}  y {b[2]:5d}..{b[3]:5d}")
