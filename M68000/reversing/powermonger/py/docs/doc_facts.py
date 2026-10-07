#!/usr/bin/env python3
"""Preservation check: facts in $WORK/in/<doc>/<piece> that are missing from $WORK/out/<doc>/<piece>, and facts new in out.

doc_facts.py [doc/piece.md ...]   (default: every piece present in out/); $WORK = $DOCCLEAN_WORK, default M68000/scratchpad/docclean
Whole-document check against git: import facts() and compare `git show HEAD:<doc>` with the working copy.
Facts: $hex addresses, file names, ratios (a/b and 'a of b' normalised), numbers of 3+ digits, pmNNN tags,
backticked identifiers.
"""
import re, sys, os, glob

HERE = os.environ.get("DOCCLEAN_WORK") or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../scratchpad/docclean"))

RX = {
    "hex": re.compile(r"\$[0-9a-fA-F]{2,8}\b|0x[0-9a-fA-F]+\b"),
    "file": re.compile(r"[A-Za-z0-9_./\\-]+\.(?:py|sh|fs|fsx|md|snap|cmds|png|json|txt|st|asm|sym|html|tmpl|ram|lua|cs)\b"),
    "ratio": re.compile(r"\b(\d[\d,]*)\s*(?:/|of)\s*(\d[\d,]*)\b"),
    "num": re.compile(r"(?<![\w$])\d[\d,]{2,}(?:\.\d+)?(?![\w])"),
    "pm": re.compile(r"\bpm\d{2,3}\w*\b"),
    "ident": re.compile(r"`([^`\n]{1,60})`"),
}


def facts(text):
    f = set()
    for k, rx in RX.items():
        for m in rx.finditer(text):
            if k == "ratio":
                f.add(("ratio", m.group(1).replace(",", "") + "/" + m.group(2).replace(",", "")))
            elif k == "num":
                f.add(("num", m.group(0).replace(",", "").rstrip(",")))
            elif k == "ident":
                f.add(("ident", m.group(1).strip().lower()))
            else:
                f.add((k, m.group(0).lower()))
    return f


def check(rel, verbose=True):
    a = open(f"{HERE}/in/{rel}", encoding="utf-8").read()
    p = f"{HERE}/out/{rel}"
    if not os.path.exists(p):
        return None
    b = open(p, encoding="utf-8").read()
    fa, fb = facts(a), facts(b)
    miss = sorted(fa - fb)
    new = sorted(fb - fa)
    if verbose:
        print(f"== {rel}: {len(a)} -> {len(b)} bytes ({100*len(b)//max(1,len(a))}%); missing {len(miss)}, new {len(new)}")
        for k in ("hex", "file", "pm", "ratio", "num", "ident"):
            mk = [v for t, v in miss if t == k]
            nk = [v for t, v in new if t == k]
            if mk:
                print(f"  MISSING {k}: " + "; ".join(mk))
            if nk:
                print(f"  NEW     {k}: " + "; ".join(nk))
    return miss, new


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = sorted(os.path.relpath(f, f"{HERE}/out") for f in glob.glob(f"{HERE}/out/*/*.md"))
    for r in args:
        if check(r) is None:
            print(f"== {r}: not written yet")
