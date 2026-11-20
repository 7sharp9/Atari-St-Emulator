"""Aggregate the per-chunk npz files made by run_chunks.sh into routines.csv and coverage numbers.

usage: CENSUS_DIR=<dir> .venv/bin/python <this>   (CENSUS_DIR default $VIRUS_WORK/census; CENSUS_SYM overrides virus.sym)
  reads  $CENSUS_DIR/meta.jsonl and $CENSUS_DIR/<label>/<label>_NNN.npz
  writes $CENSUS_DIR/routines.csv, ranked_unnamed.txt, coverage.txt

Phases: for the long game label (g050) a chunk is assigned to wave bucket `w<N>` (N = raw $32a50; the HUD
shows N+1) when $32a50 is the same at the chunk's start and end, else to `w<N>to<M>` (a 10M-step chunk that
holds a wave change; `(over)` when lives are 0 at its end), and `postover` when lives are 0 at its start; other labels (over, title, press) are one phase each.
"""
import collections
import json
import os
import sys
from pathlib import Path
import numpy as np

ROOT = next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
WORK = Path(os.environ.get("CENSUS_DIR") or Path(os.environ.get("VIRUS_WORK") or ROOT / "scratchpad/virus") / "census")
sys.path.insert(0, str(ROOT / "tools"))
import doc_addrs  # noqa: E402

CODE_LO, CODE_HI = 0xC000, 0x27FFC + 2


def load_sym():
    syms = {}
    for line in Path(os.environ.get("CENSUS_SYM") or ROOT / "reversing/virus/virus.sym").read_text().splitlines():
        s = line.split("#", 1)[0].split()
        if len(s) >= 2:
            syms[int(s[0].lstrip("$"), 16)] = s[1]
    return syms


def parse_mem(s):
    b = [int(x, 16) for x in s.split()]
    # start wave word, start lives word, end wave word, end lives word, demo flag byte
    return dict(w0=b[0] << 8 | b[1], l0=b[2] << 8 | b[3], w1=b[4] << 8 | b[5], l1=b[6] << 8 | b[7], flag=b[8] if len(b) > 8 else None)


def main():
    metas = [json.loads(l) for l in (WORK / "meta.jsonl").read_text().splitlines()]
    phases = collections.OrderedDict()
    calls = collections.defaultdict(lambda: collections.Counter())      # addr -> phase -> n
    kinds = collections.defaultdict(lambda: [0, 0])                      # addr -> [direct, indirect]
    ints = collections.Counter()
    sites = collections.defaultdict(set)
    cover = {}                                                           # phase -> bool array
    steps_by_phase = collections.Counter()
    for m in metas:
        z = np.load(WORK / m["label"] / f"{m['label']}_{m['chunk']:03d}.npz")
        mem = parse_mem(m["mem"])
        if m["label"] == "g050":
            if mem["l0"] == 0:
                ph = "postover"      # attract game after the game over: no wave
            elif mem["w0"] == mem["w1"]:
                ph = f"w{mem['w0']}"
            else:
                ph = f"w{mem['w0']}to{mem['w1']}" + ("(over)" if mem["l1"] == 0 else "")
        else:
            ph = m["label"]
        phases.setdefault(ph, None)
        steps_by_phase[ph] += int(z["step1"][0] - z["step0"][0])
        for k, (t, n) in enumerate((("direct_t", "direct_n"), ("indirect_t", "indirect_n"))):
            for a, c in zip(z[t].tolist(), z[n].tolist()):
                calls[a][ph] += c
                kinds[a][k] += c
        for a, c in zip(z["int_t"].tolist(), z["int_n"].tolist()):
            ints[a] += c
        for a, p in zip(z["site_t"].tolist(), z["site_pc"].tolist()):
            sites[a].add(p)
        cv = np.unpackbits(z["cover"])[:0x80000].astype(bool)
        cover[ph] = cover[ph] | cv if ph in cover else cv
    syms = load_sym()
    mentions = collections.Counter()
    for g, f, n, line, kind, v, mm in doc_addrs.scan("virus"):
        if kind in ("addr", "imm"):
            mentions[v] += 1
    sym_addrs = sorted(syms)
    import bisect

    def inside(a):
        i = bisect.bisect_right(sym_addrs, a) - 1
        return f"{syms[sym_addrs[i]]}+{a - sym_addrs[i]:#x}" if i >= 0 and 0 < a - sym_addrs[i] < 0x400 else ""
    plist = list(phases)
    rows = []
    for a, c in calls.items():
        tot = sum(c.values())
        rows.append((a, tot, c))
    rows.sort(key=lambda r: -r[1])
    with open(WORK / "routines.csv", "w") as f:
        f.write("addr,total,direct,indirect,sites,named,sym,doc_mentions,inside_sym," + ",".join(plist) + "\n")
        for a, tot, c in sorted(rows, key=lambda r: r[0]):
            f.write(f"{a:06x},{tot},{kinds[a][0]},{kinds[a][1]},{len(sites[a])},{int(a in syms)},{syms.get(a, '')},"
                    f"{mentions.get(a, 0)},{inside(a)}," + ",".join(str(c.get(p, 0)) for p in plist) + "\n")
    game = [r for r in rows if CODE_LO <= r[0] < CODE_HI]
    unnamed = [r for r in game if r[0] not in syms]
    with open(WORK / "ranked_unnamed.txt", "w") as f:
        for a, tot, c in sorted(unnamed, key=lambda r: -r[1]):
            f.write(f"{a:06x} {tot:12d} sites={len(sites[a]):3d} ind={kinds[a][1]:10d} docs={mentions.get(a, 0)} {inside(a)}\n")
    with open(WORK / "coverage.txt", "w") as f:
        tot = np.zeros(0x80000, bool)
        for p, cv in cover.items():
            tot |= cv
        span = CODE_HI - CODE_LO
        def line(name, cv):
            n = int(cv[CODE_LO:CODE_HI].sum())
            lo = int(np.flatnonzero(cv[CODE_LO:CODE_HI])[0]) + CODE_LO if n else 0
            hi = int(np.flatnonzero(cv[CODE_LO:CODE_HI])[-1]) + CODE_LO if n else 0
            return f"{name:12s} bytes {n:6d} of {span} ({100 * n / span:.1f}%) first ${lo:x} last ${hi:x}\n"
        f.write(line("ALL", tot))
        for p, cv in cover.items():
            f.write(line(p, cv) + f"{'':12s} steps {steps_by_phase[p]}\n")
        f.write(f"outside code window: {int(tot[:CODE_LO].sum())} bytes below ${CODE_LO:x}, {int(tot[CODE_HI:].sum())} at/above ${CODE_HI:x}\n")
        np.save(WORK / "cover_all.npy", np.packbits(tot))
    ng = len(game)
    print(f"game-code call targets {ng}; named {ng - len(unnamed)}; unnamed {len(unnamed)}; all targets {len(rows)}; "
          f"interrupt targets {len(ints)}")
    print(f"phases: {', '.join(f'{p}:{steps_by_phase[p]}' for p in plist)}")
    print((WORK / "coverage.txt").read_text())


if __name__ == "__main__":
    main()
