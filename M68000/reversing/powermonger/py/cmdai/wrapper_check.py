"""141st: the four order wrappers inside the executor's table (`$6b8e` type 2, `$6ba8` type 4, `$6bbe` type 6, `$6bea` type 8): the registers
each hands its callee, against the code read.  Slot 3 (side 3, state 2) gets {type, x, y}; `bp <callee>` stops at the callee's entry and the
register dump is compared with the expectation:

    type 2  $3888   D0.w = x sign-extended, D1.w = y sign-extended, D6.w = $ea (`ext.w`: the high words are stale)
    type 4  $1c18   D0.b = side, D1.b = x, D2.b = y
    type 6  $3154   D0 = x, D1 = y (bytes, zero-extended), D3 = 2, D4 = $1a, D5.b = side   (then `$38ce` when `$3154` returns zero)
    type 8  $3154   D0 = x, D1 = y, D3 = 3, D4 = $1c, D5.b = side                           (then `$3248` when `$3154` returns zero)

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/wrapper_check.py [reuse]
"""
import os
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness

BASE = Path(WORK_REL) / "corpus" / "k5_8.snap"
OUT = WORK / "gw"
OUT.mkdir(exist_ok=True)
reuse = "reuse" in sys.argv
ram0 = (ROOT / BASE).with_suffix(".ram").read_bytes()
SIDE = 3
SLOT = 0x58016 + 6 * SIDE
GROUP = 0x51538 + SIDE * 0x13c + 0x4c
CALLEE = {2: 0x3888, 4: 0x1c18, 6: 0x3154, 8: 0x3154}
TAIL = {6: 0x38ce, 8: 0x3248}


def sx(b):
    return b - 256 if b >= 128 else b


def expect(T, x, y):
    if T == 2:
        return {"D0&ffff": sx(x) & 0xffff, "D1&ffff": sx(y) & 0xffff, "D6&ffff": 0xea}
    if T == 4:
        return {"D0&ff": SIDE, "D1&ff": x, "D2&ff": y}
    return {"D0": x, "D1": y, "D3&ffff": 2 if T == 6 else 3, "D4&ffff": 0x1a if T == 6 else 0x1c, "D5&ff": SIDE}


def case(c):
    T, x, y = c
    m = P.Mem(ram0)
    m.wb(SLOT + 1, T)
    m.wb(SLOT + 2, x)
    m.wb(SLOT + 3, y)
    m.wb(SLOT + 4, 2)
    m.ww(GROUP + 48, 0)                                    # no sender: the order runs at once
    pokes = Harness.bytepokes(ram0, {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]})
    res = {}
    for tgt in (CALLEE[T], TAIL.get(T)):
        if tgt is None:
            continue
        f = OUT / f"w_{T}_{x:02x}_{y:02x}_{tgt:x}.txt"
        if not (reuse and f.exists()):
            p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(BASE), "repl", "--disk-a", "scratchpad/powermonger.st"],
                               input="".join(f"w {a:x} {w:08x}\n" for a, w in pokes) + f"bp {tgt:x} 600000\nq\n", capture_output=True, text=True,
                               cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
            f.write_text(p.stdout + p.stderr)
        t = f.read_text()
        hit = f"breakpoint ${tgt:08x} hit" in t
        regs = {k: int(v, 16) for k, v in re.findall(r"\b([DA][0-7]):([0-9a-f]{8})", t.split("hit")[-1])} if hit else {}
        res[tgt] = (hit, regs)
    return c, res


def main():
    rng = random.Random(3)
    cases = [(T, rng.randrange(256), rng.randrange(256)) for T in (2, 4, 6, 8) for _ in range(8)]
    cases += [(2, 0x80, 0xff), (2, 0x7f, 0), (6, 0xff, 0xff), (8, 0, 0)]
    ok = n = 0
    tail_hit = tail_n = 0
    with ThreadPoolExecutor(4) as ex:
        for (T, x, y), res in ex.map(case, cases):
            hit, regs = res[CALLEE[T]]
            exp = expect(T, x, y)
            good = hit and all(((regs[k.split("&")[0]] & (0xffff if k.endswith("&ffff") else 0xff if k.endswith("&ff") else 0xffffffff)) == v)
                               for k, v in exp.items())
            n += 1
            ok += bool(good)
            if T in TAIL:
                tail_n += 1
                tail_hit += res[TAIL[T]][0]
            if not good:
                print("MISMATCH", T, x, y, hit, {k: hex(v) for k, v in regs.items() if k[0] == "D"})
    print(f"wrapper registers {ok}/{n}; `$3154` returned zero and the tail ($38ce/$3248) ran in {tail_hit}/{tail_n} cases")
    sys.exit(0 if ok == n else 1)


main()
