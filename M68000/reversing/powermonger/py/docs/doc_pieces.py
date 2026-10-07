#!/usr/bin/env python3
"""Split the powermonger docs at '## ' headings (outside code fences) into pieces, and join them.

doc_pieces.py split                 -> $WORK/in/<doc>/<NN>_<slug>.md (concatenating the pieces is byte-identical to the doc)
doc_pieces.py join DIR [--only doc,...] -> writes the joined docs of piece dir DIR (for example $WORK/out) to DIR/joined/<doc>.md
$WORK = $DOCCLEAN_WORK, default M68000/scratchpad/docclean. Method: BRIEF.md in this directory.
Edit the PIECES, never DIR/joined: a join rebuilds joined/ from the pieces and discards edits made there.
"""
import re, sys, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, "../.."))   # reversing/powermonger
HERE = os.environ.get("DOCCLEAN_WORK") or os.path.normpath(os.path.join(DOCS, "../../scratchpad/docclean"))   # work dir (in/, out/)
NAMEPATH = {"README": "README.md", "strategy": "strategy.md", "ai": "ai.md", "economy": "economy.md", "graphics": "graphics.md", "system": "system.md",
            "py_README": "py/README.md", "port_README": "port/README.md", "port_SPEC": "port/SPEC.md"}
NAMES = list(NAMEPATH)


def pieces_of(text):
    out, cur, fence = [], [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and line.startswith("## ") and cur:
            out.append("".join(cur))
            cur = []
        cur.append(line)
    out.append("".join(cur))
    return out


def slug(piece):
    first = piece.splitlines()[0]
    s = re.sub(r"[^a-z0-9]+", "_", first.lower()).strip("_")
    return s[:40] or "head"


def split():
    for n in NAMES:
        text = open(f"{DOCS}/{NAMEPATH[n]}", encoding="utf-8", newline="").read()
        ps = pieces_of(text)
        assert "".join(ps) == text
        d = f"{HERE}/in/{n}"
        os.makedirs(d, exist_ok=True)
        for i, p in enumerate(ps):
            name = "00_preamble.md" if (i == 0 and not p.startswith("## ")) else f"{i:02d}_{slug(p)}.md"
            open(f"{d}/{name}", "w", encoding="utf-8", newline="").write(p)
        print(n, len(ps), "pieces")


def join(src, only=None):
    os.makedirs(f"{src}/joined", exist_ok=True)
    for n in NAMES:
        if only and n not in only:
            continue
        fs = sorted(glob.glob(f"{src}/{n}/*.md"))
        text = "".join(open(f, encoding="utf-8", newline="").read() for f in fs)
        open(f"{src}/joined/{n}.md", "w", encoding="utf-8", newline="").write(text)
        print(n, len(fs), "pieces", len(text), "bytes")


if __name__ == "__main__":
    if sys.argv[1] == "split":
        split()
    else:
        only = None
        if "--only" in sys.argv:
            only = sys.argv[sys.argv.index("--only") + 1].split(",")
        join(sys.argv[2], only)
