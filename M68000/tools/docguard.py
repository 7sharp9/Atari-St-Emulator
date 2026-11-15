"""Guard a prose rewrite: list every number, address, match count and code span it added or removed.

    uv run python tools/docguard.py [--ref REF] <file>...      each file against its version at REF (default HEAD)
    uv run python tools/docguard.py --pair BEFORE AFTER         two files on disk
    options: -q (one summary line per file), --context N (characters of context, default 70)

A clarity rewrite should change words, not facts. The guard extracts four kinds of token from each version and
compares them as multisets, so moving a sentence or a section changes nothing and only a token whose count
changed is reported:

  code   a backticked span, verbatim (`gate_score.py`, `$2337a`, `52(A1)`)
  ratio  a match count: `a/b`, `a / b` or `a of b`, thousands separators dropped (65,455 of 65,455 == 65455/65455)
  addr   `$hex` or `0xhex`, lower-cased, with or without `#`
  num    a decimal number not touching a letter, `_` or `$` (D0, pm88, x16 are not numbers), thousands separators
         dropped, a trailing % kept

Tokens inside code spans are also counted as addr/num, so dropping the backticks round `$1abaa` reports only the
code token. `.html`, `.htm` and `.svg` files are read as text with tags, scripts and styles removed and entities
decoded. Spelling a number as a word ("two" for 2) is reported as a removal: the reviewer decides.

Each changed token is listed with its delta and the first line it occurs on in the version that holds it. Exit
status: 0 when no file changed a token, 1 when any did, 2 on a usage or git error. A positive control: change one
digit in a doc and run the guard on it (`tools/tests/docguard_check.sh`).
"""
import argparse
import html
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

CODE = re.compile(r"`([^`\n]+)`")
ADDR = re.compile(r"(?<![\w$])#?(?:\$|0x)([0-9a-fA-F]+)\b")
_N = r"\d{1,3}(?:,\d{3})+|\d+"
RATIO = re.compile(rf"(?<![\w$.])({_N})\s*(?:/|\bof\b)\s*({_N})(?![\w.]|/\d)")
NUM = re.compile(rf"(?<![\w$.])-?({_N})(\.\d+)?(%?)(?![\w])")
TAGS = re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>", re.S | re.I)


def plain(n: str) -> str:
    return n.replace(",", "")


def tokens(text: str, markup: bool):
    """Return {token: [count, [(line number, line text), ...]]}."""
    if markup:
        text = html.unescape(TAGS.sub(" ", text))
    found: dict[str, list] = {}

    def add(tok, ln, line):
        if tok in found:
            found[tok][0] += 1
            found[tok][1].append((ln, line.strip()))
        else:
            found[tok] = [1, [(ln, line.strip())]]

    for ln, line in enumerate(text.splitlines(), 1):
        rest = line
        for m in CODE.finditer(line):
            add("code " + m.group(1), ln, line)
        rest = CODE.sub(lambda m: " " + m.group(1) + " ", rest)
        for m in ADDR.finditer(rest):
            add("addr $" + m.group(1).lower(), ln, line)
        rest = ADDR.sub(" ", rest)
        for m in RATIO.finditer(rest):
            add(f"ratio {plain(m.group(1))}/{plain(m.group(2))}", ln, line)
        rest = RATIO.sub(" ", rest)
        for m in NUM.finditer(rest):
            add(f"num {plain(m.group(1))}{m.group(2) or ''}{m.group(3)}", ln, line)
    return found


def git_version(path: Path, ref: str) -> str | None:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path.parent, capture_output=True,
                         text=True)
    if top.returncode:
        raise SystemExit(f"docguard: not in a git checkout: {path}")
    rel = path.resolve().relative_to(Path(top.stdout.strip()).resolve())
    r = subprocess.run(["git", "show", f"{ref}:{rel.as_posix()}"], cwd=top.stdout.strip(), capture_output=True)
    if r.returncode:
        if b"does not exist" in r.stderr or b"exists on disk, but not in" in r.stderr:
            return None
        raise SystemExit(f"docguard: git show {ref}:{rel}: {r.stderr.decode().strip()}")
    return r.stdout.decode("utf-8", "replace")


def compare(name: str, before: str | None, after: str, markup: bool, quiet: bool, width: int) -> bool:
    if before is None:
        print(f"{name}: new file (no version to compare)")
        return False
    a, b = tokens(before, markup), tokens(after, markup)
    changed = []
    for tok in sorted(set(a) | set(b)):
        ca, cb = a.get(tok, [0])[0], b.get(tok, [0])[0]
        if ca != cb:
            holder = b if cb > ca else a
            lines = set(l.strip() for l in (before if cb > ca else after).splitlines())
            occ = holder[tok][1]
            # the line to show: the first holding the token that the other version does not have verbatim
            changed.append((tok, cb - ca, next(((ln, t) for ln, t in occ if t not in lines), occ[0])))
    removed = sum(1 for _, d, _ in changed if d < 0)
    added = len(changed) - removed
    if not changed:
        print(f"{name}: CLEAN ({sum(v[0] for v in b.values())} tokens, none added or removed)")
        return False
    print(f"{name}: {removed} token(s) lost, {added} gained")
    if not quiet:
        for tok, d, (ln, line) in changed:
            side = "after" if d > 0 else "before"
            snip = line if len(line) <= width else line[:width] + "..."
            print(f"  {d:+d}  {tok:<34} {side}:{ln}  {snip}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--pair", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("-q", action="store_true")
    ap.add_argument("--context", type=int, default=70)
    o = ap.parse_args()
    if not o.files and not o.pair:
        ap.print_usage(sys.stderr)
        sys.exit(2)
    markup = lambda p: Path(p).suffix.lower() in (".html", ".htm", ".svg")
    dirty = False
    try:
        if o.pair:
            bp, ap_ = (Path(p) for p in o.pair)
            dirty |= compare(f"{bp} -> {ap_}", bp.read_text("utf-8", "replace"), ap_.read_text("utf-8", "replace"),
                             markup(ap_), o.q, o.context)
        for f in o.files:
            p = Path(f)
            if not p.exists():
                print(f"{f}: missing on disk (deleted?)")
                dirty = True
                continue
            dirty |= compare(f, git_version(p, o.ref), p.read_text("utf-8", "replace"), markup(p), o.q, o.context)
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code, file=sys.stderr)
            sys.exit(2)
        raise
    sys.exit(1 if dirty else 0)


if __name__ == "__main__":
    main()
