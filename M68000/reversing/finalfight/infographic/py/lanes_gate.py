"""lanes_gate.py: the per-player candidate-list rectangle in the saved work-RAM dumps against the rule read from $8d70.

$8d70 (called from $8c6e once per player) clears words 6, 8, 10, 12 of the list descriptor at 21250(A5) (player 1 victims),
21354(A5) (player 2 victims) and then, only if the player record is in use, its state byte +2 is 2 and +22 is 0, writes
   lane low -12, lane high +9, x offset $80, x width $100          (+139 = 0)
   or -24, +24, $80, $100                                          (+139 != 0; $8d1e sets +139 when the sub-state +3 is $10, the special)
Usage: python lanes_gate.py   (M68000/.venv/bin/python)"""
import glob, os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
def main():
    on = on_ok = off = off_ok = 0
    wide = 0
    bad = []
    files = sorted(glob.glob(os.path.join(ROOT, "scratchpad/finalfight/gfx/dump/*_ram.bin")))
    for f in files:
        ram = open(f, "rb").read()
        for pl, lst in ((0x8568, 21250), (0x8628, 21354)):
            a = 0x8000 + lst
            w = struct.unpack(">4h", ram[a + 6:a + 14])
            r = ram[pl:pl + 0xc0]
            if r[0] == 0: continue
            active = r[2] == 2 and r[22] == 0
            want = ((-24, 24) if r[139] else (-12, 9)) + (0x80, 0x100) if active else (0, 0, 0, 0)
            ok = tuple(w) == want
            if active: on += 1; on_ok += ok; wide += bool(r[139])
            else: off += 1; off_ok += ok
            if not ok: bad.append((os.path.basename(f), pl, w, want))
    print("player records in %d dumps: active (state 2, +22 = 0) %d, window equals the rule in %d (of them %d with +139 set)" % (len(files), on, on_ok, wide))
    print("inactive %d, list rectangle all zero in %d" % (off, off_ok))
    for b in bad[:8]: print("  miss", b)
if __name__ == "__main__":
    main()
