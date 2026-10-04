"""pics_atlas.py - PNG atlases of BTCLIPS, BTOBJ, BT5 (ending picture)."""
import os

from pics import *  # noqa


def sheet(ents, pal, name, scale=3, cols=6):
    items = [(k, r) for k, r in enumerate(ents) if r]
    seen = {}
    uniq = []
    for k, r in items:
        key = tuple(map(tuple, r))
        if key in seen:
            continue
        seen[key] = k
        uniq.append((k, r))
    cw = max(len(r[0]) for k, r in uniq) + 4
    ch = max(len(r) for k, r in uniq) + 4
    # big pictures get their own rows
    small = [(k, r) for k, r in uniq if len(r[0]) <= 64 and len(r) <= 40]
    big = [(k, r) for k, r in uniq if not (len(r[0]) <= 64 and len(r) <= 40)]
    scw, sch = 68, 44
    rows = (len(small) + cols - 1) // cols
    H = rows * sch + sum(len(r) + 4 for k, r in big)
    W = max(cols * scw, max((len(r[0]) + 4 for k, r in big), default=0))
    img = Image.new("RGBA", (W, H), (40, 0, 40, 255))
    for i, (k, r) in enumerate(small):
        img.alpha_composite(indexed_image(r, pal, True), ((i % cols) * scw + 2, (i // cols) * sch + 2))
    y = rows * sch
    for k, r in big:
        img.alpha_composite(indexed_image(r, pal, False), (2, y + 2))
        y += len(r) + 4
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(os.path.join(PNG, name))
    print(name, "unique pictures", [k for k, r in uniq])


def main():
    t0 = read_file("T0")
    pal = pal_from_bytes(t0, 0)
    for nm in ("BTCLIPS", "BTOBJ"):
        d, offs, ents = collection(nm)
        sheet(ents, pal, "pics_%s.png" % nm, scale=3 if nm == "BTOBJ" else 2)
    ram = load_snap("agents/graphics/snaps/L0a.snap")
    epal = [w16(ram, 0x172f6 + 2 * i) for i in range(16)]
    print("ending palette $172f6:", [hex(p) for p in epal])
    d = read_file("BT5")
    rows = pic_rows(d, 0)
    indexed_image(rows, epal).resize((96 * 3, 112 * 3), Image.NEAREST).save(os.path.join(PNG, "pic_BT5_ending.png"))


if __name__ == "__main__":
    main()
