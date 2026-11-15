"""Populous II settlement land claim $25168 (state 6's per-tick call): callcap against a literal model.

Model (read from $25168, $251d8, $252d8, $25368, $253b8, $253e0; README "Settlement land claim"):
  $25168(A0 = settlement): the claim $251d8 runs when byte 1 (size) is 0, or (record index & 3) equals
    ($3979c & 3), or the settlement's own cell has shape & 7 == 0; otherwise D0 = byte 1 and nothing else.
    After the claim, a size D3 > 0 that differs from byte 1 is stored there. D0 = D3 is the return value;
    state 6 ($23580) turns a settlement with D0 <= 0 back into a walker.
  $251d8: own code D4 = $2f (side 1) / $3f (side 2). Rings of the offset list $2549a around the cell:
    the centre, then ring 1 (8) only if the centre counted, ring 2 (16) only if all 9 counted, ring 3
    (24) only if all 25 counted and $25368 finds every ring-3 cell usable; then the count is forced to 26.
    A cell counts when it is on the map, its shape word w = $3697a[code] has w & $17 != 0 and bit 4 clear,
    and no occupant has type $18. Every other type-4 occupant (another settlement) on a looked-at cell is
    demoted to a walker (type 2, state 2, word 10 = 0) after $253e0 clears its own land. The shape word of
    each on-map cell is stored at $25366; the enemy-land test reads its high byte (always 0), so enemy
    cells count. Counted cells not already coded D4 are pushed on the list at $254fe.
    size = $2547e[count]. If size < byte 1: own-coded cells of rings 2-3 (size < 9) or ring 3 go to $0f.
    Pushed cells get code D4 (popped, the list words stay). The 8 neighbours' bytes in the map $3d79e are
    set from $25562 + 8 * size.
  $253e0(A2 = settlement, D2 = $0f): over the first $2546a[size] + 1 offsets of $2549a, clear the
    $3d79e byte and set own-coded cells (shape bit 4 clear) to $0f.
Compared after each callcap: every RAM byte except the dead stack below the entry SP, and D0.w.

usage: uv run python reversing/populous2/py/claim/claim_gate.py [natural|poked|all] [stride]
  (poked variants on every stride-th natural state, default 4; the gate uses `all 16`)
Corpus: tools/capture_hits.py on p2_game_60m and p2_game_start, $25168, into scratchpad/populous2/claim/
(see py/README.md, claim/capture.sh).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(__file__)
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

C, SHAPE, ENT, BLD = 0x3979E, 0x3697A, 0x3FF1A, 0x3D79E
RINGS, R23, R3, NB, PUSH = 0x2549A, 0x254AC, 0x254CC, 0x25640, 0x254FE
DLL = os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll")
CORPUS = os.path.join(ROOT, "scratchpad/populous2/claim")
WORK = os.path.join(CORPUS, "work")


def w16(m, a):
    return (m[a] << 8) | m[a + 1]


def p16(m, a, v):
    m[a], m[a + 1] = (v >> 8) & 0xFF, v & 0xFF


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def sb(v):
    return v - 0x100 if v & 0x80 else v


def cell(off, pos):
    """offset word + position word ($yyxx) -> cell byte offset y*256 + x*4, or None off the map."""
    d1 = (off + pos) & 0xFFFF
    if d1 & 0xC0C0:
        return None
    return (d1 & 0xFF00) | ((d1 << 2) & 0xFF)


def pos_of(m, a):
    return (m[a + 8] << 8) | m[a + 6]


class Model:
    def __init__(self, m, **k):
        self.m = m
        self.k = k

    def clear_land(self, a2, d2=0x0F):  # $253e0
        m = self.m
        d4 = 0x2F if m[a2 + 12] == 1 else 0x3F
        n = m[0x2546A + m[a2 + 1]] + 1
        pos = pos_of(m, a2)
        p = RINGS
        for _ in range(n):
            off = w16(m, p)
            p += 2
            if off == 0xFF9D:
                break
            i = cell(off, pos)
            if i is None:
                continue
            m[BLD + (i >> 2)] = 0
            code = m[C + i + 1]
            if code == d4 and not (m[SHAPE + 2 * code + 1] & 0x10):
                m[C + i + 1] = d2

    def count(self, n, a0, pos):  # $252d8
        m = self.m
        for _ in range(n):
            off = w16(m, self.a3)
            self.a3 += 2
            i = cell(off, pos)
            if i is None:
                continue
            code = m[C + i + 1]
            sh = w16(m, SHAPE + 2 * code)
            p16(m, 0x25366, sh)
            if not (sh & 0x17) or sh & 0x10:
                continue
            d0 = w16(m, C + i + 2)
            blocked = False
            while d0:
                a1 = ENT + s16(d0)
                if m[a1] == 4 and a1 != a0 and not self.k.get("no_demote"):
                    self.clear_land(a1)
                    m[a1], m[a1 + 22] = 2, 2
                    p16(m, a1 + 10, 0)
                if a1 != a0 and m[a1] == 0x18:
                    blocked = True
                    break
                d0 = w16(m, a1 + 2)
            if blocked:
                continue
            enemy = 0x3F if self.d4 == 0x2F else 0x2F
            if self.k.get("enemy_excluded") and code == enemy:
                continue
            if code != self.d4:
                p16(m, self.a6, i)
                self.a6 += 2
            self.d3 += 1

    def ring3_ok(self, pos):  # $25368
        m = self.m
        p = self.a3
        while True:
            off = w16(m, p)
            p += 2
            if off == 0xFF9D:
                return True
            i = cell(off, pos)
            if i is None:
                return False
            sh = w16(m, SHAPE + ((2 * m[C + i + 1]) & 0xFF))
            if not (sh & 0x17) or sh & 0x10:
                return False
            d0 = w16(m, C + i + 2)
            while d0:
                a1 = ENT + s16(d0)
                if m[a1] == 0x18:
                    return False
                d0 = w16(m, a1 + 2)

    def claim(self, a0):  # $251d8
        m = self.m
        self.d4 = 0x2F if m[a0 + 12] == 1 else 0x3F
        self.a3, self.a6, self.d3 = RINGS, PUSH, 0
        pos = pos_of(m, a0)
        self.count(1, a0, pos)
        if self.d3 == 0:
            return 0
        self.count(8, a0, pos)
        if self.d3 >= 9:
            self.count(16, a0, pos)
            if self.d3 >= 25 and not self.k.get("no_ring3"):
                if self.ring3_ok(pos):
                    self.count(24, a0, pos)
                    self.d3 = 26
        size = m[0x2547E + self.d3]
        if sb(size) < sb(m[a0 + 1]) and not self.k.get("no_shrink"):
            lst, n = (R23, 40) if size < 9 else (R3, 24)
            for j in range(n):
                i = cell(w16(m, lst + 2 * j), pos)
                if i is not None and m[C + i + 1] == self.d4:
                    m[C + i + 1] = 0x0F
        while self.a6 != PUSH:
            self.a6 -= 2
            m[C + w16(m, self.a6) + 1] = self.d4
        pat = 0x25562 + size * 8
        for j in range(8):
            v = m[pat + j]
            i = cell(w16(m, NB + 2 * j), pos)
            if i is not None:
                m[BLD + (i >> 2)] = v
        return size

    def run(self, a0):  # $25168
        m = self.m
        b1 = m[a0 + 1]
        go = (b1 == 0 or ((a0 - ENT) // 0x34) & 3 == w16(m, 0x3979C) & 3
              or not (w16(m, SHAPE + 2 * m[C + (pos_of(m, a0) & 0xFF00) + ((m[a0 + 6] * 4) & 0xFF) + 1]) & 7))
        if self.k.get("always"):
            go = True
        if not go:
            return b1
        d3 = self.claim(a0)
        if 0 < sb(d3) and d3 != m[a0 + 1]:
            m[a0 + 1] = d3
        return d3


CONTROLS = {
    "enemy cells excluded": {"enemy_excluded": True},
    "no demote": {"no_demote": True},
    "no shrink reset": {"no_shrink": True},
    "no ring 3": {"no_ring3": True},
    "claim every call": {"always": True},
}


def natural_cases():
    out = []
    for js in (os.path.join(CORPUS, f"game_{a}.json") for a in ("60m", "start")):
        for e in json.load(open(js)):
            out.append((os.path.basename(e["snap"]), e["snap"], e["regs"]["A0"], [], "natural"))
    return out


def poked_cases(nat, stride=4):
    """Variants on natural states where the claim ran, each aimed at a branch the natural run leaves unused."""
    out = []
    for name, snap, a0, _, _ in nat[::stride]:
        m, _ = load_ram(snap)
        x, y = m[a0 + 6], m[a0 + 8]
        ph = w16(m, 0x3979C) & 3
        idx = ((a0 - ENT) // 0x34) & 3
        tick = [("ww", 0x3979C, (w16(m, 0x3979C) & ~3 & 0xFFFF) | idx)] if ph != idx else []
        def flat_at(cx, cy, own=False):
            return [("wb", C + 4 * ((cy + dy) * 64 + cx + dx) + 1, 0x0F)
                    for dy in range(-3, 4) for dx in range(-3, 4)
                    if 0 <= cx + dx < 64 and 0 <= cy + dy < 64 and (own or dx or dy)]
        flat = flat_at(x, y)
        enemy = 0x3F if m[a0 + 12] == 1 else 0x2F
        e1 = [("wb", C + 4 * ((y + dy) * 64 + x + dx) + 1, enemy) for dx, dy in ((1, 0), (0, 1), (-1, -1))
              if 0 <= x + dx < 64 and 0 <= y + dy < 64]
        out.append((name, snap, a0, tick + [("wb", a0 + 1, 0x11)], "shrink: size $11"))
        out.append((name, snap, a0, tick + [("wb", a0 + 1, 0x05)], "shrink: size 5"))
        out.append((name, snap, a0, tick + flat, "7x7 flat: ring 3"))
        out.append((name, snap, a0, tick + flat + [("wb", a0 + 1, 0x12)], "7x7 flat, size $12"))
        out.append((name, snap, a0, tick + e1, "enemy code on 3 neighbours"))
        out.append((name, snap, a0, [("wb", C + 4 * (y * 64 + x) + 1, 0x00)], "own cell sea, any phase"))
        # the settlement moved (not relinked: the claim never looks for itself in a list) onto a flat patch at
        # an edge or corner, so the off-map tests run inside the rings, $25368 and the shrink list
        for cx, cy, where in ((0, 63, "corner (0,63)"), (63, 0, "corner (63,0)"), (63, 20, "edge x=63"), (1, 1, "near corner (1,1)")):
            mv = [("wb", a0 + 6, cx), ("wb", a0 + 8, cy)]
            out.append((name, snap, a0, tick + mv + flat_at(cx, cy, own=True), f"moved to {where}, flat"))
            out.append((name, snap, a0, tick + mv + flat_at(cx, cy, own=True) + [("wb", a0 + 1, 0x12)], f"moved to {where}, flat, size $12"))
        out.append((name, snap, a0, tick + [("wb", a0 + 1, 0)], "size 0, any phase" if not tick else "size 0"))
        # the first two occupants (not this settlement) within 3 cells, by ring: retyped as another settlement,
        # then as a type-$18 blocker
        near = sorted(((max(abs(dx), abs(dy)), dy, dx) for dy in range(-3, 4) for dx in range(-3, 4)
                       if (dx or dy) and 0 <= x + dx < 64 and 0 <= y + dy < 64))
        found = []
        for _r, dy, dx in near:
            occ = w16(m, C + 4 * ((y + dy) * 64 + x + dx) + 2)
            if occ and ENT + s16(occ) != a0:
                found.append(ENT + s16(occ))
            if len(found) == 2:
                break
        for k, a1 in enumerate(found):
            out.append((name, snap, a0, tick + flat + [("wb", a1, 4), ("wb", a1 + 1, 6)], "neighbour retyped settlement"))
            out.append((name, snap, a0, tick + flat + [("wb", a1, 0x18)], "neighbour retyped $18"))
    return out


def run_case(i, snap, a0, pokes):
    js = os.path.join(WORK, f"c{i}.json")
    script = "".join(f"{op} {a:x} {v:x}\n" for op, a, v in pokes)
    script += f"callcap 25168 2000000 {js}\nq\n"
    r = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl"], input=script, capture_output=True, text=True, cwd=ROOT)
    if "--- callcap $025168: returned" not in r.stdout:
        sys.exit(f"case {i}: callcap did not return\n{r.stdout[-1500:]}{r.stderr[-500:]}")
    cap = json.load(open(js))
    os.remove(js)
    return cap


def apply(m, pokes):
    for op, a, v in pokes:
        if op == "wb":
            m[a] = v
        else:
            p16(m, a, v)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    stride = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    os.makedirs(WORK, exist_ok=True)
    nat = natural_cases()
    cases = (nat if which in ("natural", "all") else []) + (poked_cases(nat, stride) if which in ("poked", "all") else [])
    stats, ctl, sizes = {}, {k: {} for k in CONTROLS}, {}
    for i, (name, snap, a0, pokes, label) in enumerate(cases):
        cap = run_case(i, snap, a0, pokes)
        base, _ = load_ram(snap)
        base = bytearray(base)
        apply(base, pokes)
        sp = cap["entrySP"] & 0xFFFFFF
        emu = bytearray(base)
        for a, _o, v in cap["mem"]:
            emu[a] = v
        ed0 = cap["regN"][0] & 0xFFFF
        keep = lambda a: not (sp - 0x400 <= a < sp)  # noqa: E731
        m = bytearray(base)
        d0 = Model(m).run(a0)
        bad = [a for a in range(len(m)) if m[a] != emu[a] and keep(a)]
        ok = not bad and ed0 == (d0 & 0xFFFF)
        changed = sum(1 for a in range(len(m)) if emu[a] != base[a] and keep(a))
        st = stats.setdefault(label, [0, 0, 0])
        st[0] += ok
        st[1] += 1
        st[2] += changed > 0
        sizes.setdefault(label, set()).add(d0)
        if not ok:
            print(f"case {i} {name} {label}: {len(bad)} bytes differ {[hex(a) for a in bad[:8]]}, D0 emu {ed0} model {d0}")
        for cn, kw in CONTROLS.items():
            cm = bytearray(base)
            cd0 = Model(cm, **kw).run(a0)
            c = ctl[cn].setdefault(label, [0, 0])
            c[0] += all(cm[a] == emu[a] for a in range(len(m)) if keep(a)) and ed0 == (cd0 & 0xFFFF)
            c[1] += 1
    tot = sum(v[0] for v in stats.values())
    n = sum(v[1] for v in stats.values())
    for label, (ok, k, ch) in stats.items():
        print(f"{label}: model == emulator {ok}/{k} (RAM changed in {ch}; sizes returned {sorted(sizes[label])})")
    print(f"TOTAL {tot}/{n} cases, RAM and D0.w equal except the dead stack")
    for cn in CONTROLS:
        cok = sum(v[0] for v in ctl[cn].values())
        print(f"control '{cn}': equal in {cok}/{n}")


if __name__ == "__main__":
    main()
