"""chars.py: character, boss, prop, item and weapon sprite sheets from the game's own animation scripts.

Frames come from `ffframes.build` (the port of `$16910`, proven word for word against the game's routine by
gate_oracle.py) and the animation scripts that scan_scripts.py finds by the calls of `$3b1c`/`$3b10`.  Owners:
  players   thunks `movea.l 6(PC,D0.w),A1 / jmp $3b1c` (three pointers: Guy, Cody, Haggar, +20 of the player record,
            player.md) plus the direct scripts inside each character's data block (`$a124` data and box pointers:
            Guy `$10ffa`/`$10b76`, Cody `$12b80`/`$12910`, Haggar `$14f4e`/`$14cfa`; scripts placed by address range)
  fighters  `lea 6(PC),A1 / jmp $3b10` per-character word tables (`ai.md`: BRED, DUG, JAKE, SIMONS for kind 0), scripts
            named by the handler region of the call site (`sheetlib.handler_labels`)
  others    bosses, props, weapons, items, pool 8 scenery: scripts by handler region
Palette: the palette RAM of a dump in which the owner is live (records of the pools, census below); the line of
each frame is the one in the frame block (attr bits 0-4), as the game's own list builder writes it.
Usage: python chars.py [owner substring ...]   writes scratchpad/finalfight/gfx/out/chars/*.png"""
import collections, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from cpsgfx import *
import ffframes as F
import sheetlib as S
from census import dumps

OUTD = os.path.join(OUT, "chars")
os.makedirs(OUTD, exist_ok=True)


def live_census():
    """{owner key: [dump index]}.  Keys: ('player', char), ('fighter', kind, char), ('boss', kind), ('weapon', kind),
    ('prop', kind), ('item', type), ('pool8', kind)."""
    ds = dumps()
    cen = collections.defaultdict(list)
    for di, (gp, rp) in enumerate(ds):
        ram = open(rp, "rb").read()
        def rec(base, n, stride):
            for i in range(n):
                r = base + i * stride - 0xff0000
                if ram[r]:
                    yield r
        for r in rec(0xff8568, 2, 0xc0):
            cen[("player", ram[r + 20])].append(di)
        for r in rec(0xff86e8, 13, 0xc0):
            cen[("fighter", ram[r + 19], ram[r + 20])].append(di)
        for r in rec(0xff90a8, 6, 0xc0):
            cen[("weapon", ram[r + 19])].append(di)
        for r in rec(0xff9528, 8, 0xc0):
            cen[("boss", ram[r + 19])].append(di)
        for r in rec(0xff9b28, 30, 0xc0):
            cen[("pool8", ram[r + 19])].append(di)
        for r in rec(0xffb2e8, 16, 0xc0):
            cen[("prop", ram[r + 19])].append(di)
        for r in rec(0xffbee8, 10, 0xc0):
            cen[("item", ram[r + 20])].append(di)
    return ds, cen


def palette_of(ds, di):
    g = np.fromfile(ds[di][0], dtype=">u2")
    ram = np.fromfile(ds[di][1], dtype=">u2")
    regs = regs_from_ram(ram)
    return build_palette(g[cps_base(regs.a[A_PAL], 0x400) // 2:][:0xc00], 0x3f)


def frame_image(G, block, pal, mirror=False):
    ent = F.build(block, 0, 0x80, 0x40, 0, mirror, 0, 0)
    return render_entries(G, ent, pal, anchor=(0, 128))


def script_sheet(G, title, rows, pal, path, per_row=12, scale=1):
    """rows: list of (label, script address).  One strip per script (frames in order, wrapped after per_row)."""
    strips = []
    allw = []
    for label, a in rows:
        frames, loop = F.script(a)
        imgs = []
        for (e, b, d, fl) in frames:
            img, o = frame_image(G, b, pal)
            imgs.append((img, o, b, d))
            if img is not None:
                allw.append((o[0], o[1], o[0] + img.shape[1], o[1] + img.shape[0]))
        strips.append((label, a, imgs, loop))
    if not allw:
        return None
    x0 = min(v[0] for v in allw)
    y0 = min(v[1] for v in allw)
    x1 = max(v[2] for v in allw)
    y1 = max(v[3] for v in allw)
    cw, ch = (x1 - x0 + 4) * scale, (y1 - y0 + 14) * scale
    nrows = sum(max(1, (len(s[2]) + per_row - 1) // per_row) for s in strips)
    W = cw * per_row + 4
    H = 22 + nrows * (ch + 14)
    im = Image.new("RGB", (W, H), S.BG)
    d = ImageDraw.Draw(im)
    d.text((6, 4), title, font=S.FONT, fill=S.FG)
    y = 20
    for (label, a, imgs, loop) in strips:
        n = len(imgs)
        lines = max(1, (n + per_row - 1) // per_row)
        d.text((6, y), "%s  script $%05x  %d frames%s" % (label, a, n, "  loops to $%05x" % loop if loop else ""),
               font=S.FONT_S, fill=S.DIM)
        for li in range(lines):
            yy = y + 12
            for k in range(per_row):
                idx = li * per_row + k
                if idx >= n:
                    break
                img, o, b, dur = imgs[idx]
                cx = 2 + k * cw
                d.rectangle([cx, yy, cx + cw - 2, yy + ch - 2], fill=(S.CHECK_A if (idx % 2 == 0) else S.CHECK_B))
                if img is not None:
                    big = Image.fromarray(img, "RGBA")
                    if scale != 1:
                        big = big.resize((big.width * scale, big.height * scale), Image.NEAREST)
                    im.paste(big, (cx + (o[0] - x0) * scale, yy + (o[1] - y0) * scale), big)
                d.text((cx + 2, yy + ch - 12 * 1), "%x/%d" % (b & 0xfffff, dur), font=S.FONT_S, fill=S.DIM)
            y += ch + 14
            if li < lines - 1:
                pass
        if lines == 0:
            y += ch + 14
    im = im.crop((0, 0, W, min(H, y + 6)))
    im.save(path, optimize=True)
    return im.size


def collect():
    sc = json.load(open(os.path.join(OUT, "scripts.json")))
    owners = collections.defaultdict(list)       # key -> [(label, script address)]
    for a, v in sc.items():
        if not v["ok"]:
            continue
        a = int(a, 16)
        for how, call in v["src"]:
            if how.startswith("tab3["):
                ch = int(how[5])
                owners[("player", ch)].append(("thunk $%05x" % call, a))
            elif how.startswith("wtab["):
                c = int(how[5])
                lab = S.owner_of(call)
                kind = int(lab.split()[2]) if lab and lab.startswith("fighter kind") else None
                if lab and lab.startswith("boss"):
                    owners[("bossw", int(lab.split()[1]), c)].append(("thunk $%05x" % call, a))
                elif kind is not None:
                    owners[("fighter", kind, c)].append(("thunk $%05x" % call, a))
                else:
                    owners[("other", lab or "engine")].append(("thunk $%05x ch%d" % (call, c), a))
            else:
                lab = S.owner_of(call)
                if lab is None:
                    # player code: script lies inside one character's data block
                    if 0xfc00 <= a < 0x14c00:
                        ch = 0 if a < 0x11200 else (1 if a < 0x12dd0 else 2)
                        owners[("player", ch)].append(("direct $%05x" % call, a))
                    else:
                        owners[("other", "player code, script outside the three data blocks")].append(("$%05x" % call, a))
                else:
                    owners[("other", lab)].append(("$%05x" % call, a))
    return owners


NAMES = {("player", 0): "Guy", ("player", 1): "Cody", ("player", 2): "Haggar"}
FIGHTER = {0: ["BRED", "DUG", "JAKE", "SIMONS"], 1: ["J", "TWO.P"], 2: ["AXL", "SLASH"],
           3: ["ANDORE JR.", "ANDORE", "G.ANDORE", "U.ANDORE", "F.ANDORE"], 4: ["G.ORIBER", "BILL BULL", "WONG WHO"],
           5: ["HOLLY WOOD", "EL GADO"], 6: ["ROXY", "POISON"]}


def owner_palette(key, cen, ds, cache):
    """(palette, dump index, description): a dump in which the owner is live; handler-labelled owners match the census
    keys; otherwise Cody's dump."""
    def pal_for(k):
        cands = cen.get(k)
        if not cands:
            return None, None
        di = cands[0]
        if di not in cache:
            cache[di] = palette_of(ds, di)
        return cache[di], di
    pal, di = pal_for(key)
    src = "live in %s" % os.path.basename(ds[di][0]) if pal is not None else None
    if pal is None and key[0] == "other":
        lab = key[1]
        for k2 in cen:
            if (k2[0] == "boss" and lab.startswith("boss %d" % k2[1])) or \
                    (k2[0] == "weapon" and lab == "weapon kind %d" % k2[1]) or \
                    (k2[0] == "prop" and lab.startswith("prop kind %d " % k2[1])) or \
                    (k2[0] == "pool8" and lab == "pool 8 kind %d" % k2[1]) or \
                    (k2[0] == "fighter" and lab.startswith("fighter kind %d " % k2[1])):
                pal, di = pal_for(k2)
                src = "live (%s) in %s" % (k2, os.path.basename(ds[di][0]))
                break
    if pal is None:
        pal, di = pal_for(("player", 1))
        src = "fallback: Cody's dump %s" % os.path.basename(ds[di][0])
    return pal, di, src


def main():
    G = Gfx()
    owners = collect()
    ds, cen = live_census()
    cache = {}

    want = sys.argv[1:]
    report = []
    for key in sorted(owners, key=lambda k: str(k)):
        if key[0] == "player":
            name = NAMES[key]
        elif key[0] == "fighter":
            nm = FIGHTER.get(key[1], [])
            name = "fighter_k%d_%s" % (key[1], nm[key[2]] if key[2] < len(nm) else "c%d" % key[2])
        elif key[0] == "bossw":
            name = "boss%d_c%d" % (key[1], key[2])
        else:
            name = "other_" + key[1].replace(" ", "_").replace("/", "-")
        if key[0] == "bossw" or (key[0] == "fighter" and key[2] >= len(FIGHTER.get(key[1], []))):
            continue
        if want and not any(w.lower() in name.lower() for w in want):
            continue
        pal, di, src = owner_palette(key, cen, ds, cache)
        rows = sorted(set(owners[key]), key=lambda r: (r[1]))
        rows = sorted(owners[key], key=lambda r: r[0])
        seen = set()
        rows = [r for r in rows if not (r[1] in seen or seen.add(r[1]))]
        path = os.path.join(OUTD, name + ".png")
        sz = script_sheet(G, "%s: %d scripts   palette: %s" % (name, len(rows), src), rows, pal, path)
        report.append((name, len(rows), sz, src))
        print("%-40s scripts %3d size %s  %s" % (name, len(rows), sz, src))


if __name__ == "__main__":
    main()
