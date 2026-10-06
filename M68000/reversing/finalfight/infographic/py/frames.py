"""frames.py: the game's own hit and hurt boxes of one saved frame, and the hit test the game would run on them.

Input: a gfx/work-RAM dump of scratchpad/finalfight/gfx/dump (<tag>_ram.bin) and the MAME screenshot of the same frame
(scratchpad/finalfight/run/snap/<tag>.png). Everything is read from the work RAM and the program ROM, nothing is estimated:
  record      $c0 bytes at $ff8568 + n * $c0 (frame.md "The player and fighter record"): x +6, y +10, ground line +14, tag +18, kind +19, char +20,
              state +2, hit reaction id +22, health +24, boxes +112/+116/+118 (attack) and +120/+124/+126 (hurt); the descriptor
              pointers lead to dx, dy, half width, half height words in the ROM
  camera      1042(A5) = $8412 (x), 1046(A5) = $8416 (y)
  to screen   x - camx, 240 - (y - camy)  (the object-list builder $16910 negates y and the CPS clip window starts at y 16, x 64)
Candidate rules (frame.md "Hit resolution", $3382 / $33c4 / $33f2 / $3428 / $3578 / $35ae, disassembled again for this figure):
  x window  (candidate x - player x + $80) <= $100 unsigned, that is -128 <= dx <= +128
  lane      g = candidate ground line - player ground line: g in [-12, +9] (the list rectangle that $8d70 writes, [-24, +24] during the special)
  overlap   $7932: ((hurt cx - attack cx) + (hw1 + hw2)) & $ffff <= 2 * (hw1 + hw2), then the same on y with the half heights"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
ROM = open(os.environ.get("FF_MAIN", os.path.join(ROOT, "scratchpad/finalfight/ff_main.bin")), "rb").read()
DUMP = os.path.join(ROOT, "scratchpad/finalfight/gfx/dump")
SNAP = os.path.join(ROOT, "scratchpad/finalfight/run/snap")


def sw(b, a): return struct.unpack(">h", b[a:a + 2])[0]
def uw(b, a): return struct.unpack(">H", b[a:a + 2])[0]
def ul(b, a): return struct.unpack(">I", b[a:a + 4])[0]


def passes(d, s):
    """The $7932 axis test: ((d + s) & $ffff) <= (2 s) & $ffff, s = sum of the two half sizes."""
    return ((d + s) & 0xffff) <= ((2 * s) & 0xffff)


def load(tag):
    ram = open(os.path.join(DUMP, tag + "_ram.bin"), "rb").read()
    camx, camy = uw(ram, 0x8412), uw(ram, 0x8416)
    recs = []
    for i in range((0xb1a8 - 0x8568) // 0xc0):
        a = 0x8568 + i * 0xc0
        r = ram[a:a + 0xc0]
        if not r[0] or r[18] not in (0, 2, 4): continue
        d = dict(addr=0xff0000 + a, tag=r[18], kind=r[19], char=r[20], state=r[2], sub=r[3], x=uw(r, 6), y=uw(r, 10), g=uw(r, 14), hp=sw(r, 24),
                 hit22=r[22], by=0xff0000 + uw(r, 60) if uw(r, 60) else 0, stop=r[23], atk=None, hurt=None)
        ap, hp = ul(r, 112), ul(r, 120)
        if 0 < ap < len(ROM) - 16:
            d["atk"] = dict(cx=uw(r, 116), cy=uw(r, 118), hw=sw(ROM, ap + 4), hh=sw(ROM, ap + 6), row=uw(ROM, ap + 8) >> 5, type=ROM[ap + 11] & 0x7f)
        if 0 < hp < len(ROM) - 8:
            d["hurt"] = dict(cx=uw(r, 124), cy=uw(r, 126), hw=sw(ROM, hp + 4), hh=sw(ROM, hp + 6))
        recs.append(d)
    return dict(tag=tag, camx=camx, camy=camy, recs=recs)


def overlaps(frame):
    """Every pair whose boxes overlap by the $7932 test, whatever the queue says, tagged 'tested' when a player is one side and a
    fighter or boss the other (the only pairs the candidate lists can hold) and 'landed' when the victim's record says this
    attacker hit it (+60 = attacker, +22 = the blow id: the frame the dump was taken on is the frame the blow resolved)."""
    out = []
    for a in frame["recs"]:
        for v in frame["recs"]:
            if a is v or not a["atk"] or not v["hurt"]: continue
            s_x = a["atk"]["hw"] + v["hurt"]["hw"]; s_y = a["atk"]["hh"] + v["hurt"]["hh"]
            dx = v["hurt"]["cx"] - a["atk"]["cx"]; dy = v["hurt"]["cy"] - a["atk"]["cy"]
            if not (passes(dx, s_x) and passes(dy, s_y)): continue
            tested = (a["tag"] == 0 and v["tag"] in (2, 4)) or (v["tag"] == 0 and a["tag"] in (2, 4))
            out.append(dict(att=a, vic=v, dx=dx, sx=s_x, dy=dy, sy=s_y, tested=tested, landed=bool(v["by"] == a["addr"] and v["hit22"])))
    return out


def hits(frame):
    """Every (attacker, victim) the game would queue and overlap: a player's blow on a fighter or boss, a fighter's blow on a player.
    Also lists the overlaps the game never tests (a fighter's box over another fighter)."""
    recs = frame["recs"]
    players = [r for r in recs if r["tag"] == 0 and r["state"] == 2 and r["hit22"] == 0]
    out, untested = [], []
    for a in recs:
        for v in recs:
            if a is v or not a["atk"] or not v["hurt"]: continue
            s_x = a["atk"]["hw"] + v["hurt"]["hw"]; s_y = a["atk"]["hh"] + v["hurt"]["hh"]
            if not (passes(v["hurt"]["cx"] - a["atk"]["cx"], s_x) and passes(v["hurt"]["cy"] - a["atk"]["cy"], s_y)): continue
            pair = (a, v)
            if a["tag"] == 0 and v["tag"] in (2, 4): player, other = a, v
            elif v["tag"] == 0 and a["tag"] in (2, 4): player, other = v, a
            else:
                untested.append(pair); continue
            if player not in players: untested.append(pair); continue
            dxr = other["x"] - player["x"]; g = other["g"] - player["g"]
            if 0 <= dxr + 0x80 <= 0x100 and -12 <= g <= 9:
                out.append(dict(att=a, vic=v, dxr=dxr, g=g, dx=v["hurt"]["cx"] - a["atk"]["cx"], sx=s_x, dy=v["hurt"]["cy"] - a["atk"]["cy"], sy=s_y))
            else:
                untested.append(pair)
    return out, untested


if __name__ == "__main__":
    for tag in sys.argv[1:] or ["st_bb_4800_1", "st_a_boss_mid_1"]:
        f = load(tag)
        h, u = hits(f)
        print(tag, "camera", f["camx"], f["camy"])
        for r in f["recs"]:
            print("  %06x tag %d kind %d char %d x %d g %d hp %d atk %s hurt %s" % (r["addr"], r["tag"], r["kind"], r["char"], r["x"], r["g"], r["hp"], r["atk"], r["hurt"]))
        for x in h: print("  HIT %06x -> %06x" % (x["att"]["addr"], x["vic"]["addr"]), {k: v for k, v in x.items() if k not in ("att", "vic")})
        for a, v in u: print("  overlap the game does not test %06x -> %06x" % (a["addr"], v["addr"]))
