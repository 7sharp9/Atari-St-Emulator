"""build.py: writes infographic/finalfight_hit_detection.html from the program ROM, the saved work-RAM dumps and the MAME screenshots.

Inputs (all derived, nothing typed in from memory):
  frames.py                 boxes of the two landing frames (st_bb_4800_1, st_a_boss_mid_1) read from work RAM and the ROM
  ../../py/player/ffchar.py attack boxes, damage rows, awards of Guy, Cody and Haggar from the ROM
  scratchpad/finalfight/run/snap/<tag>.png   the MAME screenshots of those frames (copied to assets/ so the page does not need the scratchpad)
Usage: python py/build.py     (from reversing/finalfight/infographic, with M68000/.venv)
Set ARTIFACT_FRAGMENT=<path> to also write the fragment the Artifact tool publishes."""
import base64, html, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import frames as F
sys.path.insert(0, os.path.join(BASE, "..", "py", "player"))
import ffchar as C

esc = lambda s: html.escape(str(s), quote=True)
CHAR = {0: "Guy", 1: "Cody", 2: "Haggar"}
KIND0 = {0: "BRED", 1: "DUG", 2: "JAKE", 3: "SIMONS"}      # ai.md: +20 of a kind 0 fighter, names from the game's HUD text
KINDS = {1: ("J", "TWO.P"), 2: ("AXL", "SLASH"), 5: ("HOLLY WOOD", "EL GADO")}


def name(r):
    if r["tag"] == 0: return "%s (P%d)" % (CHAR[r["char"]], 1 if r["addr"] == 0xff8568 else 2)
    if r["tag"] == 4: return "DAMND" if r["kind"] == 0 else "boss kind %d" % r["kind"]
    if r["kind"] == 0: return KIND0.get(r["char"], "kind 0")
    return (KINDS.get(r["kind"]) or ("kind %d" % r["kind"],) * 2)[min(r["char"], 1)]


def png_data(tag):
    src = os.path.join(F.SNAP, tag + ".png")
    dst = os.path.join(BASE, "assets", tag + ".png")
    if os.path.exists(src): shutil.copyfile(src, dst)
    return "data:image/png;base64," + base64.b64encode(open(dst, "rb").read()).decode()


# ---------------------------------------------------------------- the two landing frames
def hero(tag, label):
    f = F.load(tag)
    ov = [o for o in F.overlaps(f) if o["landed"]]
    assert len(ov) == 1, (tag, len(ov))
    land = ov[0]
    cx, cy = f["camx"], f["camy"]
    out = ['<svg class="frame" viewBox="0 0 384 224" role="img" aria-label="%s"><image href="%s" width="384" height="224"/>' % (esc(label), png_data(tag))]
    def box(b, cls, tip):
        x0 = b["cx"] - b["hw"] - cx; y0 = 240 - (b["cy"] + b["hh"]) + cy
        return '<g class="cell" data-tip="%s"><rect class="bx %s" x="%d" y="%d" width="%d" height="%d"/></g>' % (esc(tip), cls, x0, y0, 2 * b["hw"], 2 * b["hh"]), (x0, y0)
    for r in f["recs"]:
        if r["hurt"] and r is not land["vic"]:
            s, _ = box(r["hurt"], "hurt", "%s hurt box: centre (%d, %d), half %d x %d" % (name(r), r["hurt"]["cx"], r["hurt"]["cy"], r["hurt"]["hw"], r["hurt"]["hh"]))
            out.append(s)
    s, vpos = box(land["vic"]["hurt"], "hit", "%s hurt box: centre (%d, %d), half %d x %d" % (name(land["vic"]), land["vic"]["hurt"]["cx"], land["vic"]["hurt"]["cy"], land["vic"]["hurt"]["hw"], land["vic"]["hurt"]["hh"]))
    out.append(s)
    for r in f["recs"]:
        if r["atk"] and r is not land["att"]:
            s, _ = box(r["atk"], "atk", "%s attack box" % name(r)); out.append(s)
    a = land["att"]["atk"]
    s, apos = box(a, "hit", "%s attack box: centre (%d, %d), half %d x %d, damage row %d, hit type %d" % (name(land["att"]), a["cx"], a["cy"], a["hw"], a["hh"], a["row"], a["type"]))
    out.append(s)
    out.append('<text class="ann" x="%d" y="%d">attack box</text>' % (apos[0] + 2, max(apos[1] - 3, 9)))
    out.append('<text class="ann" x="%d" y="%d">hurt box</text>' % (vpos[0] + 2, vpos[1] + 2 * land["vic"]["hurt"]["hh"] + 9))
    out.append("</svg>")
    return "".join(out), f, land


def worked(f, land):
    a, v = land["att"], land["vic"]
    player = a if a["tag"] == 0 else v
    other = v if a["tag"] == 0 else a
    dxr = other["x"] - player["x"]; g = other["g"] - player["g"]
    ok = lambda c: '<span class="pass">pass</span>' if c else '<span class="fail">fail</span>'
    rows = [
        ("attack box", "%s: centre (%d, %d), half %d × %d" % (name(a), a["atk"]["cx"], a["atk"]["cy"], a["atk"]["hw"], a["atk"]["hh"]), ""),
        ("hurt box", "%s: centre (%d, %d), half %d × %d" % (name(v), v["hurt"]["cx"], v["hurt"]["cy"], v["hurt"]["hw"], v["hurt"]["hh"]), ""),
        ("1 reach list", "x gap %d, %d + 128 = %d ≤ 256" % (dxr, dxr, dxr + 128), ok(0 <= dxr + 128 <= 256)),
        ("2 depth lane", "ground line gap %+d, window −12 to +9" % g, ok(-12 <= g <= 9)),
        ("3 x overlap", "dx %d, s %d: %d ≤ %d" % (land["dx"], land["sx"], (land["dx"] + land["sx"]) & 0xffff, 2 * land["sx"]), ok(F.passes(land["dx"], land["sx"]))),
        ("4 y overlap", "dy %d, s %d: %d ≤ %d" % (land["dy"], land["sy"], (land["dy"] + land["sy"]) & 0xffff, 2 * land["sy"]), ok(F.passes(land["dy"], land["sy"]))),
    ]
    assert all("fail" not in r[2] for r in rows)
    return "<table>" + "".join("<tr><th>%s</th><td>%s</td><td>%s</td></tr>" % (esc(k), esc(v_), p) for k, v_, p in rows) + "</table>"


# ---------------------------------------------------------------- reach
STAND = {0: (0, 35, 14, 36), 1: (0, 35, 14, 36), 2: (3, 35, 18, 36)}   # hurt box 1 of each character (py/player/boxes.py hurt)
PLAN = [  # character, [(label, [ids])]
    (0, [("chain hits 1, 2", [1]), ("chain hit 3", [2]), ("chain hit 4", [7]), ("chain finisher, hit 5", [0xd]), ("jump attack", [3]), ("jump, down", [8]), ("special, all boxes", list(range(0xf, 0x19)))]),
    (1, [("chain hits 1, 2", [1]), ("chain hit 3", [2]), ("chain finisher, hit 4", [3]), ("jump, diagonal", [0xc]), ("jump, vertical", [0xd]), ("jump, down", [0xe]), ("special, all boxes", [6, 7, 8, 9, 0xa])]),
    (2, [("chain hits 1, 2", [1]), ("chain finisher, hit 3", [2]), ("jump attack", [3]), ("jump attack, second", [4]), ("special, all boxes", [6, 9])]),
]


def blow_info(ch, i):
    b = C.attack_box(ch, i)
    return dict(id=i, dx=b["dx"], dy=b["dy"], hw=b["hw"], hh=b["hh"], dmg=C.damage_row_value(ch, b["off"]), type=b["hit"], hard=b["hard"], award=C.hit_award(ch, b["off"])[1])


def cell(ch, label, ids):
    k = 1.0; x0, x1, h0, h1 = -125, 135, -75, 95
    X = lambda x: (x - x0) * k; Y = lambda h: (h1 - h) * k
    bx, by, bw, bh = STAND[ch]
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s, %s">' % (x1 - x0, h1 - h0, CHAR[ch], esc(label))]
    out.append('<line class="ground" x1="0" y1="%d" x2="%d" y2="%d"/>' % (Y(0), x1 - x0, Y(0)))
    out.append('<rect class="bx hurt dim" x="%d" y="%d" width="%d" height="%d"/>' % (X(bx - bw), Y(by + bh), 2 * bw, 2 * bh))
    infos = [blow_info(ch, i) for i in ids]
    infos = [b for b in infos if b["hw"] or b["hh"]]
    front = 0
    for b in infos:
        front = max(front, b["dx"] + b["hw"])
        out.append('<g class="cell" data-tip="%s"><rect class="bx atk" x="%d" y="%d" width="%d" height="%d"/></g>' % (
            esc("%s id %02x: dx %d, dy %d, half %d × %d; damage %d, type %d" % (CHAR[ch], b["id"], b["dx"], b["dy"], b["hw"], b["hh"], b["dmg"], b["type"])),
            X(b["dx"] - b["hw"]), Y(b["dy"] + b["hh"]), 2 * b["hw"], 2 * b["hh"]))
    out.append("</svg>")
    if len(infos) == 1:
        b = infos[0]
        sub = "id %02x · front edge %d px<br>%d damage · type %d%s · +%d" % (b["id"], b["dx"] + b["hw"], b["dmg"], b["type"], " hard" if b["hard"] else "", b["award"] or 0)
    else:
        span = ("ids %02x to %02x" % (ids[0], ids[-1])) if ids == list(range(ids[0], ids[-1] + 1)) else ("ids " + ", ".join("%02x" % i for i in ids))
        sub = "%s · front edge %d px<br>%d damage · type %d" % (span, front, infos[0]["dmg"], infos[0]["type"])
    return '<div class="mv">%s<div class="t">%s</div><div class="s">%s</div></div>' % ("".join(out), esc(label), sub)


def reach():
    out = []
    for ch, moves in PLAN:
        out.append('<div class="who"><h3>%s <span>chain limit %d hits · box table %05x</span></h3><div class="cells">' % (CHAR[ch], C.combo_limit(ch), C.box_base(ch)))
        out.extend(cell(ch, l, ids) for l, ids in moves)
        out.append("</div></div>")
    return "".join(out)


def cody_table():
    rows = [("Jab, chain hits 1 and 2", 1), ("Chain hit 3", 2), ("Chain finisher", 3), ("Jump, diagonal", 0xc), ("Jump, vertical", 0xd), ("Jump, down", 0xe), ("Jump, down backwards", 0x13),
            ("Special (spin)", 6), ("Knife stab (weapon)", 0x10), ("Pipe or sword swing (weapon)", 0x11)]
    out = ['<table class="data"><tr><th>Cody\'s blow</th><th class="n">box id</th><th class="n">front edge</th><th class="n">height above feet</th><th class="n">damage</th><th class="n">hit type</th><th class="n">score</th></tr>']
    for l, i in rows:
        b = blow_info(1, i)
        out.append('<tr><td>%s</td><td class="n">%02x</td><td class="n">%d px</td><td class="n">%d to %d</td><td class="n">%d</td><td class="n">%d%s</td><td class="n">%d</td></tr>' % (
            esc(l), i, b["dx"] + b["hw"], b["dy"] - b["hh"], b["dy"] + b["hh"], b["dmg"], b["type"], " hard" if b["hard"] else "", b["award"] or 0))
    out.append("</table>")
    return "".join(out)


# ---------------------------------------------------------------- widget data
def widget():
    pick = [(1, 1, "jab"), (1, 2, "chain hit 3"), (1, 3, "chain finisher"), (1, 0xc, "jump, diagonal"), (1, 0xd, "jump, vertical"), (1, 0xe, "jump, down"), (1, 7, "special, front spin"),
            (0, 1, "jab"), (0, 0xd, "chain finisher"), (2, 1, "jab"), (2, 2, "chain finisher")]
    blows = []
    for ch, i, l in pick:
        b = C.attack_box(ch, i)
        blows.append(dict(label="%s · %s (id %02x, front edge %d)" % (CHAR[ch], l, i, b["dx"] + b["hw"]), dx=b["dx"], dy=b["dy"], hw=b["hw"], hh=b["hh"]))
    victims = [dict(label="Standard fighter, hurt box 28 × 72", dx=0, dy=35, hw=14, hh=36), dict(label="Boss DAMND, hurt box 46 × 78", dx=0, dy=37, hw=23, hh=39)]
    ix = lambda ch, i: [n for n, (c, j, _) in enumerate(pick) if (c, j) == (ch, i)][0]
    pre = [dict(blow=ix(1, 1), vict=1, x=43, g=0, sp=0), dict(blow=ix(1, 1), vict=0, x=100, g=0, sp=0), dict(blow=ix(1, 1), vict=0, x=43, g=10, sp=0),
           dict(blow=ix(1, 1), vict=0, x=43, g=-12, sp=0), dict(blow=ix(1, 7), vict=0, x=60, g=20, sp=1)]
    return dict(blows=blows, victims=victims), pre


# ---------------------------------------------------------------- page
def build():
    a_svg, fa, la = hero("st_bb_4800_1", "A frame of stage 1: BRED's jab lands on Cody, with every hurt and attack box drawn over it")
    b_svg, fb, lb = hero("st_a_boss_mid_1", "A frame of the stage 0 boss fight: Cody's jab lands on DAMND, with every hurt and attack box drawn over it")
    ca = la["vic"]; ba = la["att"]
    cap_a = ("<b>BRED jabs Cody.</b> Stage 1, camera x %d. Cody's record names the attacker (<code>+60</code> = $%x, BRED), the blow (<code>+22</code> = %d) and a hit-stop of %d frames. "
             "The jab box also covers the knife fighter beside BRED. Nothing happens to him: the game tests blows only against players.") % (fa["camx"], ba["addr"] & 0xffffff, ca["hit22"], ca["stop"])
    cb = lb["vic"]; bb = lb["att"]
    cap_b = ("<b>Cody jabs DAMND.</b> Stage 0 boss fight, camera x %d. DAMND's record names Cody (<code>+60</code> = $%x) and the blow (<code>+22</code> = %d). "
             "The jab box is %d wide and %d tall, %d to %d px above Cody's feet. DAMND's hurt box is %d by %d.") % (
        fb["camx"], bb["addr"] & 0xffffff, cb["hit22"], 2 * bb["atk"]["hw"], 2 * bb["atk"]["hh"], bb["atk"]["cy"] - bb["atk"]["hh"] - bb["y"], bb["atk"]["cy"] + bb["atk"]["hh"] - bb["y"], 2 * cb["hurt"]["hw"], 2 * cb["hurt"]["hh"])
    data, pre = widget()
    css = open(os.path.join(HERE, "style.css")).read()
    js = open(os.path.join(HERE, "page.js")).read()
    tpl = open(os.path.join(HERE, "page.html")).read()
    page = (tpl.replace("{{CSS}}", css).replace("{{JS}}", js).replace("{{DATA}}", json.dumps(data))
            .replace("{{HEROA}}", a_svg).replace("{{HEROB}}", b_svg).replace("{{CAPA}}", cap_a).replace("{{CAPB}}", cap_b)
            .replace("{{WORKEDA}}", worked(fa, la)).replace("{{WORKEDB}}", worked(fb, lb)).replace("{{REACH}}", reach()).replace("{{COBLOWS}}", cody_table()))
    for n, p in enumerate(pre, 1): page = page.replace("{{PRE%d}}" % n, json.dumps(p))
    left = re.findall(r"\{\{[A-Z0-9]+\}\}", page)
    assert not left, left
    out = os.path.join(BASE, "finalfight_hit_detection.html")
    open(out, "w").write('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>' + page + "</body></html>")
    frag = os.environ.get("ARTIFACT_FRAGMENT")
    if frag: open(frag, "w").write(page)
    print("wrote", out, len(page) // 1024, "KiB")


if __name__ == "__main__":
    build()
