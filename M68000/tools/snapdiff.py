"""snapdiff.py <layout.toml> <a.snap> <b.snap> [--gap N] [--max-ranges N] [--regs]: named snapshot diff.

Prints, through a game's memory schema (`tools/layout.py`, DEVELOPING.md "Memory layouts and the semantic snapshot
diff"):
  1. every named field whose value differs, as `name a -> b` (array slots present in only one snapshot say so);
  2. each named region (`[regions]`, e.g. a display buffer) with its changed byte count;
  3. the changed RAM bytes that no field or region covers, merged into ranges (runs closer than --gap bytes join)
     with each range's changed byte count, largest first beyond --max-ranges.
A field counts as covering its bytes at the address it decodes to in either snapshot. A zero-change result also
prints the total changed byte count, so "nothing named changed" is told apart from "nothing changed".
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402
from gfxview import load_ram, snapshot_regs  # noqa: E402


def changed_runs(a, b, lo=0, hi=None):
    """[(start, end_exclusive)] of maximal runs of differing bytes."""
    hi = min(len(a), len(b)) if hi is None else hi
    runs, i = [], lo
    # compare in 4 KB blocks first: most of RAM is identical
    blk = 4096
    while i < hi:
        j = min(i + blk, hi)
        if a[i:j] == b[i:j]:
            i = j
            continue
        k = i
        while k < j:
            if a[k] != b[k]:
                s = k
                while k < hi and a[k] != b[k]:
                    k += 1
                if runs and runs[-1][1] == s:
                    runs[-1] = (runs[-1][0], k)
                else:
                    runs.append((s, k))
            else:
                k += 1
        i = max(j, k)
    return runs


def subtract(runs, covered):
    """Split runs into bytes not in the covered set."""
    out = []
    for s, e in runs:
        cur = None
        for x in range(s, e):
            if x in covered:
                if cur is not None:
                    out.append((cur, x))
                    cur = None
            elif cur is None:
                cur = x
        if cur is not None:
            out.append((cur, e))
    return out


def merge(runs, gap):
    """Join runs separated by fewer than `gap` unchanged bytes; returns [(start, end, changed_bytes)]."""
    out = []
    for s, e in runs:
        if out and s - out[-1][1] < gap:
            ps, pe, n = out[-1]
            out[-1] = (ps, e, n + e - s)
        else:
            out.append((s, e, e - s))
    return out


def diff(L, snap_a, snap_b, gap=16, max_ranges=40, show_regs=False, out=sys.stdout):
    ram_a, _ = load_ram(snap_a)
    ram_b, _ = load_ram(snap_b)
    for w in layout.check_symbols(L, snap_a) + layout.check_symbols(L, snap_b):
        print("warning:", w, file=out)
    va = layout.decode(L, ram_a)
    vb = layout.decode(L, ram_b)
    da = {v.name: v for v in va}
    db = {v.name: v for v in vb}
    names = list(da) + [n for n in db if n not in da]
    covered = set()
    for v in va + vb:
        if v.addr >= 0:
            covered.update(range(v.addr, v.addr + v.width))

    print(f"== named fields ({os.path.basename(snap_a)} -> {os.path.basename(snap_b)})", file=out)
    nchg = 0
    only = {}
    for n in names:
        x, y = da.get(n), db.get(n)
        if x is None or y is None:
            slot = n.rsplit(".", 1)[0]
            only.setdefault(slot, "b only" if x is None else "a only")
            continue
        if x.raw != y.raw:
            nchg += 1
            print(f"  {n:<36} {x.text} -> {y.text}", file=out)
    for slot, side in only.items():
        print(f"  {slot:<36} present in {side[0]} only (count changed)", file=out)
    if nchg == 0 and not only:
        print("  (no named field changed)", file=out)

    runs = changed_runs(ram_a, ram_b)
    total = sum(e - s for s, e in runs)
    regs_a = layout.regions(L, ram_a)
    if regs_a:
        print("== named regions", file=out)
        for name, addr, ln, _c in regs_a:
            n = sum(max(0, min(e, addr + ln) - max(s, addr)) for s, e in runs)
            print(f"  {name:<36} ${addr:06x}+{ln}: {n} bytes changed", file=out)
            covered.update(range(addr, addr + ln))
    rest = merge(subtract(runs, covered), gap)
    nrest = sum(n for _s, _e, n in rest)
    print(f"== raw changes outside the schema: {nrest} bytes in {len(rest)} ranges (gap {gap}); "
          f"{total} bytes changed in all", file=out)
    shown = rest if len(rest) <= max_ranges else sorted(sorted(rest, key=lambda r: -r[2])[:max_ranges])
    for s, e, n in shown:
        print(f"  ${s:06x}-${e - 1:06x}  {e - s:6d} span  {n:6d} changed", file=out)
    if len(shown) < len(rest):
        print(f"  ... {len(rest) - len(shown)} smaller ranges not shown "
              f"({nrest - sum(n for _s, _e, n in shown)} bytes)", file=out)
    if show_regs:
        ra, _ = snapshot_regs(snap_a)
        rb, _ = snapshot_regs(snap_b)
        ch = [f"{k} ${ra[k]:x} -> ${rb[k]:x}" for k in ra if ra[k] != rb.get(k)]
        print("== registers: " + (", ".join(ch) if ch else "unchanged"), file=out)
    return nchg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("layout")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--gap", type=int, default=16, help="join raw runs closer than this many bytes (default 16)")
    ap.add_argument("--max-ranges", type=int, default=40, help="list at most this many raw ranges, largest first")
    ap.add_argument("--regs", action="store_true", help="also print changed CPU registers")
    a = ap.parse_args(argv)
    try:
        L = layout.load(a.layout)
    except layout.LayoutError as e:
        sys.exit(str(e))
    diff(L, a.a, a.b, a.gap, a.max_ranges, a.regs)


if __name__ == "__main__":
    main()
