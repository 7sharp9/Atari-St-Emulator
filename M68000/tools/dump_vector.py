#!/usr/bin/env python3
"""Inspect SingleStepTests / ProcessorTests 68000 vectors (the `selftest` fixtures).

The `selftest` CLI reports a per-file pass/fail tally and a few FAIL sample lines,
but chasing a `frame` (exception-frame) or `wrong` sub-class means reading the raw
vectors: what the initial state was, what the 14-byte group-0 frame on the
supervisor stack should look like, which An the fault path should have fixed up,
where the stacked PC points. This does that.

    python tools/dump_vector.py JMP --frame          # first few real group-0 frames, decoded
    python tools/dump_vector.py ADDX.l --frame -n 8   # 8 genuine address-error frames
    python tools/dump_vector.py CLR.w --name 4243 --regs   # one named case, full registers
    python tools/dump_vector.py MOVE.l --count        # just the tally

The counts are fixture-wide (every matching case), not the subset the emulator
currently fails - `selftest` gives you the fail count, this shows you what those
frames should contain so you can spot the pattern.

Selection mirrors `Program.fs` `SelfTest.runCase`: a case is SKIPPED when the
initial PC is odd / < 8 or any referenced RAM address is < 8. `--frame` keeps
only GENUINE group-0 frames (fin.pc == the seeded vector-2/3 handler);
`--classifier-frame` keeps everything the selftest buckets as `frame`, which
also catches `-(A7)` predecrements that merely walked SSP down (that gap is why
ADDX/SUBX/MOVE show inflated `frame` counts).

Frame layout (68000 group 0, vector 2/3), from `EnterGroup0Vector` / the WinUAE
oracle: [ssp+0].w mode/SSW, [ssp+2].l fault addr, [ssp+6].w opcode,
[ssp+8].w pre-exception SR, [ssp+10].l stacked PC.

`.json.gz` fixtures live in M68000/tests/680x0/ (fetch_680x0_tests.py); not
committed. Prints nothing that isn't already in those public CC0 files.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests" / "680x0"

DREG = [f"d{i}" for i in range(8)]
AREG = [f"a{i}" for i in range(7)]


def find_file(token: str) -> Path:
    p = Path(token)
    if p.exists():
        return p
    cands = sorted(
        f for f in TESTS_DIR.glob("*.json*")
        if token.lower() in f.name.lower()
    )
    if not cands:
        sys.exit(f"no vector file under {TESTS_DIR} matching {token!r}")
    if len(cands) > 1:
        # prefer an exact stem match (JMP -> JMP.json.gz, not JMPfoo)
        exact = [c for c in cands if c.name.lower().startswith(token.lower() + ".")]
        if len(exact) == 1:
            return exact[0]
        sys.exit("ambiguous: " + ", ".join(c.name for c in cands))
    return cands[0]


def load(path: Path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt") as fh:
        return json.load(fh)


def ram_map(entry) -> dict:
    return {a: v for a, v in entry.get("ram", [])}


def would_skip(ini, fin) -> bool:
    if ini["pc"] % 2 or ini["pc"] < 8:
        return True
    for a, _ in ini.get("ram", []) + fin.get("ram", []):
        if a < 8:
            return True
    return False


def classifier_frame(ini, fin) -> bool:
    """The exact test Program.fs SelfTest.runCase uses to bucket a fail as `frame`
    rather than `wrong`: final state supervisor AND supervisor stack moved down."""
    return bool(fin["sr"] & 0x2000) and fin["ssp"] < ini["ssp"]


def real_group0_frame(ini, fin) -> bool:
    """True group-0 exception: fin.pc is the vector-2 or vector-3 handler that the
    case seeded into low RAM. Distinguishes a genuine bus/address-error frame from
    a `-(A7)` predecrement that merely walked SSP down (which the classifier above
    also flags, giving ADDX/SUBX/MOVE their inflated `frame` counts)."""
    mi = ram_map(ini)
    for vec in (2, 3):
        base = vec * 4
        h = u32([mi.get(base + i) for i in range(4)])
        if h is not None and h == fin["pc"] and fin["ssp"] < ini["ssp"]:
            return True
    return False


def rd(m_fin, m_ini, a):
    if a in m_fin:
        return m_fin[a]
    return m_ini.get(a, None)


def u16(b0, b1):
    if b0 is None or b1 is None:
        return None
    return (b0 << 8) | b1


def u32(bs):
    if any(b is None for b in bs):
        return None
    return (bs[0] << 24) | (bs[1] << 16) | (bs[2] << 8) | bs[3]


def hexn(v, w=8):
    return "????????"[:w] if v is None else f"{v:0{w}x}"


def decode_frame(ini, fin):
    """Return the 14-byte group-0 frame read at fin['ssp'] plus derived fields."""
    mf, mi = ram_map(fin), ram_map(ini)
    ssp = fin["ssp"]
    b = [rd(mf, mi, ssp + i) for i in range(14)]
    mode = u16(b[0], b[1])
    faddr = u32(b[2:6])
    op = u16(b[6], b[7])
    sr = u16(b[8], b[9])
    spc = u32(b[10:14])
    return {
        "ssp": ssp,
        "bytes": b,
        "mode": mode,
        "fault_addr": faddr,
        "opcode": op,
        "stacked_sr": sr,
        "stacked_pc": spc,
        "ssp_delta": ini["ssp"] - ssp,
        # mode word cracked open
        "mode_sv": None if mode is None else bool(mode & 4),
        "mode_fc": None if mode is None else (mode & 3),
        "mode_rw_read": None if mode is None else bool(mode & 16),
        "mode_notinstr": None if mode is None else bool(mode & 8),
        "mode_opbits": None if mode is None else (mode & ~0x1f) & 0xffff,
    }


def reg_deltas(ini, fin):
    out = []
    for r in DREG + AREG + ["pc", "usp", "ssp", "sr"]:
        iv, fv = ini.get(r), fin.get(r)
        if iv != fv:
            w = 4 if r == "sr" else 8
            out.append(f"{r}:{hexn(iv, w)}->{hexn(fv, w)}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="vector file path, or a family substring (JMP, ADDX.l, ...)")
    ap.add_argument("--frame", action="store_true",
                    help="only genuine group-0 (bus/address-error) frame cases")
    ap.add_argument("--classifier-frame", action="store_true",
                    help="only cases the Program.fs classifier buckets as `frame` "
                         "(includes -(A7) predecrements that just walked SSP down)")
    ap.add_argument("--skip", action="store_true", help="only cases selftest would SKIP")
    ap.add_argument("--name", default=None, help="only cases whose name contains this")
    ap.add_argument("-n", "--limit", type=int, default=6, help="max cases to print (default 6)")
    ap.add_argument("--regs", action="store_true", help="print every changed register, not just the frame")
    ap.add_argument("--raw", action="store_true", help="also dump the 14 frame bytes")
    ap.add_argument("--count", action="store_true", help="just tally frame / skip / other, print nothing else")
    args = ap.parse_args()

    path = find_file(args.file)
    data = load(path)

    n_real = n_cls = n_skip = n_other = n_total = 0
    shown = 0
    for case in data:
        ini, fin = case["initial"], case["final"]
        skip = would_skip(ini, fin)
        real = (not skip) and real_group0_frame(ini, fin)
        cls = (not skip) and classifier_frame(ini, fin) and bool(reg_deltas(ini, fin))
        if skip:
            n_skip += 1
        else:
            if real:
                n_real += 1
            if cls:
                n_cls += 1
            if not cls:
                n_other += 1
        n_total += 1

        if args.count:
            continue
        if args.name and args.name.lower() not in case["name"].lower():
            continue
        if args.frame and not real:
            continue
        if args.classifier_frame and not cls:
            continue
        if args.skip and not skip:
            continue
        if shown >= args.limit:
            continue
        shown += 1

        pref = ini.get("prefetch", [])
        print(f"\n=== {case['name']}   [{path.name}]")
        print(f"  ini  pc={hexn(ini['pc'])} sr={hexn(ini['sr'],4)} "
              f"ssp={hexn(ini['ssp'])} usp={hexn(ini['usp'])} "
              f"prefetch={[hex(x) for x in pref]}")
        print(f"  fin  pc={hexn(fin['pc'])} sr={hexn(fin['sr'],4)} "
              f"ssp={hexn(fin['ssp'])} usp={hexn(fin['usp'])}")
        if args.regs:
            print("  changed:", "  ".join(reg_deltas(ini, fin)) or "(none)")
        if real or cls:
            f = decode_frame(ini, fin)
            tag = "FRAME" if real else "classifier-frame (SSP walked down, not a real exception)"
            print(f"  {tag} @ssp={hexn(f['ssp'])}  ssp_delta={f['ssp_delta']}")
            print(f"    mode/SSW = {hexn(f['mode'],4)}   "
                  f"sv={f['mode_sv']} fc={f['mode_fc']} "
                  f"rw={'READ' if f['mode_rw_read'] else 'WRITE'} "
                  f"notinstr={f['mode_notinstr']} opbits={hexn(f['mode_opbits'],4)}")
            print(f"    fault_addr = {hexn(f['fault_addr'])}")
            print(f"    opcode     = {hexn(f['opcode'],4)}  (prefetch[0]={hex(pref[0]) if pref else '?'})")
            print(f"    stacked_sr = {hexn(f['stacked_sr'],4)}")
            print(f"    stacked_pc = {hexn(f['stacked_pc'])}  "
                  f"(ini.pc + {None if f['stacked_pc'] is None else f['stacked_pc'] - ini['pc']})")
            if args.raw:
                print("    bytes:", " ".join(
                    "??" if x is None else f"{x:02x}" for x in f["bytes"]))
        elif not skip and not args.regs:
            print("  changed:", "  ".join(reg_deltas(ini, fin)) or "(none)")

    print(f"\n{path.name}: {n_total} cases   real-group0-frame={n_real}   "
          f"classifier-frame={n_cls}   skip={n_skip}   other={n_other}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
