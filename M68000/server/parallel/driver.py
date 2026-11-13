#!/usr/bin/env python3
"""driver.py: runs every arm of the threads-vs-processes experiment through par.fsx and appends one JSON row per
run to <out>/results.jsonl as each run ends. See README.md.

  python3 driver.py <out_dir> [--n 20000000] [--rounds 3] [--phase equality,scaling,memory|all]

Each row carries the arm, the `uptime` line before the run, the wall time of the whole run (process start to exit,
fsi start-up included), /usr/bin/time -l's maximum resident set size per process, and par.fsx's own JSON (stepping-loop
time, gen-0/1/2 collections, GC pause, per-thread allocation, end-snapshot paths)."""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
M = HERE
while not os.path.exists(os.path.join(M, "tools", "rdis.py")):
    M = os.path.dirname(M)
ROM = os.path.join(M, "TOS100UK.IMG")
JOBS = {
    "pm": (os.path.join(M, "scratchpad/pm123/win/m1_s0.snap"), os.path.join(M, "scratchpad/powermonger.st")),
    "pop": (os.path.join(M, "scratchpad/pop/repro.snap"), os.path.join(M, "scratchpad/pop/pop_auto.st")),
}

args = sys.argv[1:]
OUT = os.path.abspath(args[0])
def opt(k, d):
    return args[args.index(k) + 1] if k in args else d
N = int(opt("--n", "20000000"))
ROUNDS = int(opt("--rounds", "3"))
PHASE = opt("--phase", "all").split(",")
SNAPS = os.path.join(OUT, "snaps")
LOGS = os.path.join(OUT, "logs")
os.makedirs(SNAPS, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)
RESULTS = os.path.join(OUT, "results.jsonl")


def uptime():
    return subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()


def env(server_gc, extra_env=None):
    e = dict(os.environ)
    e.update(extra_env or {})
    e["ATARI_NOTRACE"] = "1"
    e["DOTNET_gcServer"] = "1" if server_gc else "0"
    return e


def par_cmd(tag, assign, mode="threads", n=None, extra=(), pokes=()):
    c = ["/usr/bin/time", "-l", "dotnet", "fsi", os.path.join(HERE, "par.fsx"), "--rom", ROM,
         "--n", str(N if n is None else n), "--out", SNAPS, "--tag", tag, "--mode", mode, "--assign", ",".join(assign)]
    for name in sorted(set(assign)):
        c += ["--job", "%s=%s|%s" % (name, JOBS[name][0], JOBS[name][1])]
    for e in extra:
        c += ["--extra", e]
    for p in pokes:
        c += ["--poke", p]
    return c


def parse(stdout, stderr):
    row = None
    for line in stdout.splitlines():
        if line.startswith("{"):
            row = json.loads(line)
    m = re.search(r"(\d+)\s+maximum resident set size", stderr)
    return row, (int(m.group(1)) if m else None)


def launch(tag, cmd, server_gc, extra_env=None):
    log = os.path.join(LOGS, tag)
    so, se = open(log + ".out", "w"), open(log + ".err", "w")
    p = subprocess.Popen(cmd, cwd=HERE, env=env(server_gc, extra_env), stdout=so, stderr=se)
    return p, log, so, se


def finish(p, log, so, se):
    p.wait()
    so.close(); se.close()
    return p.returncode, open(log + ".out").read(), open(log + ".err").read()


def emit(row):
    with open(RESULTS, "a") as f:
        f.write(json.dumps(row) + "\n")


def one(arm, tag, assign, server_gc=False, extra_env=None, **kw):
    """One fsi process stepping len(assign) machines."""
    up = uptime()
    t0 = time.time()
    p, log, so, se = launch(tag, par_cmd(tag, assign, **kw), server_gc, extra_env)
    with open(os.path.join(OUT, "children.pid"), "a") as f:
        f.write("%d %s\n" % (p.pid, tag))
    rc, out, err = finish(p, log, so, se)
    wall = time.time() - t0
    r, rss = parse(out, err)
    emit({"arm": arm, "tag": tag, "rc": rc, "uptime": up, "wall_s": wall, "maxrss": [rss], "procs": [r],
          "k": len(assign), "server_gc_env": server_gc, "extra_env": extra_env or {}, "cmd": par_cmd(tag, assign, **kw)})


def procs(arm, tag, assign):
    """len(assign) concurrent fsi processes, one machine each (workstation GC, the emulator's own default)."""
    up = uptime()
    t0 = time.time()
    running = []
    for i, name in enumerate(assign):
        t = "%s_p%02d" % (tag, i)
        p = launch(t, par_cmd(t, [name], mode="seq"), False)
        with open(os.path.join(OUT, "children.pid"), "a") as f:
            f.write("%d %s\n" % (p[0].pid, t))
        running.append(p)
    res = [finish(*p) for p in running]
    wall = time.time() - t0
    rows, rss = zip(*[parse(o, e) for (_, o, e) in res])
    emit({"arm": arm, "tag": tag, "rc": max(r for (r, _, _) in res), "uptime": up, "wall_s": wall,
          "maxrss": list(rss), "procs": list(rows), "k": len(assign), "server_gc_env": False,
          "cmd": par_cmd(tag + "_p00", [assign[0]], mode="seq")})


def mixed(k):
    return [("pm", "pop")[i % 2] for i in range(k)]


if {"equality", "all"} & set(PHASE):
    for g in ("pm", "pop"):                       # positive control: the sequential reference twice
        for rep in ("a", "b"):
            one("ref", "ref_%s_%s" % (g, rep), [g], mode="seq")
    for k in (1, 2, 4, 8, 16):
        one("eq_threads_ws", "eq_t%d" % k, mixed(k))
    one("eq_threads_ws", "eq_t16_pm", ["pm"] * 16)
    one("eq_threads_ws", "eq_t16_pop", ["pop"] * 16)
    for rep in range(5):
        one("eq_threads_ws_rep", "eq_t8_r%d" % rep, mixed(8))
    one("eq_seq_ws", "eq_seq4", mixed(4), mode="seq")
    one("eq_threads_srv", "eq_srv_t8", mixed(8), server_gc=True)
    one("eq_threads_srv", "eq_srv_t16", mixed(16), server_gc=True)
    # negative controls: machine 2 one extra step; machine 1 poked at $380 (TOS crash-dump area) before the run
    one("neg_extra", "neg_extra_t4", mixed(4), extra=["2=1"])
    one("neg_poke", "neg_poke_t4", mixed(4), pokes=["1=380=5a"])

if {"memory", "all"} & set(PHASE):
    for k in (1, 16):                              # construct + load only: memory per machine in one process
        one("mem_threads", "mem_k%d" % k, mixed(k), n=0)

if {"scaling", "all"} & set(PHASE):
    for rnd in range(ROUNDS):
        for k in (1, 2, 4, 8, 16):
            arms = [("threads_ws", lambda t: one("sc_threads_ws", t, mixed(k))),
                    ("procs_ws", lambda t: procs("sc_procs_ws", t, mixed(k))),
                    ("threads_srv", lambda t: one("sc_threads_srv", t, mixed(k), server_gc=True))]
            if k >= 8:                             # workstation GC with a 256 MB gen-0 budget (GCgen0size, hex)
                arms.append(("threads_ws_g0", lambda t: one("sc_threads_ws_g0", t, mixed(k),
                                                            extra_env={"DOTNET_GCgen0size": "10000000"})))
            if (rnd + k) % 2:                      # alternate the order per round and K
                arms.reverse()
            for name, f in arms:
                f("sc_%s_k%d_r%d" % (name, k, rnd))

emit({"arm": "done", "uptime": uptime()})
