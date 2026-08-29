#!/usr/bin/env python3
"""Download the SingleStepTests / ProcessorTests 68000 instruction-level test
vectors (github.com/SingleStepTests/ProcessorTests, `680x0/68000/v1`).

Each opcode has its own `NAME.json.gz` file holding ~8000 randomised cases, each
with a full initial machine state and the expected final registers / SR /
memory. The emulator runs them via its `selftest` CLI mode:

    python tools/fetch_680x0_tests.py            # -> M68000/tests/680x0/*.json.gz
    dotnet exec bin/Debug/net8.0/M68000.dll selftest tests/680x0
    dotnet exec bin/Debug/net8.0/M68000.dll selftest tests/680x0 lsr   # one family

The `.json.gz` files are NOT committed (see .gitignore) - they are ~1.5 MB each,
~190 MB total, and are external fixture data keyed to nothing in this repo.

The vectors are CC0-licensed. This script only fetches; it stores nothing that
isn't already public.
"""
import argparse
import sys
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/SingleStepTests/ProcessorTests/main/680x0/68000/v1"
API = "https://api.github.com/repos/SingleStepTests/ProcessorTests/contents/680x0/68000/v1"


def list_files() -> list[str]:
    import json

    with urllib.request.urlopen(API) as r:
        entries = json.load(r)
    return sorted(e["name"] for e in entries if e["name"].endswith(".json.gz"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "tests" / "680x0"),
                    help="destination directory (default: M68000/tests/680x0)")
    ap.add_argument("--only", nargs="*", default=None,
                    help="only fetch files whose name contains one of these substrings (e.g. LSR ROR)")
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    names = list_files()
    if args.only:
        subs = [s.lower() for s in args.only]
        names = [n for n in names if any(s in n.lower() for s in subs)]
    if not names:
        print("nothing to fetch", file=sys.stderr)
        return 1

    for i, name in enumerate(names, 1):
        dest = out / name
        if dest.exists() and not args.force:
            print(f"[{i:3}/{len(names)}] skip {name} (exists)")
            continue
        print(f"[{i:3}/{len(names)}] {name} ...", end="", flush=True)
        urllib.request.urlretrieve(f"{RAW}/{name}", dest)
        print(f" {dest.stat().st_size // 1024} KB")

    print(f"\n{len(names)} file(s) in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
