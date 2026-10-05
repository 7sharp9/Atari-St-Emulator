"""Driver for lua/lab.lua experiments.  run_plans(name, [(tag, plan_dict)], parallel=6) writes out/<name>/<tag>/plan.lua, runs ./labrun.sh and returns the log paths.
plan_dict keys: stop, pin=(x,y), scriptoff, god, events=[(frame, 'spawn', type, var, x, y) | (frame,'hit',slot,val) | (frame,'poke8',addr,val) | (frame,'kill',slot)], scroll=(sx,sy) optional (written at load)."""
import os, subprocess, sys, concurrent.futures
HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
def lua_plan(p):
    ev = []
    for e in p.get("events", []):
        ev.append("{" + ",".join(('"%s"' % x) if isinstance(x, str) else str(x) for x in e) + "}")
    setup = ""
    if p.get("scroll"):
        setup = "setup = function(m) m:write_u16(0x8040a, %d); m:write_u16(0x80406, %d) end," % p["scroll"]
    pin = ("pin = {x=%d,y=%d}," % p["pin"]) if p.get("pin") else ""
    return "return { stop=%d, %s scriptoff=%s, god=%s, shots={%s}, %s events={%s} }\n" % (
        p["stop"], pin, str(p.get("scriptoff", True)).lower(), str(p.get("god", True)).lower(),
        ",".join("[%d]=true" % s for s in p.get("shots", [])), setup, ",\n".join(ev))
def run_one(name, tag, p, secs=3000):
    d = os.path.join(HERE, "out", name, tag); os.makedirs(d, exist_ok=True)
    pl = os.path.join(d, "plan.lua"); open(pl, "w").write(lua_plan(p))
    env = dict(os.environ, SECS=str(secs))
    subprocess.run([os.path.join(HERE, "labrun.sh"), os.path.join(name, tag), pl], env=env, cwd=HERE, check=False)
    return os.path.join(d, "enemylog.txt")
def run_plans(name, plans, parallel=6):
    with concurrent.futures.ThreadPoolExecutor(parallel) as ex:
        futs = {tag: ex.submit(run_one, name, tag, p) for tag, p in plans}
        return {tag: f.result() for tag, f in futs.items()}
