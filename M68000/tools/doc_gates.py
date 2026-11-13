"""List the match counts the game docs record and which of them a promoted gate (`tools/gates.py`) re-checks.

    uv run python tools/doc_gates.py [<game>|all] [--list [CLASS]] [--manifest-dir DIR]

Scans `reversing/<game>/**/*.md` (never `scratchpad/`) for match counts, attributes each to the script the text
around it names, and classifies it against `reversing/<game>/gates.toml`:

  GATED             the attributed script, or any script the same table row or paragraph names, is run by a gate
                    whose `expect` holds the count (a gate's `.sh` passes its counts to the scripts it runs); or no
                    script resolves and a gate expects the count and either cites this doc or the count is >= 100
                    (tagged `count-only`)
  SCRIPTED-UNGATED  the attributed script exists in the tree but no gate expects this count from it (tagged
                    `gated-script` when a gate runs the script with other counts, e.g. another argument set)
  ORPHAN            no script attributed, or the attributed script does not exist in the tree

A count is `a/b` or `a / b` (thousands separators allowed) or `a of b`, with 1 <= b and a <= b. Equal counts are kept
unless they sit in a list of index pairs (a sentence that also holds an `a/b` with a > b or b == 0, for b < 10);
an unequal or spaced one only when a match word (match, identical, exact, agree, equal, pass, ...) is within 80
chars in its sentence (or an equal one is in bold), since unequal slashes are mostly sprite ranges, bit pairs, zoom
indices and fractions. Excluded: chains (`12 / 8 / 16`, dates), slashes touching letters, `$`, `.` or `(`
(`MPR5/6`, `22/24(A6)`, `1.0/2.0`), and `N of M` after a bit/byte/entry-style noun. Attribution takes a
backticked or bare `*.py`/`*.sh`/`*.fsx` path: one written right next to the count in its sentence (before it
within 40 chars, else after it within 60, no other count between), else the first cell of a script table row, else
the nearest in the sentence, else in the table row, else the last one named earlier in the paragraph or list item.
A script resolves by its path relative to the doc, the game dir, `M68000/`, or a suffix match among the game's,
`tools/`' and `server/`'s scripts.

The tool is a review list, not a verdict: a count next to a script is attributed to it whether or not that script
printed it. On a seeded 40-item hand-check (drawn after tuning on a different 40) the class was right for 36; the
misses were a count attributed to the script that closes the previous clause, a coincidental small count in a row
that names a gate script, and two gated counts restated in a README with no script named (ORPHAN where GATED).
Expect a few per cent of items to be pixel sizes or live-observation tallies rather than script output.
--manifest-dir DIR reads `DIR/<game>/gates.toml` instead of the real manifests (the negative-control hook).
Exit status 0 (1 for an unknown game): it reports, it does not gate.
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import tomllib
except ImportError:
    sys.exit("doc_gates.py needs Python 3.11+ (tomllib); run it with `uv run python`")

ROOT = next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
REV = ROOT / "reversing"

NUM = r"(\d{1,3}(?:,\d{3})+|\d+)"
SLASH = re.compile(r"(?<![\w.$/(`-])" + NUM + r"(\s?)/(\s?)" + NUM + r"(?![\w./(]|\s?/\s?\d|`\w)")
OF = re.compile(r"(?<![\w.$/-])" + NUM + r" of " + NUM + r"(?![\w./(]|\s?/\s?\d)")
OF_NOUN = re.compile(r"(?i)\b(bits?|bytes?|words?|longs?|entry|entries|slot|index|level|frame|page|disk|side|track|"
                     r"sector|part|chapter|section|step|row|column|plane|layer|nibble|line|field|offset|item|"
                     r"number|no\.|land|round|stage|phase|move|wave|byte6)\s*$")
MATCHW = re.compile(r"(?i)\b(match\w*|identical|exact\w*|agree\w*|equal\w*|correct\w*|pass\w*|same|reproduc\w*|"
                    r"mismatch\w*|wrong|differ\w*|gate|compar\w*|check\w*|verified|consistent|confirm\w*)\b")
SCRIPT = re.compile(r"(?<![\w/.-])((?:\.\./|\./)*[\w][\w./-]*\.(?:py|sh|fsx))(?![\w])")
SENT_SPLIT = re.compile(r"(?<=[.;?!])\s+(?=[A-Z`(\[*])|\s\|\s|^\|\s*|\s*\|$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def canon(a, b):
    return f"{a.replace(',', '')}/{b.replace(',', '')}"


def doc_files(game):
    for f in sorted((REV / game).rglob("*.md")):
        if "scratchpad" not in f.relative_to(ROOT).parts:
            yield f


def script_index(game):
    """Every .py/.sh/.fsx a doc of `game` can name: the game's own, tools/ and server/ (scratchpad excluded)."""
    out = []
    for base in (REV / game, ROOT / "tools", ROOT / "server"):
        if base.exists():
            for ext in ("py", "sh", "fsx"):
                out += [p.resolve() for p in base.rglob(f"*.{ext}")
                        if "scratchpad" not in p.parts and ".venv" not in p.parts and "bin" not in p.parts
                        and "obj" not in p.parts]
    by_name = defaultdict(list)
    for p in out:
        by_name[p.name].append(p)
    return by_name


def resolve(name, doc, game, idx):
    """The script files `name` (as written in `doc`) can mean; [] when none exists."""
    for base in (doc.parent, REV / game, REV / game / "py", ROOT):
        p = (base / name)
        if p.is_file():
            return [p.resolve()]
    cands = idx.get(Path(name).name, [])
    tail = Path(name).parts
    hits = [c for c in cands if c.parts[-len(tail):] == tail]
    if hits:
        return hits if len(hits) == 1 else hits     # ambiguous: every candidate
    return cands if "/" not in name else []


def shell_children(sh, idx):
    """The scripts a gate's shell script runs (`$py "$here/x.py"`), resolved beside it or by unique basename."""
    out = []
    try:
        text = sh.read_text(errors="replace")
    except OSError:
        return out
    for m in SCRIPT.finditer(text):
        name = Path(m.group(1)).name
        p = sh.parent / name
        if p.is_file():
            out.append(p.resolve())
        elif len(idx.get(name, [])) == 1:
            out.append(idx[name][0])
    return out


def manifest(game, mdir, idx):
    """{resolved script path: set of expected counts} (a gate's shell script passes its counts to the scripts it
    runs), every count any gate expects, and {count: cited doc paths} for the gates expecting it."""
    f = (mdir / game / "gates.toml") if mdir else (REV / game / "gates.toml")
    by_script, allc, cited = defaultdict(set), set(), defaultdict(set)
    if not f.exists():
        return by_script, allc, cited, False
    for g in tomllib.loads(f.read_text())["gate"]:
        cwd = REV / game / g["cwd"] if "cwd" in g else ROOT
        want = set()
        for e in g["expect"]:
            if e.startswith("re:"):
                nums = re.findall(r"\d+", e[3:])
                # an `re:` entry gates the counts whose both sides it spells out (`700 ... 700`, `268, ... 268`)
                want |= {f"{a}/{b}" for a in nums for b in nums if int(a) <= int(b)}
            else:
                want |= {canon(a, b) for a, _, _, b in SLASH.findall(e)}
        allc |= want
        for c in want:
            cited[c] |= set(re.findall(r"[\w./-]+\.md", g.get("cite", "")))
        for tok in g["cmd"].split():
            if re.search(r"\.(py|sh|fsx)$", tok):
                p = (cwd / tok).resolve()
                by_script[p] |= want
                if p.suffix == ".sh":
                    for q in shell_children(p, idx):
                        by_script[q] |= want
    return by_script, allc, cited, True


def blocks(lines):
    """Paragraph / list-item id of each line (0-based), and whether it is a table row."""
    pid, out, cur = 0, [], None
    for l in lines:
        s = l.strip()
        table = s.startswith("|")
        if not s or s.startswith("#") or s.startswith("```"):
            pid += 1
            out.append((pid, table))
            pid += 1
            continue
        if table or LIST_ITEM.match(l) or cur == "table":
            pid += 1
        cur = "table" if table else "text"
        out.append((pid, table))
    return out


def sentence_span(line, start, end):
    lo, hi = 0, len(line)
    for m in SENT_SPLIT.finditer(line):
        if m.end() <= start:
            lo = m.end()
        elif m.start() >= end:
            hi = m.start()
            break
    return lo, hi


def counts_in(line):
    """(start, end, canonical count, a==b) for every match count on the line, by the rules in the docstring."""
    found = []
    for m in SLASH.finditer(line):
        a, s1, s2, b = m.groups()
        found.append((m.start(), m.end(), a, b, bool(s1 or s2)))
    for m in OF.finditer(line):
        if OF_NOUN.search(line[:m.start()]):
            continue
        found.append((m.start(), m.end(), m.group(1), m.group(2), False))
    # a sentence holding a/b with a > b or b == 0 is a list of index pairs (`0/2 $7076e; 2/0 $709f2; 2/2 ...`)
    pairs = [m.start() for m in SLASH.finditer(line)
             if int(m.group(4).replace(",", "")) == 0 or int(m.group(1).replace(",", "")) > int(m.group(4).replace(",", ""))]
    out = []
    for s, e, a, b, spaced in found:
        ia, ib = int(a.replace(",", "")), int(b.replace(",", ""))
        if ib == 0 or ia > ib:
            continue
        lo, hi = sentence_span(line, s, e)
        if ib < 10 and any(lo <= p < hi for p in pairs):
            continue
        if ia != ib or spaced:
            lo, hi = sentence_span(line, s, e)
            near = line[max(lo, s - 80):min(hi, e + 80)]
            if not MATCHW.search(near) and not (ia == ib and line[max(0, s - 2):s] == "**"):
                continue
        out.append((s, e, canon(a, b), ia == ib))
    return out


def scripts_in(text, offset=0):
    return [(m.start() + offset, m.end() + offset, m.group(1)) for m in SCRIPT.finditer(text)]


def adjacent(cands, s, e, spans, line):
    """A script written right next to the count: just before it (`x.py` 12/12, gap <= 40 chars) or just after it
    (12/12 (`x.py`), gap <= 60), with no other count in the gap; the before side wins."""
    clear = lambda lo, hi: not any(lo <= a and b <= hi for a, b in spans if (a, b) != (s, e))
    # `x.py`); claim 12/12: a `)` or `;` after the script closes its clause
    before = [c for c in cands if c[1] <= s and s - c[1] <= 40 and clear(c[1], s)
              and not re.search(r"[;)]", line[c[1]:s])]
    if before:
        return max(before, key=lambda c: c[1])
    after = [c for c in cands if c[0] >= e and c[0] - e <= 60 and clear(e, c[0])]
    return min(after, key=lambda c: c[0]) if after else None


def pick(cands, s, e, spans, line):
    """Script for the count at [s, e): an adjacent one, else the nearest before it, else the nearest after it."""
    hit = adjacent(cands, s, e, spans, line)
    if hit:
        return hit
    before = [c for c in cands if c[1] <= s]
    if before:
        return max(before, key=lambda c: c[1])
    after = [c for c in cands if c[0] >= e]
    return min(after, key=lambda c: c[0]) if after else None


def scan(game, mdir):
    idx = script_index(game)
    by_script, allc, cited, has_manifest = manifest(game, mdir, idx)
    items = []
    for f in doc_files(game):
        lines = f.read_text(errors="replace").splitlines()
        bl = blocks(lines)
        # pre[i]: the scripts named in line i's paragraph on earlier lines (text paragraphs only)
        pre, run, last = [], [], None
        for i, (pid, table) in enumerate(bl):
            if pid != last:
                run = []
            pre.append(list(run))
            if not table:
                run = run + [n for _, _, n in scripts_in(lines[i])]
            last = pid
        for i, line in enumerate(lines):
            cs = counts_in(line)
            if not cs:
                continue
            row_scripts = scripts_in(line)
            spans = [(s, e) for s, e, _, _ in cs]
            is_row = bl[i][1]
            # a script table (`| `x.py args` | what it proves |`): the first cell names the script the row is about
            cells = line.split("|")
            first = scripts_in(cells[1], len(cells[0]) + 1) if is_row and len(cells) > 2 else []
            for s, e, c, eq in cs:
                src, where = None, None
                lo, hi = sentence_span(line, s, e)
                sent = [x for x in row_scripts if x[0] >= lo and x[1] <= hi]
                adj = adjacent(sent, s, e, spans, line) if sent else None
                if adj:
                    src, where = adj, "sentence"
                elif first and s > first[0][1]:
                    src, where = first[0], "first cell"
                elif sent:
                    src, where = pick(sent, s, e, spans, line), "sentence"
                elif is_row and row_scripts:
                    src, where = pick(row_scripts, s, e, spans, line), "row"
                elif not is_row and (pre[i] or any(x[1] <= s for x in row_scripts)):
                    # a paragraph's script counts only when written before the count (a later one is usually
                    # another claim's)
                    same = [x[2] for x in row_scripts if x[1] <= s]
                    src, where = (0, 0, (pre[i] + same)[-1]), "paragraph"
                name = src[2] if src else None
                paths = resolve(name, f, game, idx) if name else []
                # every script the row or the paragraph names: a gate script expecting this count among them gates it
                scope = row_scripts if is_row else [(0, 0, n) for n in pre[i]] + row_scripts
                scope_paths = [p for _, _, n in scope for p in resolve(n, f, game, idx)]
                rel = str(f.relative_to(REV / game))
                if paths and any(c in by_script.get(p, ()) for p in paths):
                    cls, why = "GATED", "script+count"
                elif any(c in by_script.get(p, ()) for p in scope_paths):
                    cls, why = "GATED", "gate script in scope"
                elif paths and any(p in by_script for p in paths):
                    cls, why = "SCRIPTED-UNGATED", "gated-script"
                elif paths:
                    cls, why = "SCRIPTED-UNGATED", "no gate"
                elif c in allc and (rel in cited[c] or int(c.split("/")[1]) >= 100
                                    or cited[c] & set(re.findall(r"[\w./-]+\.md", line))):
                    # a small count (4/4) in a doc no expecting gate cites is a coincidence more often than not;
                    # a README index row that names the cited doc (`| `ai.md` | ... 3/3 |`) is the same claim
                    cls, why = "GATED", "count-only"
                elif name:
                    cls, why = "ORPHAN", "script missing"
                else:
                    cls, why = "ORPHAN", "no script"
                items.append(dict(game=game, file=str(f.relative_to(ROOT)), line=i + 1, count=c, equal=eq,
                                  script=name, where=where, cls=cls, why=why,
                                  text=line[max(0, s - 90):e + 60].strip()))
    return items, has_manifest


CLASSES = ["GATED", "SCRIPTED-UNGATED", "ORPHAN"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("game", nargs="?", default="all", help="a reversing/<game> dir, or all")
    ap.add_argument("--list", nargs="?", const="all", metavar="CLASS",
                    help="list every item (or only GATED / SCRIPTED-UNGATED / ORPHAN) with file:line")
    ap.add_argument("--manifest-dir", type=Path, help="read DIR/<game>/gates.toml instead of the real manifests")
    a = ap.parse_args()
    games = sorted(p.name for p in REV.iterdir() if p.is_dir()) if a.game == "all" else [a.game]
    if a.game != "all" and not (REV / a.game).is_dir():
        sys.exit(f"no {REV / a.game}")
    rows, everything = [], []
    for g in games:
        items, has = scan(g, a.manifest_dir)
        everything += items
        n = Counter(x["cls"] for x in items)
        d = {k: len({x["count"] for x in items if x["cls"] == k}) for k in CLASSES}
        rows.append((g, has, n, d, sum(x["equal"] for x in items), len(items)))
    print(f"{'game':16} {'manifest':8} " + " ".join(f"{k:>16}" for k in CLASSES) + f" {'total':>6} {'a==b':>5}")
    tot = Counter()
    for g, has, n, d, eq, t in rows:
        if not t:
            continue
        print(f"{g:16} {'yes' if has else '-':8} " + " ".join(f"{n[k]:>9} ({d[k]:>4})" for k in CLASSES)
              + f" {t:>6} {eq:>5}")
        tot.update(n)
    print(f"{'all':16} {'':8} " + " ".join(f"{tot[k]:>16}" for k in CLASSES) + f" {sum(tot.values()):>6}")
    print("# items per class (distinct count strings in parentheses); a==b: items whose two sides are equal")
    if a.list:
        want = CLASSES if a.list == "all" else [a.list]
        for x in everything:
            if x["cls"] in want:
                print(f"{x['cls']:16} {x['file']}:{x['line']}  {x['count']}  [{x['why']}; {x['where'] or '-'}] "
                      f"{x['script'] or '-'}  | {x['text']}")


if __name__ == "__main__":
    main()
