"""layout.py <layout.toml> <snap> [--array NAME] [--all-slots] [--check]: decode a snapshot's RAM through a game's memory schema.

A schema (`reversing/<game>/layout.toml`, format in DEVELOPING.md "Memory layouts and the semantic snapshot diff") names
globals, arrays of structs and raw regions; every entry cites the doc section that proves it. This module loads it,
validates it (every entry has a `cite` whose file exists next to the schema, widths are 1/2/4, offsets fit the struct)
and decodes a `.snap` into an ordered list of named values. `tools/snapdiff.py` diffs two decodes.

    import sys; sys.path.insert(0, '<M68000>/tools'); import layout
    L = layout.load('reversing/cadaver/layout.toml')
    vals = layout.decode_snap(L, 'scratchpad/x.snap')     # [Value(name, addr, width, raw, text, cite)]

Address expressions (`addr`, `base`, `count`): terms joined by `+`/`-`; a term is a number (`0x1a2ea`, `$1a2ea`,
`1174`), a symbol from `[symbols]`, `.` (the struct slot's own address, fields only), `[e]` (the longword at e),
`w[e]` (the word at e) or `b[e]` (the byte at e). Cadaver's `[A5+56]` is "the pointer at 56(A5)".
The RAM image and registers come from `tools/gfxview.py`'s `load_ram`/`snapshot_regs` (the `.snap` header has an
int16 CCR; do not re-derive it here).
"""
import os
import re
import sys
import tomllib
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfxview import load_ram, snapshot_regs  # noqa: E402


class LayoutError(Exception):
    pass


@dataclass
class Value:
    name: str        # "health", "objects[0:hero].x_lead"
    addr: int        # address of the field's bytes, or -1 when its pointer chain left RAM
    width: int
    raw: int | None  # unsigned raw value, None when unreadable
    text: str        # rendered value (signed, enum name, bit names, hex)
    cite: str


# ---------------------------------------------------------------------------------------------------------------------
# address expressions

_TOK = re.compile(r"\s*(0x[0-9a-fA-F]+|\$[0-9a-fA-F]+|\d+|[A-Za-z_][A-Za-z0-9_]*\[|[A-Za-z_][A-Za-z0-9_]*|\[|\]|\+|-|\.)")


def _tokens(s):
    pos, out = 0, []
    s = s.rstrip()
    while pos < len(s):
        m = _TOK.match(s, pos)
        if not m:
            raise LayoutError(f"bad address expression {s!r} at {s[pos:]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


class _Expr:
    """Parsed once, evaluated per snapshot (and per slot for `.`)."""

    def __init__(self, src, symbols):
        self.src = str(src)
        self.symbols = symbols
        if isinstance(src, int):
            self.toks = [str(src)]
        else:
            self.toks = _tokens(src)
        self._i = 0
        self.tree = self._sum()
        if self._i != len(self.toks):
            raise LayoutError(f"trailing tokens in {self.src!r}")

    def _peek(self):
        return self.toks[self._i] if self._i < len(self.toks) else None

    def _take(self):
        t = self._peek()
        self._i += 1
        return t

    def _sum(self):
        terms = [(1, self._term())]
        while self._peek() in ("+", "-"):
            sign = 1 if self._take() == "+" else -1
            terms.append((sign, self._term()))
        return ("sum", terms)

    def _term(self):
        t = self._take()
        if t is None:
            raise LayoutError(f"unexpected end of {self.src!r}")
        if t in ("[", "w[", "b[", "l["):
            width = {"[": 4, "l[": 4, "w[": 2, "b[": 1}[t]
            inner = self._sum()
            if self._take() != "]":
                raise LayoutError(f"missing ] in {self.src!r}")
            return ("deref", width, inner)
        if t.endswith("["):
            raise LayoutError(f"unknown deref {t!r} in {self.src!r} (use [ ], w[ ], b[ ])")
        if t == ".":
            return ("dot",)
        if t.startswith("0x"):
            return ("num", int(t, 16))
        if t.startswith("$"):
            return ("num", int(t[1:], 16))
        if t.isdigit():
            return ("num", int(t))
        if t in self.symbols:
            return ("num", self.symbols[t])
        raise LayoutError(f"unknown symbol {t!r} in {self.src!r}")

    def eval(self, ram, dot=None):
        return _ev(self.tree, ram, dot) & 0xFFFFFFFF


def _ev(node, ram, dot):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "dot":
        if dot is None:
            raise LayoutError("`.` used outside a struct field")
        return dot
    if kind == "sum":
        return sum(sign * _ev(t, ram, dot) for sign, t in node[1])
    if kind == "deref":
        a = _ev(node[2], ram, dot) & 0xFFFFFF   # 24-bit bus: a pointer's top byte is ignored by the 68000
        w = node[1]
        if a + w > len(ram):
            raise _OffRam(a)
        return int.from_bytes(ram[a:a + w], "big")
    raise AssertionError(node)


class _OffRam(Exception):
    def __init__(self, addr):
        self.addr = addr


# ---------------------------------------------------------------------------------------------------------------------
# schema loading and validation

_FIELD_KEYS = {"off", "addr", "width", "signed", "fmt", "enum", "bits", "cite", "note"}


def _int(v, what):
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("$"):
            return int(s[1:], 16)
        return int(s, 0)
    raise LayoutError(f"{what}: expected a number, got {v!r}")


def _check_cite(entry, what, root, errors):
    c = entry.get("cite")
    if not c or not isinstance(c, str):
        errors.append(f"{what}: no `cite`")
        return
    path = c.split()[0]
    if not os.path.exists(os.path.join(root, path)):
        errors.append(f"{what}: cite names {path!r}, which does not exist under {root}")


def _field(spec, what, symbols, root, errors, struct_size=None):
    bad = set(spec) - _FIELD_KEYS
    if bad:
        errors.append(f"{what}: unknown keys {sorted(bad)}")
    _check_cite(spec, what, root, errors)
    width = spec.get("width", 1)
    if width not in (1, 2, 4):
        errors.append(f"{what}: width {width} (1, 2 or 4)")
    if ("off" in spec) == ("addr" in spec):
        errors.append(f"{what}: give exactly one of `off` (struct offset) or `addr` (expression)")
    f = dict(name=what.split(".")[-1], width=width, signed=bool(spec.get("signed", False)), fmt=spec.get("fmt", "dec"),
             cite=spec.get("cite", ""), note=spec.get("note", ""),
             enum={_int(k, what): v for k, v in spec.get("enum", {}).items()},
             bits={_int(k, what): v for k, v in spec.get("bits", {}).items()})
    try:
        if "off" in spec:
            off = _int(spec["off"], what)
            if struct_size is not None and off + width > struct_size:
                errors.append(f"{what}: off {off} + width {width} past the struct size {struct_size}")
            f["off"] = off
            f["expr"] = None
        else:
            f["off"] = None
            f["expr"] = _Expr(spec["addr"], symbols)
    except LayoutError as e:
        errors.append(f"{what}: {e}")
        f["off"], f["expr"] = 0, None
    if f["fmt"] not in ("dec", "hex"):
        errors.append(f"{what}: fmt {f['fmt']!r} (dec or hex)")
    return f


def load(path):
    """Parse and validate a layout.toml; raises LayoutError listing every problem."""
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)
    root = os.path.dirname(os.path.abspath(path))
    errors = []
    meta = doc.get("layout", {})
    symbols, symregs = {}, {}
    for name, spec in doc.get("symbols", {}).items():
        if isinstance(spec, dict):
            _check_cite(spec, f"symbols.{name}", root, errors)
            symbols[name] = _int(spec.get("value"), f"symbols.{name}")
            if "reg" in spec:
                symregs[name] = spec["reg"].lower()
        else:
            errors.append(f"symbols.{name}: write it as a table with value and cite")
    globals_ = []
    for name, spec in doc.get("globals", {}).items():
        f = _field(spec, name, symbols, root, errors)
        if f["off"] is not None:
            errors.append(f"globals.{name}: a global takes `addr`, not `off`")
        globals_.append(f)
    structs = {}
    for sname, spec in doc.get("structs", {}).items():
        _check_cite(spec, f"structs.{sname}", root, errors)
        size = _int(spec.get("size", 0), f"structs.{sname}.size")
        fields = [_field(fs, f"{sname}.{fname}", symbols, root, errors, size) for fname, fs in spec.get("fields", {}).items()]
        structs[sname] = dict(name=sname, size=size, fields=fields, cite=spec.get("cite", ""))
    arrays = []
    for aname, spec in doc.get("arrays", {}).items():
        what = f"arrays.{aname}"
        _check_cite(spec, what, root, errors)
        st = spec.get("struct")
        if st not in structs:
            errors.append(f"{what}: struct {st!r} is not defined")
            continue
        try:
            base = _Expr(spec["base"], symbols)
            count = _Expr(spec.get("count", 1), symbols)
        except (LayoutError, KeyError) as e:
            errors.append(f"{what}: {e}")
            continue
        stride = _int(spec.get("stride", structs[st]["size"]), f"{what}.stride")
        if stride < structs[st]["size"]:
            errors.append(f"{what}: stride {stride} below the struct size {structs[st]['size']}")
        arrays.append(dict(name=aname, struct=structs[st], base=base, stride=stride, count=count,
                           max=_int(spec.get("max", 4096), f"{what}.max"), first=_int(spec.get("first", 0), f"{what}.first"),
                           labels={_int(k, what): v for k, v in spec.get("labels", {}).items()}, cite=spec.get("cite", "")))
    regions = []
    for rname, spec in doc.get("regions", {}).items():
        _check_cite(spec, f"regions.{rname}", root, errors)
        try:
            regions.append(dict(name=rname, addr=_Expr(spec["addr"], symbols), len=_int(spec["len"], f"regions.{rname}.len"),
                                cite=spec.get("cite", "")))
        except (LayoutError, KeyError) as e:
            errors.append(f"regions.{rname}: {e}")
    if errors:
        raise LayoutError(f"{path}:\n  " + "\n  ".join(errors))
    return dict(path=path, root=root, meta=meta, symbols=symbols, symregs=symregs, globals=globals_, structs=structs,
                arrays=arrays, regions=regions)


# ---------------------------------------------------------------------------------------------------------------------
# decoding

def _render(f, raw):
    if raw is None:
        return "?"
    w = f["width"]
    v = raw
    if f["signed"] and raw & (1 << (8 * w - 1)):
        v = raw - (1 << (8 * w))
    if f["enum"]:
        name = f["enum"].get(raw)
        return f"{name}({v})" if name else str(v)
    if f["bits"]:
        on = [f["bits"][b] for b in sorted(f["bits"]) if raw >> b & 1]
        return f"${raw:0{2 * w}x}" + (f"[{'|'.join(on)}]" if on else "")
    if f["fmt"] == "hex":
        return f"${raw:0{2 * w}x}"
    return str(v)


def _read_field(f, ram, dot, name):
    try:
        a = f["expr"].eval(ram, dot) if f["expr"] is not None else dot + f["off"]
    except _OffRam:
        return Value(name, -1, f["width"], None, "?", f["cite"])
    a &= 0xFFFFFF
    if a + f["width"] > len(ram):
        return Value(name, -1, f["width"], None, "?", f["cite"])
    raw = int.from_bytes(ram[a:a + f["width"]], "big")
    return Value(name, a, f["width"], raw, _render(f, raw), f["cite"])


def array_slots(L, arr, ram, all_slots=False):
    """[(index, slot_address)] of an array in this RAM image; `count` bounds it unless all_slots (then `max`)."""
    try:
        base = arr["base"].eval(ram) & 0xFFFFFF
        n = arr["max"] if all_slots else min(arr["count"].eval(ram), arr["max"])
    except _OffRam:
        return []
    first = arr["first"]
    return [(i, base + arr["stride"] * i) for i in range(first, n) if base + arr["stride"] * (i + 1) <= len(ram)]


def slot_name(arr, i):
    lab = arr["labels"].get(i)
    return f"{arr['name']}[{i}:{lab}]" if lab else f"{arr['name']}[{i}]"


def decode(L, ram, only_array=None, all_slots=False):
    out = []
    if only_array is None:
        for f in L["globals"]:
            out.append(_read_field(f, ram, None, f["name"]))
    for arr in L["arrays"]:
        if only_array is not None and arr["name"] != only_array:
            continue
        for i, a in array_slots(L, arr, ram, all_slots):
            sn = slot_name(arr, i)
            for f in arr["struct"]["fields"]:
                out.append(_read_field(f, ram, a, f"{sn}.{f['name']}"))
    return out


def regions(L, ram):
    """[(name, addr, len, cite)] with each region's address evaluated in this RAM image."""
    res = []
    for r in L["regions"]:
        try:
            res.append((r["name"], r["addr"].eval(ram) & 0xFFFFFF, r["len"], r["cite"]))
        except _OffRam:
            pass
    return res


def check_symbols(L, snap):
    """Warnings for symbols tied to a register (`reg = "a5"`) whose value differs in this snapshot."""
    regs, ok = snapshot_regs(snap)
    warn = []
    if not ok:
        return warn
    for name, reg in L["symregs"].items():
        if reg in regs and regs[reg] != L["symbols"][name]:
            warn.append(f"{snap}: symbol {name} = ${L['symbols'][name]:x} but register {reg} = ${regs[reg]:x} "
                        f"(another build or a snapshot inside an interrupt?)")
    return warn


def decode_snap(L, snap, **kw):
    ram, _ = load_ram(snap)
    return decode(L, ram, **kw)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("layout")
    ap.add_argument("snap", nargs="?")
    ap.add_argument("--array", help="print only this array")
    ap.add_argument("--all-slots", action="store_true", help="decode every slot up to `max`, not only up to `count`")
    ap.add_argument("--cite", action="store_true", help="print each value's citation")
    ap.add_argument("--check", action="store_true", help="validate the schema only")
    a = ap.parse_args(argv)
    try:
        L = load(a.layout)
    except LayoutError as e:
        sys.exit(str(e))
    if a.check or not a.snap:
        n = len(L["globals"]) + sum(len(s["fields"]) for s in L["structs"].values())
        print(f"{a.layout}: ok ({len(L['globals'])} globals, {len(L['arrays'])} arrays, {n} fields with citations, "
              f"{len(L['regions'])} regions)")
        return
    for w in check_symbols(L, a.snap):
        print("warning:", w, file=sys.stderr)
    for v in decode_snap(L, a.snap, only_array=a.array, all_slots=a.all_slots):
        loc = f"${v.addr:06x}" if v.addr >= 0 else "  (off RAM)"
        print(f"{loc}  {v.name:<34} {v.text}" + (f"    [{v.cite}]" if a.cite else ""))


if __name__ == "__main__":
    main()
