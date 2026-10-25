"""Index every hex address and N(An) field offset the game docs mention, and cross-check them against the .sym.

    uv run python tools/doc_addrs.py --addr 1abaa [--game powermonger] [-C 2]   every mention of one address, all games
    uv run python tools/doc_addrs.py --field "44(A5)" [--game cadaver]       every mention of one field (or --field 44: any An)
    uv run python tools/doc_addrs.py --check powermonger [--range LO HI] [--near N] [--top N]

Scans `reversing/<game>/**/*.md` (never `scratchpad/`). An address is `$hex` or `0xhex`; one written as an
immediate (`#$100`) is listed by --addr but ignored by --check. A field is `disp(An)`, `$disp(An)` or
`disp(An,Dn.w)`; `$2c(A0)` and `44(A0)` are the same field.

--addr / --field is the check CLAUDE.md "Docs" asks for after a correction lands: list every copy of the routine's
address (or the field) across all games' docs, so the old wording is fixed everywhere in the same edit.

--check <game> reads every `.sym` under the game's directory and reports, for addresses inside the .sym's own range
(min..max symbol address, or --range):
  near    an address within --near bytes (default 6) of a symbol but not on it: a typo or a stale entry point (the
          `$fec6` -> `$fecc` kind of fix), or a legitimate label just inside a routine; read each one
  pairs   a doc that pairs an address with a backticked name (`` `$A` (`name`) ``, `` `name` (`$A`) ``,
          `` `name` `$A` ``) where the name is a .sym name for a different address, or the address has .sym names and
          the name is not one of them but carries a .sym naming prefix; a name paired with an address inside its own
          routine is tagged `inside` (usually a call site, sometimes the wrong name)
  stale   backticked names with a .sym naming prefix (`pm_`, `g_`: any shared by 25+ names of one .sym, or --prefix)
          that no .sym line (comments included) holds and no doc declares as a C struct: renamed or never added
  unnamed the addresses the docs mention most that have no .sym entry (--top, default 25): candidates for the .sym
The check is a review list, not a verdict: each line carries file:line and the sentence, settle it in the code.
Exit status 0 always (it reports, it does not gate).
"""
import argparse
import bisect
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
REV = ROOT / "reversing"

HEX = re.compile(r"(?<![\w$])(#?)(?:\$|0x)([0-9a-fA-F]+)\b")
FIELD = re.compile(r"(?<![\w$])(-?)(\$|0x)?([0-9a-fA-F]+)\(([aA][0-7]|[sS][pP])[,)]")
NAME = r"`([A-Za-z_][A-Za-z0-9_]*)`"
ADDR = r"`?(?:\$|0x)([0-9a-fA-F]{3,8})`?"
PAIRS = [re.compile(ADDR + r"\s*\(" + NAME + r"\)"),          # `$A` (`name`)
         re.compile(NAME + r"\s*\(" + ADDR + r"\)", ),         # `name` (`$A`)
         re.compile(NAME + r"\s+" + ADDR)]                     # `name` `$A`
ENTRY_CTX = re.compile(r"(?i)\b(callcap|bsr|jsr|jmp|bpc|bp|hits|u|routine|calls?|called|entry|entered|gate of|handler)\b[^$\n]{0,14}`?$")
SENT_SPLIT = re.compile(r"(?<=[.;?!])\s+(?=[A-Z`(\[*])|\s\|\s|^\|\s*|\s*\|$")


def doc_files(game=None):
    games = [REV / game] if game else sorted(p for p in REV.iterdir() if p.is_dir())
    for g in games:
        for f in sorted(g.rglob("*.md")):
            if "scratchpad" not in f.parts:
                yield g.name, f


def sentence(line, start, end, width=240):
    """The sentence (or table cell) of `line` holding [start, end), trimmed to about `width` chars."""
    lo, hi = 0, len(line)
    for m in SENT_SPLIT.finditer(line):
        if m.end() <= start:
            lo = m.end()
        elif m.start() >= end:
            hi = m.start()
            break
    s = line[lo:hi].strip()
    if len(s) > width:
        c = start - lo
        a = max(0, c - width // 2)
        s = ("..." if a else "") + s[a:a + width] + ("..." if a + width < len(s) else "")
    return s


LINES = {}


def context(f, n, k):
    """Lines n-k..n+k of f (1-based), indented, for -C."""
    ls = LINES[f]
    return "\n".join(f"    {i}: {ls[i - 1]}" for i in range(max(1, n - k), min(len(ls), n + k) + 1))


def scan(game=None):
    """Yield (game, path, lineno, line, kind, value, match) for every hex address and field mention."""
    for g, f in doc_files(game):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        LINES[f] = text.splitlines()
        for n, line in enumerate(LINES[f], 1):
            for m in HEX.finditer(line):
                yield g, f, n, line, "imm" if m.group(1) else "addr", int(m.group(2), 16), m
            for m in FIELD.finditer(line):
                disp = int(m.group(3), 16) if m.group(2) else (int(m.group(3)) if m.group(3).isdigit() else None)
                if disp is None:
                    continue
                if m.group(1):
                    disp = -disp
                reg = m.group(4).upper().replace("SP", "A7")
                yield g, f, n, line, "field", (disp, reg), m


def load_syms(game, per_file=False):
    by_addr, by_name, file_names = defaultdict(set), defaultdict(set), defaultdict(list)
    files = sorted((REV / game).rglob("*.sym"))
    for f in files:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.split("#", 1)[0].split()
            if len(s) < 2:
                continue
            try:
                a = int(s[0].lstrip("$"), 16)
            except ValueError:
                continue
            by_addr[a].add(s[1])
            by_name[s[1]].add(a)
            file_names[f].append(s[1])
    return file_names if per_file else (files, by_addr, by_name)


def rel(p):
    return p.relative_to(REV)


def parse_addr(s):
    s = s.strip().lower()
    for p in ("$", "0x"):
        if s.startswith(p):
            s = s[len(p):]
    return int(s, 16)


def cmd_addr(args):
    want = parse_addr(args.addr)
    games = [args.game] if args.game else sorted(p.name for p in REV.iterdir() if p.is_dir())
    for g in games:
        _, by_addr, _ = load_syms(g)
        if want in by_addr:
            print(f"{g}.sym: ${want:x} = {', '.join(sorted(by_addr[want]))}")
    hits = 0
    for g, f, n, line, kind, v, m in scan(args.game):
        if kind in ("addr", "imm") and v == want:
            hits += 1
            tag = " [imm]" if kind == "imm" else ""
            print(f"{rel(f)}:{n}{tag}: {sentence(line, m.start(), m.end())}")
            if args.C:
                print(context(f, n, args.C))
    print(f"-- {hits} mentions of ${want:x}", file=sys.stderr)


def cmd_field(args):
    m = re.fullmatch(r"\s*(-?)(\$|0x)?([0-9a-fA-F]+)\s*(?:\(\s*([aA][0-7]|[sS][pP])\s*\))?\s*", args.field)
    if not m:
        sys.exit(f"bad --field {args.field!r}: want 44(A5), $2c(A0) or 44")
    disp = int(m.group(3), 16) if m.group(2) else int(m.group(3))
    disp = -disp if m.group(1) else disp
    reg = m.group(4).upper().replace("SP", "A7") if m.group(4) else None
    hits = 0
    for g, f, n, line, kind, v, mm in scan(args.game):
        if kind == "field" and v[0] == disp and (reg is None or v[1] == reg):
            hits += 1
            print(f"{rel(f)}:{n}: {sentence(line, mm.start(), mm.end())}")
            if args.C:
                print(context(f, n, args.C))
    print(f"-- {hits} mentions of {disp}({reg or 'An'})", file=sys.stderr)


def cmd_check(args):
    game = args.check
    if not (REV / game).is_dir():
        sys.exit(f"no reversing/{game}/")
    files, by_addr, by_name = load_syms(game)
    file_names = load_syms(game, per_file=True)
    if not files:
        sys.exit(f"reversing/{game}/ has no .sym")
    lo, hi = (parse_addr(args.range[0]), parse_addr(args.range[1])) if args.range else (min(by_addr), max(by_addr))
    addrs = sorted(by_addr)
    if args.prefix is not None:
        prefixes = tuple(x for x in args.prefix.split(",") if x)
    else:      # every naming prefix that 25+ names of one .sym share (`pm_`, `g_`); none: no stale-name report
        prefixes = set()
        for names in file_names.values():
            c = Counter(n.split("_", 1)[0] + "_" for n in names if not n.startswith("_") and "_" in n)
            prefixes |= {p for p, k in c.items() if k >= 25}
        prefixes = tuple(sorted(prefixes))

    def next_sym(x):
        i = bisect.bisect_right(addrs, x)
        return addrs[i] if i < len(addrs) else hi + 1
    print(f"# {game}: {len(by_addr)} symbol addresses from {', '.join(str(rel(f)) for f in files)}; "
          f"range ${lo:x}..${hi:x}; prefixes {', '.join(prefixes) or '(none)'}")

    near, unnamed, pairs, stale = [], defaultdict(list), [], defaultdict(list)
    seen_lines = set()
    for g, f, n, line, kind, v, m in scan(game):
        if kind == "addr" and lo <= v <= hi and v not in by_addr:
            i = bisect.bisect_left(addrs, v)
            cands = [a for a in addrs[max(0, i - 1):i + 1] if abs(a - v) <= args.near]
            if cands and ENTRY_CTX.search(line[max(0, m.start() - 28):m.start()]):
                a = min(cands, key=lambda a: abs(a - v))
                near.append((v, a, f, n, sentence(line, m.start(), m.end())))
            else:
                unnamed[v].append((f, n))
        if (f, n) in seen_lines:
            continue
        seen_lines.add((f, n))
        for rx in PAIRS:
            for pm in rx.finditer(line):
                a_s, name = (pm.group(1), pm.group(2)) if rx is PAIRS[0] else (pm.group(2), pm.group(1))
                a = int(a_s, 16)
                if name in by_name and a not in by_name[name]:
                    where = ", ".join(f"${x:x}" for x in sorted(by_name[name]))
                    inside = [x for x in by_name[name] if x < a < next_sym(x)]
                    tag = (f"inside `{name}` ${inside[0]:x}..${next_sym(inside[0]):x} (a site, or the wrong name?)" if inside
                           else "CONTRADICTS")
                    pairs.append((f, n, f"{tag}: `{name}` is {where} in the .sym, paired here with ${a:x}"
                                        + (f" (= {', '.join(sorted(by_addr[a]))})" if a in by_addr else ""),
                                  sentence(line, pm.start(), pm.end())))
                elif a in by_addr and name not in by_addr[a] and prefixes and name.startswith(prefixes):
                    pairs.append((f, n, f"CONTRADICTS: ${a:x} is {', '.join(sorted(by_addr[a]))} in the .sym, named `{name}` here",
                                  sentence(line, pm.start(), pm.end())))
        if prefixes:
            for nm in re.finditer(r"`((?:" + "|".join(map(re.escape, prefixes)) + r")[A-Za-z0-9_]+)`", line):
                if nm.group(1) not in by_name:
                    stale[nm.group(1)].append((f, n, sentence(line, nm.start(), nm.end())))

    print(f"\n## near: {len(near)} entry-like mentions (after callcap/bsr/jsr/bp/hits/routine/entry...) within "
          f"{args.near} bytes of a symbol but not on it")
    for v, a, f, n, s in sorted(near, key=lambda t: (t[0], str(t[2]), t[3])):
        print(f"${v:x} ({'+' if v > a else '-'}{abs(v - a)} from ${a:x} {','.join(sorted(by_addr[a]))})  "
              f"{rel(f)}:{n}: {s}")
    print(f"\n## pairs: {len(pairs)} address/name pairings that disagree with the .sym")
    for f, n, what, s in pairs:
        print(f"{rel(f)}:{n}: {what}\n    {s}")
    # a name the .sym comments use (struct names such as `pm_leader`) or a doc declares as a C type is not stale
    sym_text = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files)
    doc_text = "\n".join(f.read_text(encoding="utf-8", errors="replace") for _, f in doc_files(game))
    declared = set(re.findall(r"typedef\s+struct\s+(\w+)|^\}\s*(\w+)\s*;", doc_text, re.M))
    declared = {x for pair in declared for x in pair if x}
    stale = {k: v for k, v in stale.items() if not re.search(r"\b" + re.escape(k) + r"\b", sym_text) and k not in declared}
    print(f"\n## stale: {len(stale)} names with a .sym prefix ({', '.join(prefixes)}) that no .sym holds")
    for nm, locs in sorted(stale.items()):
        f, n, s = locs[0]
        more = f" (+{len(locs) - 1} more)" if len(locs) > 1 else ""
        print(f"`{nm}`  {rel(f)}:{n}{more}: {s}")
    top = sorted(unnamed.items(), key=lambda kv: -len(kv[1]))[:args.top]
    print(f"\n## unnamed: {len(unnamed)} in-range addresses with no .sym entry; the {len(top)} most mentioned")
    for v, locs in top:
        docs = Counter(str(rel(f)) for f, _ in locs)
        print(f"${v:x}  {len(locs)}x  " + ", ".join(f"{d}:{c}" for d, c in docs.most_common(4)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--addr", help="hex address ($1abaa, 0x1abaa or 1abaa)")
    mode.add_argument("--field", help="field offset: 44(A5), $2c(A0), or 44 for any An")
    mode.add_argument("--check", metavar="GAME", help="cross-check a game's docs against its .sym")
    ap.add_argument("--game", help="restrict --addr/--field to one game")
    ap.add_argument("-C", type=int, default=0, metavar="N", help="--addr/--field: also print N lines either side")
    ap.add_argument("--range", nargs=2, metavar=("LO", "HI"), help="--check: address range (default: the .sym's)")
    ap.add_argument("--near", type=lambda s: int(s, 0), default=6, help="--check: near-miss distance in bytes (6)")
    ap.add_argument("--prefix", help="--check: comma list of .sym name prefixes for the stale report (default: auto)")
    ap.add_argument("--top", type=int, default=25, help="--check: unnamed addresses to list (25)")
    args = ap.parse_args()
    if args.addr:
        cmd_addr(args)
    elif args.field:
        cmd_field(args)
    else:
        cmd_check(args)


if __name__ == "__main__":
    main()
