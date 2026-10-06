"""boxes_gate.py: re-derive the hit and hurt boxes of every live fighter record in the saved gfx/work-RAM dumps and compare with the fields the game stored.

Rule under test (frame.md "Hit and hurt boxes", routine $32c4), with A0 = long at +56 of the record:
  attack = A0 + (byte45 & $7f) * 16 + word(A0), none if byte45 = 0 or (byte45 bit 7 and the record is airborne, +14 != +10)
  hurt   = A0 + byte44 * 8, none if byte44 = 0 or byte97 != 0
  entry  = dx, dy, half width, half height (signed words); centre x = x + dx (x - dx when byte46 != 0), centre y = y + dy
Compared with: +112 / +120 (descriptor pointers), +116 / +118 (attack centre), +124 / +126 (hurt centre).
Dumps: scratchpad/finalfight/gfx/dump/*_ram.bin (work RAM $ff0000..). Usage: python boxes_gate.py   (M68000/.venv/bin/python)"""
import glob, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
ROM = open(os.environ.get("FF_MAIN", os.path.join(ROOT, "scratchpad/finalfight/ff_main.bin")), "rb").read()
def sw(b, a): return struct.unpack(">h", b[a:a + 2])[0]
def uw(b, a): return struct.unpack(">H", b[a:a + 2])[0]
def ul(b, a): return struct.unpack(">I", b[a:a + 4])[0]

TAGS = (0, 2, 4)      # players and the two damage-taking fighter pools; tag 6 and 8 records are not served by $32c4
def live_records(ram):
    """The $c0-stride run $ff8568..$ffb1a7: players and the tags 2, 4, 6, 8 pools."""
    for i in range((0xb1a8 - 0x8568) // 0xc0):
        a = 0x8568 + i * 0xc0
        r = ram[a:a + 0xc0]
        if r[0]: yield 0xff0000 + a, r

def derive(r):
    a0 = ul(r, 56)
    if not (0 < a0 < len(ROM) - 0x400): return None
    x, y = uw(r, 6), uw(r, 10)
    mir = r[46] != 0
    out = {}
    i45 = r[45]
    if i45 == 0 or ((i45 & 0x80) and uw(r, 14) != uw(r, 10)):
        out["atk"] = None
    else:
        p = a0 + (i45 & 0x7f) * 16 + sw(ROM, a0)
        dx = sw(ROM, p)
        out["atk"] = (p, ((x - dx) if mir else (x + dx)) & 0xffff, (y + sw(ROM, p + 2)) & 0xffff)
    if r[97] or r[44] == 0:
        out["hurt"] = None
    else:
        p = a0 + r[44] * 8
        dx = sw(ROM, p)
        out["hurt"] = (p, ((x - dx) if mir else (x + dx)) & 0xffff, (y + sw(ROM, p + 2)) & 0xffff)
    return out

def main():
    n = dict(rec=0, atk=0, atk_ok=0, hurt=0, hurt_ok=0, atk_none_ok=0, atk_none=0, hurt_none=0, hurt_none_ok=0)
    bad = []
    skipped = 0
    files = sorted(glob.glob(os.path.join(ROOT, "scratchpad/finalfight/gfx/dump/*_ram.bin")))
    for f in files:
        ram = open(f, "rb").read()
        for addr, r in live_records(ram):
            if r[18] not in TAGS: continue
            if r[2] != 2:                          # +2 = 2 is alive; dying (4), intro and free records keep the boxes of their last build
                skipped += 1; continue
            if r[0] & 0x80: continue                  # a record spawned this frame has no boxes yet
            d = derive(r)
            if d is None: continue
            n["rec"] += 1
            ap, hp = ul(r, 112), ul(r, 120)
            if d["atk"]:
                n["atk"] += 1
                ok = (ap == d["atk"][0] and uw(r, 116) == d["atk"][1] and uw(r, 118) == d["atk"][2])
                n["atk_ok"] += ok
                if not ok: bad.append((os.path.basename(f), hex(addr), "atk", hex(ap), d["atk"], uw(r, 116), uw(r, 118)))
            else:
                n["atk_none"] += 1; n["atk_none_ok"] += (ap == 0)
                if ap != 0: bad.append((os.path.basename(f), hex(addr), "atk none", hex(ap)))
            if d["hurt"]:
                n["hurt"] += 1
                ok = (hp == d["hurt"][0] and uw(r, 124) == d["hurt"][1] and uw(r, 126) == d["hurt"][2])
                n["hurt_ok"] += ok
                if not ok: bad.append((os.path.basename(f), hex(addr), "hurt", hex(hp), d["hurt"], uw(r, 124), uw(r, 126)))
            else:
                n["hurt_none"] += 1; n["hurt_none_ok"] += (hp == 0)
                if hp != 0: bad.append((os.path.basename(f), hex(addr), "hurt none", hex(hp)))
    print("not alive (state byte != 2), left out:", skipped)
    print("dumps", len(files), "records with a readable +56:", n["rec"])
    print("attack box: %d of %d equal; no attack box expected: %d of %d have +112 = 0" % (n["atk_ok"], n["atk"], n["atk_none_ok"], n["atk_none"]))
    print("hurt box:   %d of %d equal; no hurt box expected:   %d of %d have +120 = 0" % (n["hurt_ok"], n["hurt"], n["hurt_none_ok"], n["hurt_none"]))
    for b in bad[:12]: print("  miss", b)
    return n, bad
if __name__ == "__main__":
    main()
