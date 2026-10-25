"""stserver smoke test (DEVELOPING.md, "Memory hooks and the stserver process").

    python3 server/smoke.py <stserver.dll> <cadaver gameplay_empire.snap> <one-disk Empire .st> <outdir>

From the Cadaver gameplay snapshot, a write watch on $189ca-$189cd over 300,000 steps must give the
REPL's 25 WATCH events (writer PC $01529c, values $1e down to $06). Then: a fork/restore replay gives
a byte-identical end snapshot, a host poke is reported with source "host", a watch on an odd byte
sees the word write covering it, a missing 'disk' key is refused, and a malformed line leaves the
server alive. Exit status 0 = all pass.
"""
import json
import subprocess
import sys

dll, snap, disk, out = sys.argv[1:5]
proc = subprocess.Popen(["dotnet", "exec", dll], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
seq = 0


def call(method, **params):
    global seq
    seq += 1
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": seq, "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    r = json.loads(proc.stdout.readline())
    assert r["id"] == seq, r
    return r


def ok(method, **params):
    r = call(method, **params)
    if "error" in r:
        raise SystemExit(f"{method}: {r['error']['message']}")
    return r["result"]


fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not cond:
        fails.append(name)


r = call("load", snapshot=snap)
check("load without disk refused", "error" in r and "disk" in r["error"]["message"], r.get("error", {}).get("message", ""))

ok("load", snapshot=snap, disk=disk)
wid = ok("watch_add", lo="189ca", hi="189cd", kind="w")["id"]
fork = ok("fork")["id"]
res = ok("step", n=300000)
ev = ok("watch_events", id=wid)[0]["events"]
pcs = {e["pc"] for e in ev}
vals = [int(e["value"][1:], 16) for e in ev]
check("25 watch events", len(ev) == 25, f"{len(ev)} events")
check("writer PC $01529c", pcs == {"$01529c"}, str(pcs))
check("values $1e down to $06", bool(vals) and vals[0] == 0x1e and vals[-1] == 0x06, f"{vals[:3]}...{vals[-3:]}")
print("first event:", json.dumps(ev[0]) if ev else None)
ok("save", path=f"{out}/smoke_a.snap")

ok("restore", id=fork)
ok("step", n=300000)
ev2 = ok("watch_events", id=wid)[0]["events"]
ok("save", path=f"{out}/smoke_b.snap")
a = open(f"{out}/smoke_a.snap", "rb").read()
b = open(f"{out}/smoke_b.snap", "rb").read()
check("fork/restore replay identical", a == b and ev == ev2, f"{len(a)} bytes, {len(ev2)} events")

ok("poke", addr="189cc", width=2, value="1234")
hp = ok("watch_events", id=wid)[0]["events"]
check("host poke attributed", len(hp) == 1 and hp[0]["source"] == "host" and hp[0]["width"] == 2, json.dumps(hp))
check("peek reads the poke", ok("peek", addr="189cc", width=2) == ["$1234"])

odd = ok("watch_add", lo="189cd", kind="w", stop=True)["id"]
ok("restore", id=fork)
run = ok("run", max_steps=300000)
check("stop watch on odd byte stops run", run["reason"] == "watch" and run["watch"] == odd, json.dumps(run))
ok("watch_events")
ok("poke", addr="189cc", width=2, value="0")
ov = ok("watch_events", id=odd)[0]["events"]
check("word write at $189cc seen by a watch on $189cd", len(ov) == 1 and ov[0]["addr"] == "$0189cc", json.dumps(ov))

proc.stdin.write("not json\n")
proc.stdin.flush()
bad = json.loads(proc.stdout.readline())
check("malformed line answered", "error" in bad)
check("server alive after it", "pc" in ok("regs"))
print("render:", ok("render", path=f"{out}/smoke.png"))

ok("shutdown")
proc.wait(10)
print("ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
