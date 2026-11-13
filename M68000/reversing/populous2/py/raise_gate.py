"""Populous II raise/lower: the command path under callcap against a Python model.

For each corner of a corpus, the side's command record ($473b0 + 10*(side-1): +1 command, +2 x,
+3 y) is poked with command 2 (raise) or 4 (lower) and the command handler $292dc is callcapped
with A0 at the record. The corner grid after the call (read off the cells as in corners.py) is
compared with the model:

  raise_point(x, y):   (counts one call in $39788)
      reject if (x, y) is outside 0..64; h = corner; stop if h == 8
      for each neighbour in the order N, NE, E, SE, S, SW, W, NW (inside 0..64):
          if neighbour < h: raise_point(neighbour)      (h+1 - neighbour > 1)
      corner = h + 1                                     (written after the recursion)
  lower_point mirrors it: stop if h == 0, recurse where neighbour > h, corner = h - 1.

Lower on a cell (x, y) that holds a settled entity (type 4) of the commanding side is redirected
($24de0): no corner changes, bit 2 of that entity's byte +13 is set, and the charge is 20 x the
stale corner count left in $3962c by the previous terrain command.

Also checked on every call: every cell re-derives from the new corner grid by Populous 1's rule
without the shore codes (settlement codes $2f/$3f excluded, as in corners.py), and the side's mana (long +0 of
$46fc4 + side*$13a) is printed against the model's call count.

Control: the same comparison against a model that only moves the clicked corner.

usage: uv run python reversing/populous2/py/raise_gate.py <snap> [n] [--show]
"""
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from corners import ROOT, corner_grid, derive_check  # noqa: E402

REC = 0x473B0
SIDE_REC = 0x46FC4
ORDER = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def model(H, x, y, up):
    H = dict(H)
    calls = [0]

    def rec(x, y):
        calls[0] += 1
        if not (0 <= x <= 64 and 0 <= y <= 64):
            return
        h = H[x, y]
        if (up and h == 8) or (not up and h == 0):
            return
        for dx, dy in ORDER:
            nx, ny = x + dx, y + dy
            if 0 <= nx <= 64 and 0 <= ny <= 64:
                n = H[nx, ny]
                if (up and n < h) or (not up and n > h):
                    rec(nx, ny)
        H[x, y] = h + 1 if up else h - 1

    rec(x, y)
    return H, calls[0]


def own_settlement(ram, side, x, y):
    if not (0 <= x < 64 and 0 <= y < 64):
        return None
    node = int.from_bytes(ram[0x3979E + (y * 64 + x) * 4 + 2:][:2], "big")
    while node:
        r = 0x3FF1A + (node - 0x10000 if node & 0x8000 else node)
        if ram[r] == 4 and ram[r + 12] == side:
            return r
        node = int.from_bytes(ram[r + 2:r + 4], "big")
    return None


def apply_delta(ram, mem):
    ram = bytearray(ram)
    for a, _old, new in mem:
        ram[a] = new
    return bytes(ram)


def run(snap, cases, outdir):
    os.makedirs(outdir, exist_ok=True)
    script = []
    for i, (side, cmd, x, y) in enumerate(cases):
        r = REC + 10 * (side - 1)
        script += [f"wb {r + 1:x} {cmd:02x}", f"wb {r + 2:x} {x:02x}", f"wb {r + 3:x} {y:02x}",
                   f"callcap 292dc 4000000 {outdir}/c{i}.json A0={r:x}"]
    # callcap restores the state, but the pokes stay: clear them after each case
        script += [f"wb {r + 1:x} 00", f"wb {r + 2:x} 00", f"wb {r + 3:x} 00"]
    dll = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
    out = subprocess.run(["dotnet", "exec", dll, "resume", snap, "repl"],
                         input="\n".join(script) + "\nq\n", capture_output=True, text=True, cwd=ROOT)
    n = out.stdout.count("--- callcap $0292dc: returned")
    if n != len(cases):
        sys.exit(f"expected {len(cases)} returned callcaps, got {n}:\n{out.stdout[-1500:]}{out.stderr[-1500:]}")
    return [json.load(open(os.path.join(ROOT, outdir, f"c{i}.json"))) for i in range(len(cases))]


def m0_m1(ram0, ram1, side):
    a = SIDE_REC + side * 0x13A
    return int.from_bytes(ram0[a:a + 4], "big") - int.from_bytes(ram1[a:a + 4], "big")


def main():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from gfxview import load_ram
    snap = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 40
    ram0, _ = load_ram(snap)
    H0, dis, _ = corner_grid(ram0)
    assert dis == 0, f"start grid has {dis} disagreeing corners"
    random.seed(7)
    land = [k for k, v in H0.items() if v]
    sea = [k for k, v in H0.items() if not v]
    pts = random.sample(land, n // 2) + random.sample(sea, n // 4)
    pts += [(0, 0), (64, 64), (64, 10), (10, 0)]
    pts += [max(land, key=lambda k: H0[k])]
    cases = [(side, cmd, x, y) for (x, y) in pts for side, cmd in ((1, 2), (1, 4))]
    cases += [(2, 2, x, y) for (x, y) in pts[:6]]
    caps = run(snap, cases, "scratchpad/populous2/raise/gate")
    good = ctl = derive_ok = mana_ok = 0
    changed_total = 0
    rows = []
    for (side, cmd, x, y), cap in zip(cases, caps):
        ram1 = apply_delta(ram0, cap["mem"])
        H1, dis1, cell1 = corner_grid(ram1)
        own = own_settlement(ram0, side, x, y) if cmd == 4 else None
        if own is not None:
            Hm, calls = dict(H0), 0
        else:
            Hm, calls = model(H0, x, y, cmd == 2)
        Hc = dict(H0)
        if 0 <= x <= 64 and 0 <= y <= 64:
            Hc[x, y] = min(8, H0[x, y] + 1) if cmd == 2 else max(0, H0[x, y] - 1)
        changed = sum(H1[k] != H0[k] for k in H0)
        changed_total += changed
        stale = int.from_bytes(ram0[0x3962C:0x3962E], "big")
        spent_model = 20 * (stale if own is not None else sum(Hm[k] != H0[k] for k in H0))
        flag_ok = own is None or (ram1[own + 13] & 4 and not ram0[own + 13] & 4)
        good += Hm == H1 and dis1 == 0 and flag_ok
        mana_ok += spent_model == m0_m1(ram0, ram1, side)
        ctl += Hc == H1
        ok, tot = derive_check(H1, cell1, shore=False)
        derive_ok += ok == tot
        a = SIDE_REC + side * 0x13A
        m0 = int.from_bytes(ram0[a:a + 4], "big")
        m1 = int.from_bytes(ram1[a:a + 4], "big")
        cnt = int.from_bytes(ram1[0x39788:0x3978a], "big") - int.from_bytes(ram0[0x39788:0x3978a], "big")
        c62 = int.from_bytes(ram1[0x3962C:0x3962E], "big")
        rows.append((side, cmd, x, y, H0[x, y] if (x, y) in H0 else None, changed,
                     sum(Hm[k] != H0[k] for k in H0), calls, cnt & 0xFFFF, c62, m0 - m1,
                     Hm == H1, dis1, ok, tot))
    print(f"cases {len(cases)}: corner grid equal to the model {good}/{len(cases)} "
          f"(control: clicked corner only {ctl}/{len(cases)}); corners changed in all {changed_total}")
    print(f"mana charged = 20 x corners changed (20 x stale $3962c when redirected): {mana_ok}/{len(cases)}")
    print(f"cells re-derive from the new grid ($2f/$3f excluded) in {derive_ok}/{len(cases)} cases")
    if "--show" in sys.argv or good != len(cases):
        print("side cmd x y h0 changed model_changed model_calls $39788+ $3962c mana_spent match disagree derive")
        for r in rows:
            print(*r)


if __name__ == "__main__":
    main()
