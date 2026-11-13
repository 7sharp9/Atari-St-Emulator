#!/usr/bin/env python3
"""compare.py: byte-compares every end snapshot in <out>/results.jsonl against the sequential reference of the same
game (ref_<game>_a) and summarises equality and scaling. Writes <out>/compare.jsonl and prints the tables.

  python3 compare.py <out_dir> [<refs_dir>]   (refs_dir: a run holding the ref_* rows; default out_dir)"""
import hashlib, json, os, statistics, sys

OUT = os.path.abspath(sys.argv[1])
rows = [json.loads(l) for l in open(os.path.join(OUT, "results.jsonl"))]

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

REFDIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else OUT
refrows = [json.loads(l) for l in open(os.path.join(REFDIR, "results.jsonl"))]
refs = {}
for r in refrows:
    if r["arm"] == "ref":
        g, rep = r["tag"].split("_")[1:3]
        refs.setdefault(g, {})[rep] = sha(r["procs"][0]["outs"][0])

print("positive control (sequential reference twice):")
for g, d in sorted(refs.items()):
    print("  %-4s a=%s b=%s identical=%s" % (g, d["a"][:16], d["b"][:16], d["a"] == d["b"]))

cmp_rows = []
print("\nequality per run (end snapshot sha256 == ref_<game>_a):")
for r in rows:
    if r["arm"] in ("ref", "done") or r["arm"].startswith("mem"):
        continue
    for p in r["procs"]:
        if p is None:
            print("  %s: a process wrote no result row (rc=%s)" % (r["tag"], r["rc"]))
            continue
        for i, path in enumerate(p["outs"]):
            game = p["assign"][i]
            ok = sha(path) == refs[game]["a"]
            cmp_rows.append({"tag": r["tag"], "arm": r["arm"], "out": path, "game": game, "match": ok})
with open(os.path.join(OUT, "compare.jsonl"), "w") as f:
    for c in cmp_rows:
        f.write(json.dumps(c) + "\n")
by_tag = {}
for c in cmp_rows:
    by_tag.setdefault((c["arm"], c["tag"]), []).append(c)
for (arm, tag), cs in by_tag.items():
    bad = [os.path.basename(c["out"]) for c in cs if not c["match"]]
    print("  %-18s %-24s %2d/%2d match%s" % (arm, tag, sum(c["match"] for c in cs), len(cs),
                                            ("  MISMATCH: " + " ".join(bad)) if bad else ""))

print("\nscaling (N=%s steps per machine; agg = K*N / wall of the stepping loops; e2e = K*N / whole-run wall):" %
      next((p["n"] for r in rows if r["arm"].startswith("sc_") for p in r["procs"] if p), "?"))
sc = {}
for r in rows:
    if not r["arm"].startswith("sc_") or any(p is None for p in r["procs"]):
        continue
    arm, k = r["arm"][3:], r["k"]
    ps = r["procs"]
    steps = sum(p["steps_total"] for p in ps)
    loop_s = max(p["run_ms"] for p in ps) / 1000.0   # for procs: the slowest process's stepping loop
    per_machine = statistics.median([p["n"] / (t / 1000.0) for p in ps for t in p["thread_ms"]])
    sc.setdefault((arm, k), []).append({
        "agg": steps / loop_s, "e2e": steps / r["wall_s"], "per": per_machine,
        "gc0": sum(p["gc0"] for p in ps), "gc1": sum(p["gc1"] for p in ps), "gc2": sum(p["gc2"] for p in ps),
        "pause": sum(p["gc_pause_ms"] for p in ps), "rss": sum(x for x in r["maxrss"] if x),
        "srv": ps[0]["server_gc"], "load": r["uptime"].split("load averages:")[-1].strip()})
print("  %-12s %3s %5s  %-22s %-22s %-18s %8s %7s %9s %9s  %s" % ("arm", "K", "srvGC", "agg Msteps/s med (best)",
      "e2e Msteps/s med (best)", "per-machine med", "gen0", "gen1", "pause ms", "RSS MB/K", "load avg per round"))
for (arm, k), xs in sorted(sc.items(), key=lambda t: (t[0][1], t[0][0])):
    med = lambda key: statistics.median([x[key] for x in xs])
    mn = lambda key: max(x[key] for x in xs)   # best rate = the minimum time
    print("  %-12s %3d %5s  %6.1f (%6.1f)        %6.1f (%6.1f)        %6.2f            %8d %7d %9.0f %9.0f  %s" % (
        arm, k, xs[0]["srv"], med("agg") / 1e6, mn("agg") / 1e6, med("e2e") / 1e6, mn("e2e") / 1e6, med("per") / 1e6,
        med("gc0"), med("gc1"), med("pause"), med("rss") / 1e6 / k, " | ".join(x["load"] for x in xs)))

print("\nmemory (construct + LoadState only, n=0):")
for r in rows:
    if r["arm"] == "mem_threads":
        print("  %s K=%d maxrss %.0f MB" % (r["tag"], r["k"], r["maxrss"][0] / 1e6))
