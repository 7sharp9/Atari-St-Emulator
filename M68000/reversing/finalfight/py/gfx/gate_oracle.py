"""gate_oracle.py: ffframes.build against the game's own `$16910`, run in MAME on a fake record (framecap.lua).
Tests: every frame block reachable from a plausible animation script found by scan_scripts.py (frames of every
script, plus the blocks at the loop targets), each under 4 variants (mirror, palette byte 47, x offset 48) and one
position/camera.  The oracle's entry list must equal the port's, word for word.
Usage: python gate_oracle.py [--max N]      (needs scripts.json from scan_scripts.py; about N/100 s of MAME time)"""
import json, os, random, subprocess, sys, collections
import ffframes as F
from cpsgfx import OUT, ROOT

VARS = [(0, 0, 0), (1, 0, 0), (0, 5, 3), (1, 7, -3)]
POS = dict(x=300, y=100, camx=80, camy=16)


def blocks():
    sc = json.load(open(os.path.join(OUT, "scripts.json")))
    bl = {}
    for a, v in sc.items():
        if not v["ok"]:
            continue
        frames, loop = F.script(int(a, 16))
        for (_, b, _, _) in frames:
            bl.setdefault(b, []).append(a)
    return bl


def main():
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10 ** 9
    bl = sorted(blocks())[:mx]
    tests = []
    for b in bl:
        for (m, p, xo) in VARS:
            tests.append((b, m, p, xo))
    tin = os.path.join(OUT, "oracle_tests.txt")
    tout = os.path.join(OUT, "oracle_out.txt")
    with open(tin, "w") as f:
        for (b, m, p, xo) in tests:
            f.write("%x %d %d %d %d %d %d %d\n" % (b, m, p, xo, POS["x"], POS["y"], POS["camx"], POS["camy"]))
    env = dict(os.environ, FF_MAMEARGS="-debug -debugger none", FC_IN=tin, FC_OUT=tout)
    secs = str(max(600, len(tests) // 20))
    subprocess.run(["sh", os.path.join(ROOT, "reversing", "finalfight", "ffrun.sh"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "framecap.lua"), secs], env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = {}
    for line in open(tout):
        t = line.split()
        i, n = int(t[0]), int(t[1])
        e = [tuple(int(v, 16) for v in t[2 + 4 * k:6 + 4 * k]) for k in range(n)]
        res[i - 1] = e
    ok = bad = 0
    kinds_ok = collections.Counter()
    kinds_bad = collections.Counter()
    block_path = [0, 0]
    shown = 0
    for i, (b, m, p, xo) in enumerate(tests):
        if i not in res:
            continue
        mine = F.build(b, POS["x"], POS["y"], POS["camx"], POS["camy"], mirror=bool(m), pal=p, xoff=xo)
        kind = F.rom[b] // 4
        isblock = F.w(b + 10) >= 0x100 or (p and (F.w(b + 10) & 0xffe0 | (p & 0x1f)) >= 0x100)
        if mine == res[i]:
            ok += 1
            kinds_ok[(kind, "block" if isblock else "tiles")] += 1
        else:
            bad += 1
            kinds_bad[(kind, "block" if isblock else "tiles")] += 1
            if shown < 6:
                shown += 1
                print("MISMATCH block %x mirror %d pal %d xoff %d: mine %s\n                 oracle %s" % (b, m, p, xo, mine[:4], res[i][:4]))
    print("tests %d, oracle answered %d, equal %d, different %d" % (len(tests), len(res), ok, bad))
    print("equal by (layout kind, path):", dict(sorted(kinds_ok.items())))
    print("different by (layout kind, path):", dict(sorted(kinds_bad.items())))


if __name__ == "__main__":
    main()
