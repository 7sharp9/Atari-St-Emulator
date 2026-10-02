"""141st: the order executor's routing, live.  `$6a3a` -> `$6ac6` -> (`$6b38` | `$4562`) -> the handler of the type's table entry.

For each case a slot (slot 3, side 3, state 2 so `$6522` leaves it alone) gets an order type T and a parameter, the sender word 48
of the side's group and the word `$51b5a` are poked, and the REPL counts the executions (`hits`) of `$6ac6`, `$6b38`, `$4562`, `$6b2e`
and the 27 handler entry points of the table `$6b5a` over 600000 steps (about four ticks; the order is consumed by the first).  The route
the model `cmdai_ref.call_6ac6` predicts, and the handler the table `$6b5a` (read from RAM) names, are compared with the counts.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/exec_census.py [reuse]
"""
import os
import re
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
import cmdai_ref as C
import pm_fsm_ref as P
from pm_fsm_diff import Harness

BASE = Path(WORK_REL) / "corpus" / "k5_8.snap"
OUT = Path(WORK_REL) / "g"
reuse = "reuse" in sys.argv
ram0 = (ROOT / BASE).with_suffix(".ram").read_bytes()
P.init_tables(ram0)
TABLE = [0x6b5a + struct.unpack_from(">H", ram0, 0x6b5a + t)[0] for t in range(0, 0x34, 2)]
SIDE = 3
SLOT = C.CMD + 6 * SIDE
GROUP = C.GROUPS + SIDE * 0x13c + 0x4c                  # group 0 of side 3 (the `$58042` entry)
ADDRS = sorted(set(TABLE)) + [0x6ac6, 0x6b38, 0x4562, 0x6b2e, 0x6b32]


def men(m):
    return [P.OBJ + s * 50 for s in range(1, 512) if m.bu(P.OBJ + s * 50 + 6) == 0 and 0 < m.bu(P.OBJ + s * 50 + 5) < 128]


def build(T, mode):
    m = P.Mem(ram0)
    m.wb(SLOT + 1, T)
    m.ww(SLOT + 2, 0x1a2b)
    m.wb(SLOT + 4, 2)
    sender = [a for a in men(m) if m.bu(a + 5) == SIDE][0]
    if mode == "none":
        m.ww(GROUP + 48, 0)
    elif mode == "pigeon":
        m.ww(GROUP + 48, (sender - P.OBJ) & 0xffff)
    elif mode == "same":                                 # `$51b5a` names the sender itself: its cell equals its own
        m.ww(GROUP + 48, (sender - P.OBJ) & 0xffff)
        m.ww(P.OBJ - 12, (sender - P.OBJ) & 0xffff)
    elif mode == "noxref":
        m.ww(C.GROUP_XREF + 2 * SIDE, 0)
    pairs = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]}
    return Harness.bytepokes(ram0, pairs), bytes(m.r)


def predict(ram1):
    m = P.Mem(ram1)
    seen = []
    route = C.call_6ac6(m, SLOT, lambda mm, a0, d2: seen.append("6b38"))
    return route, seen


def run_case(case):
    T, mode = case
    pokes, ram1 = build(T, mode)
    out = ROOT / OUT / f"x_{T:02x}_{mode}.txt"
    if not (reuse and out.exists()):
        cmds = "".join(f"w {a:x} {w:08x}\n" for a, w in pokes) + f"hits 600000 {' '.join(f'{a:x}' for a in ADDRS)}\nq\n"
        p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(BASE), "repl", "--disk-a", "scratchpad/powermonger.st"],
                           input=cmds, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
        out.write_text(p.stdout + p.stderr)
    txt = out.read_text()
    cnt = {int(a, 16): int(n) for a, n in re.findall(r"\$([0-9a-f]{6})\s+(\d+)\s+first", txt)}
    if not cnt:
        # the handler of this type runs wild with the poked parameter (the emulator stops with an exception and `hits` prints nothing):
        # stop at the first entry of `$6b38` and of the handler instead (`bp` reports before the crash)
        cnt = {}
        for a in (0x6ac6, 0x6b38, 0x4562, TABLE[T // 2] if T < 0x34 else 0x6eb0):
            pk = Path(f"{out}.{a:x}.txt")
            if not (reuse and pk.exists()):
                p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(BASE), "repl", "--disk-a", "scratchpad/powermonger.st"],
                                   input="".join(f"w {x:x} {w:08x}\n" for x, w in pokes) + f"bp {a:x} 600000\nq\n", capture_output=True, text=True,
                                   cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
                pk.write_text(p.stdout + p.stderr)
            if f"breakpoint ${a:08x} hit" in pk.read_text():
                cnt[a] = 1                                   # reached (a count of 1 means "at least once")
    return case, ram1, cnt


def main():
    cases = [(T, "none") for T in range(0, 0x38, 2)]
    cases += [(T, md) for T in (2, 6, 0xc, 0x10, 0x16) for md in ("pigeon", "same")]
    cases += [(T, "noxref") for T in (2, 0xc)] + [(0x22, "pigeon"), (0x32, "pigeon"), (0x34, "pigeon"), (0x40, "pigeon")]
    ok = n = 0
    handler_ok = handler_n = 0
    with ThreadPoolExecutor(4) as ex:
        for (T, mode), ram1, cnt in ex.map(run_case, cases):
            route, seen = predict(ram1)
            exp = {0x6b38: len(seen), 0x4562: 1 if route == "pigeon" else 0}
            got = {a: cnt.get(a, 0) for a in (0x6ac6, 0x6b38, 0x4562)}
            # other slots may execute natural orders: the counts are of the poked slot's single order plus any natural one; report both
            good = got[0x6b38] == exp[0x6b38] and got[0x4562] == exp[0x4562]
            n += 1
            ok += good
            hand = ""
            if route.startswith("exec") and T < 0x34:
                handler_n += 1
                h = TABLE[T // 2]
                hit = cnt.get(h, 0)
                others = sorted(a for a in set(TABLE) if a not in (h, 0x6eb0) and cnt.get(a, 0))   # $6eb0 (type 0's entry) is also the common tail of $6d90..$6e56
                hand = f" handler ${h:x} hits {hit} others {[hex(a) for a in others]}"
                handler_ok += (hit == 1 and not others)
            print(f"T={T:02x} {mode:7s} model {route:15s} 6ac6 {got[0x6ac6]} 6b38 {got[0x6b38]} (exp {exp[0x6b38]}) 4562 {got[0x4562]} (exp {exp[0x4562]})"
                  f"{'' if good else '  MISMATCH'}{hand}")
    print(f"routing {ok}/{n}, handler {handler_ok}/{handler_n}")


main()
