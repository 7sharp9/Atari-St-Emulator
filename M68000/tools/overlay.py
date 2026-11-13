"""overlay.py <layout.toml> <snap> <out.png> [--scale N] [--fields a,b,...] [--check]: a game's object slots drawn over its screen.

Renders the snapshot's live screen (`tools/snap_render.py`, so the shifter base, resolution and palette are the live
ones) and draws, for every live slot of each array the schema's `[overlay]` table names, a box at the slot's on-screen
position labelled with the slot index and chosen fields (`kind`, hit points, AI state). Headless: snapshot in, PNG out.

The projection from a slot's fields to screen pixels is data in the schema (DEVELOPING.md "Memory layouts and the
semantic snapshot diff", `[overlay]`), one sub-table per array:

    [overlay.objects]                       # a layer; `array` names an array of `[arrays]` (default: the layer's key)
    array = "objects"
    x = "x"                                 # struct field names (or a number) for the slot's position
    y = "y"
    div_x = 1                               # field units per pixel (16 for a 12.4 fixed-point x)
    div_y = 1
    camera_x = "w[0x227b6]"                 # address expression subtracted before dividing (default 0)
    camera_y = 0
    origin_x = 0                            # pixels added after dividing (playfield origin, sprite hot spot)
    origin_y = 0
    w = { field = "type", map = { 1 = 16, 2 = 32 } }   # a number, a field name, or a field-to-number map
    h = "rows"
    live = ["type in 1,2"]                  # every condition must hold: field OP number, OP in == != < <= > >= in &;
                                            # `slot` is the slot index ("slot in 7,8,9,10,11")
    label = ["type", "hp"]                  # fields printed after the slot index
    cite = "graphics.md \"Sprites\" (...)"

    screen_x = (x - camera_x) / div_x + origin_x        (integer division toward minus infinity)

A slot whose liveness test fails, or whose fields leave RAM, is not drawn. `--fields` replaces every layer's `label`.
`--check` validates the `[overlay]` table only (fields exist in the array's struct, conditions parse, every layer has a
`cite` whose file exists). `tools/layout.py --check` ignores the table, so run this one too after editing it.

    import overlay; L = layout.load(p); O = overlay.load_overlay(L, p)
    boxes = overlay.boxes(L, O, ram)        # [Box(layer, index, name, addr, x, y, w, h, label)]
"""
import argparse
import os
import re
import sys
import tempfile
import tomllib
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402
import snap_render  # noqa: E402
from gfxview import load_ram  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

_LAYER_KEYS = {"array", "x", "y", "div_x", "div_y", "camera_x", "camera_y", "origin_x", "origin_y", "w", "h", "live", "label",
               "colour", "cite", "note"}
_COND = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|<=|>=|<|>|in|&)\s*(.+?)\s*$")
_PALETTE = [(255, 255, 0), (0, 255, 255), (255, 96, 255), (96, 255, 96), (255, 160, 64)]


@dataclass
class Box:
    layer: str       # the [overlay.<layer>] key
    index: int
    name: str        # "objects[6:hero]"
    addr: int        # the slot's address
    x: int
    y: int
    w: int
    h: int
    label: str


def _num(v):
    return layout._int(v, "overlay")


def load_overlay(L, path):
    """The `[overlay]` table of a schema already loaded by `layout.load`, validated; raises LayoutError."""
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)
    spec = doc.get("overlay")
    if not spec:
        raise layout.LayoutError(f"{path}: no [overlay] table")
    errors, layers = [], []
    arrays = {a["name"]: a for a in L["arrays"]}
    for lname, s in spec.items():
        what = f"overlay.{lname}"
        if not isinstance(s, dict):
            errors.append(f"{what}: expected a table per array")
            continue
        bad = set(s) - _LAYER_KEYS
        if bad:
            errors.append(f"{what}: unknown keys {sorted(bad)}")
        layout._check_cite(s, what, L["root"], errors)
        aname = s.get("array", lname)
        arr = arrays.get(aname)
        if arr is None:
            errors.append(f"{what}: no array {aname!r} in [arrays]")
            continue
        fields = {f["name"]: f for f in arr["struct"]["fields"]}

        def fref(v, key):
            if isinstance(v, int):
                return ("const", v)
            if isinstance(v, str) and v in fields:
                return ("field", fields[v])
            if isinstance(v, dict) and set(v) == {"field", "map"} and v["field"] in fields:
                return ("map", fields[v["field"]], {_num(k): _num(n) for k, n in v["map"].items()})
            errors.append(f"{what}.{key}: {v!r} is not a number, a field of struct {arr['struct']['name']!r}, "
                          f"or {{ field = ..., map = {{...}} }}")
            return ("const", 0)

        lay = dict(name=lname, array=arr, cite=s.get("cite", ""))
        for k in ("x", "y", "w", "h"):
            if k not in s:
                errors.append(f"{what}: `{k}` is required")
            lay[k] = fref(s.get(k, 0), k)
        for k in ("camera_x", "camera_y"):
            try:
                lay[k] = layout._Expr(s.get(k, 0), L["symbols"])
            except layout.LayoutError as e:
                errors.append(f"{what}.{k}: {e}")
                lay[k] = layout._Expr(0, {})
        for k in ("div_x", "div_y"):
            lay[k] = _num(s.get(k, 1))
            if lay[k] <= 0:
                errors.append(f"{what}.{k}: must be positive")
        lay["origin_x"], lay["origin_y"] = _num(s.get("origin_x", 0)), _num(s.get("origin_y", 0))
        conds = []
        for c in s.get("live", []):
            m = _COND.match(c)
            if not m or (m.group(1) not in fields and m.group(1) != "slot"):
                errors.append(f"{what}.live: cannot parse {c!r} (field OP number, OP in == != < <= > >= in &)")
                continue
            try:
                rhs = [_num(t) for t in m.group(3).split(",")] if m.group(2) == "in" else _num(m.group(3))
            except ValueError:
                errors.append(f"{what}.live: bad number in {c!r}")
                continue
            conds.append((fields.get(m.group(1), "slot"), m.group(2), rhs))
        lay["live"] = conds
        lay["label"] = []
        for n in s.get("label", []):
            if n not in fields:
                errors.append(f"{what}.label: no field {n!r}")
            else:
                lay["label"].append(fields[n])
        lay["fields"] = fields
        lay["colour"] = tuple(s["colour"]) if "colour" in s else _PALETTE[len(layers) % len(_PALETTE)]
        layers.append(lay)
    if errors:
        raise layout.LayoutError(f"{path}:\n  " + "\n  ".join(errors))
    return layers


def _val(f, ram, slot):
    """(signed-or-unsigned int, Value) of a struct field, or (None, Value) when it leaves RAM."""
    v = layout._read_field(f, ram, slot, f["name"])
    if v.raw is None:
        return None, v
    n = v.raw
    if f["signed"] and n & (1 << (8 * f["width"] - 1)):
        n -= 1 << (8 * f["width"])
    return n, v


def _ref(r, ram, slot):
    if r[0] == "const":
        return r[1]
    n, _ = _val(r[1], ram, slot)
    if n is None or r[0] == "field":
        return n
    return r[2].get(n)


_OPS = {"==": lambda n, r: n == r, "!=": lambda n, r: n != r, "<": lambda n, r: n < r, "<=": lambda n, r: n <= r,
        ">": lambda n, r: n > r, ">=": lambda n, r: n >= r, "in": lambda n, r: n in r, "&": lambda n, r: bool(n & r)}


def _holds(n, op, rhs):
    return _OPS[op](n, rhs)


def boxes(L, layers, ram, label_fields=None):
    """[Box] for every live slot of every layer in this RAM image."""
    out = []
    for lay in layers:
        arr = lay["array"]
        try:
            cx, cy = lay["camera_x"].eval(ram), lay["camera_y"].eval(ram)
        except layout._OffRam:
            continue
        cx = cx - (1 << 32) if cx & 0x80000000 else cx
        cy = cy - (1 << 32) if cy & 0x80000000 else cy
        labels = lay["label"] if label_fields is None else [lay["fields"][n] for n in label_fields if n in lay["fields"]]
        for i, slot in layout.array_slots(L, arr, ram):
            ok = True
            for f, op, rhs in lay["live"]:
                n = i if f == "slot" else _val(f, ram, slot)[0]
                if n is None or not _holds(n, op, rhs):
                    ok = False
                    break
            if not ok:
                continue
            x, y, w, h = (_ref(lay[k], ram, slot) for k in ("x", "y", "w", "h"))
            if None in (x, y, w, h):
                continue
            sx = (x - cx) // lay["div_x"] + lay["origin_x"]
            sy = (y - cy) // lay["div_y"] + lay["origin_y"]
            text = " ".join(f"{f['name']}={_val(f, ram, slot)[1].text}" for f in labels)
            out.append(Box(lay["name"], i, layout.slot_name(arr, i), slot, sx, sy, w, h, f"{i} {text}".rstrip()))
    return out


def render(L, layers, snap, out, scale=2, label_fields=None):
    """Write the overlay PNG; returns the boxes drawn."""
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "screen.png")
        snap_render.render(snap, base)
        img = Image.open(base).convert("RGB")
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    ram, _ = load_ram(snap)
    bx = boxes(L, layers, ram, label_fields)
    d = ImageDraw.Draw(img)
    colour = {lay["name"]: lay["colour"] for lay in layers}
    for b in bx:
        c = colour[b.layer]
        x0, y0 = b.x * scale, b.y * scale
        d.rectangle([x0, y0, x0 + b.w * scale - 1, y0 + b.h * scale - 1], outline=c)
        tw = d.textlength(b.label)
        ty = y0 - 11 if y0 >= 11 else y0 + b.h * scale + 1
        d.rectangle([x0, ty, x0 + tw + 2, ty + 10], fill=(0, 0, 0))
        d.text((x0 + 1, ty), b.label, fill=c)
    img.save(out)
    return bx


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("layout")
    ap.add_argument("snap", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--fields", help="comma-separated label fields, replacing each layer's `label`")
    ap.add_argument("--check", action="store_true", help="validate the [overlay] table only")
    a = ap.parse_args(argv)
    try:
        L = layout.load(a.layout)
        layers = load_overlay(L, a.layout)
    except layout.LayoutError as e:
        sys.exit(str(e))
    if a.check or not a.out:
        print(f"{a.layout}: overlay ok ({len(layers)} layers: "
              f"{', '.join(l['name'] + ' on ' + l['array']['name'] for l in layers)})")
        return
    fields = a.fields.split(",") if a.fields else None
    unknown = [n for n in fields or [] if not any(n in lay["fields"] for lay in layers)]
    if unknown:
        sys.exit(f"--fields: no layer's struct has {unknown}")
    for b in render(L, layers, a.snap, a.out, a.scale, fields):
        print(f"{b.layer:<8} {b.name:<20} box ({b.x},{b.y}) {b.w}x{b.h}  {b.label}")
    print(f"wrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
