"""Populous II people placement $22986 (last pass of build_world $22942): callcap against a literal model.

Model (read from $22986, $25e5e, $22acc, $22b0c, $243f6, $25dcc):
  for side s = 1 (record $470fe) then 2 (record $47238); S = $46fc4 + s*$13a:
    (x,y) = (32,32), or (byte 110(S), byte 111(S)) when the word 110(S) is not negative
    place_flag $25e5e(x,y,s): the 14-byte record at $46f9a + 14*s becomes type $14, side s, cell (x,y)
        centred ($80 sub-cell bytes), frame word $0a88 (side 1) / $0a90 (side 2), linked at the head of
        the cell's occupant list; word 10(S) = its offset from $3ff1a
    word 22(S) = word 100(S); word 2(S) = word 98(S); word $47386 / $47388 = word 102(S)
    n = word 90(S) walkers; if n != 0 scan the cell map:
        side 1: cells 1, 2, ... (raster, first to last); side 2: cells 4095, 4094, ... (last to first)
        pass 1 takes a cell when bit 0 of the shape word $3697a[b1] is set; if n walkers are not
        placed, pass 2 rescans the same direction taking every cell with b1 != 0 (a cell taken in pass
        1 is taken again: no occupancy test anywhere)
        spawn $22b0c: first record of the 399 52-byte entities $3ff4e..$4505a with byte 12 = 0
          (none: A3 is left at $4505a and the caller carries on with it), type 2, side, x,y of the cell,
          $80 sub-cell bytes, byte 24 = 2, 22 = 2, 23 = 2, 18 = 95(S), 25 = 97(S), word 28 = 92(S),
          word 50 = ((rec - $3ff1a)/52) & $e; linked at the head of the cell's list ($243f6)
        first walker of the side (counter 0): when s == word $4739c the scroll bytes $3e79f/$3e7a1
          = x-4, y-4; when word 110(S) is negative the walker is the side's leader ($25dcc): word 8(S)
          = its offset and bit 0 of its byte 13 is set
Compared after each callcap: every byte of RAM except the dead stack below SP ($12000..$12600).
Controls: broken models listed in CONTROLS.

usage: uv run python reversing/populous2/py/people/people_gate.py [n]
"""
import json
import os
import random
import subprocess
import sys

ROOT = os.path.abspath(__file__)
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

CELLS, ENT0, ENTEND, ENTBASE = 0x3979E, 0x3FF4E, 0x4505A, 0x3FF1A
DLL = os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll")
ENTRY = os.path.join(ROOT, "scratchpad/populous2/anchors/p2_gen_entry.snap")
WORK = os.path.join(ROOT, "scratchpad/populous2/people")  # per-case snapshots and callcaps, deleted after each case


def w16(m, a):
    return (m[a] << 8) | m[a + 1]


def p16(m, a, v):
    m[a] = (v >> 8) & 0xFF
    m[a + 1] = v & 0xFF


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def link_object(m, a3):
    m[a3 + 2:a3 + 6] = b"\0\0\0\0"
    d0 = (m[a3 + 8] << 8) | m[a3 + 6]
    d0 = (d0 & 0xFF00) | ((m[a3 + 6] * 4) & 0xFF)
    a2 = CELLS + d0
    me = (a3 - ENTBASE) & 0xFFFF
    head = w16(m, a2 + 2)
    if head:
        p16(m, a3 + 2, head)
        p16(m, ENTBASE + s16(head) + 4, me)
    p16(m, a2 + 2, me)


def place_flag(m, x, y, side, **k):
    a1 = 0x46FC4 + side * 0x13A
    a0 = 0x46F9A + side * 14
    p16(m, a1 + 10, (a0 - ENTBASE) & 0xFFFF)
    m[a0 + 6], m[a0 + 8], m[a0 + 7], m[a0 + 9] = x, y, 0x80, 0x80
    m[a0] = 0x14
    m[a0 + 12] = side
    p16(m, a0 + 10, {1: 0x0A88, 2: 0x0A90}[side] if not k.get("badframe") else 0x0A88)
    link_object(m, a0)


def spawn(m, off, side, a1):
    a3 = ENT0
    while m[a3 + 12]:
        a3 += 52
        if a3 >= ENTEND:
            return ENTEND
    m[a3] = 2
    m[a3 + 12] = side
    p16(m, a3 + 50, (((a3 - ENTBASE) // 52) & 0xE))
    m[a3 + 6] = (off & 0xFF) >> 2
    m[a3 + 7] = 0x80
    m[a3 + 8] = (off >> 8) & 0xFF
    m[a3 + 9] = 0x80
    p16(m, a3 + 10, 0)
    m[a3 + 13] = 0
    m[a3 + 14:a3 + 18] = b"\0\0\0\0"
    m[a3 + 24] = 2
    m[a3 + 18] = m[a1 + 95]
    m[a3 + 25] = m[a1 + 97]
    p16(m, a3 + 28, w16(m, a1 + 92))
    m[a3 + 22] = 2
    m[a3 + 23] = 2
    link_object(m, a3)
    return a3


def place(m, order="fwd", **k):
    """order: 'fwd' = $22986's own (side 1 forward, side 2 backward); controls change it."""
    m = bytearray(m)
    local = w16(m, 0x4739C)
    for side in (1, 2):
        a1 = 0x46FC4 + side * 0x13A
        x, y = 0x20, 0x20
        if not (w16(m, a1 + 110) & 0x8000):
            x, y = m[a1 + 110], m[a1 + 111]
        if not k.get("noflag"):
            place_flag(m, x, y, side, **k)
        p16(m, a1 + 22, w16(m, a1 + 100))
        p16(m, a1 + 2, w16(m, a1 + 98))
        p16(m, 0x47386 if side == 1 else 0x47388, w16(m, a1 + 102))
        n = w16(m, a1 + 90)
        if n == 0:
            continue
        step = 4 if (side == 1) != bool(k.get("reverse")) else -4
        start = CELLS if step == 4 else CELLS + 0x4000
        done = [0]
        a3box = [0]

        def take(a0):
            a3 = spawn(m, a0 - CELLS, side, a1)
            if done[0] == 0:
                if side == local and not k.get("noscroll"):
                    m[0x3E79F] = (m[a3 + 6] - 4) & 0xFF
                    m[0x3E7A1] = (m[a3 + 8] - 4) & 0xFF
                if w16(m, a1 + 110) & 0x8000 and not k.get("noleader"):
                    p16(m, a1 + 8, (a3 - ENTBASE) & 0xFFFF)
                    m[a3 + 13] |= 1
            done[0] += 1
            return done[0] == n

        fin = False
        a0 = start
        while not fin:
            a0 += step
            if not (CELLS <= a0 < CELLS + 0x4000):
                break
            b1 = m[a0 + 1]
            if k.get("nobit0") or (w16(m, 0x3697A + 2 * b1) & 1):
                fin = take(a0)
        if not fin and not k.get("nopass2"):
            a0 = start
            while True:
                a0 += step
                if not (CELLS <= a0 < CELLS + 0x4000):
                    break
                if m[a0 + 1] == 0:
                    continue
                if take(a0):
                    break
    return m


CONTROLS = {
    "side 2 scans forward": dict(reverse=True),
    "no shape bit 0 test": dict(nobit0=True),
    "no second pass": dict(nopass2=True),
    "no leader pointer": dict(noleader=True),
    "no scroll bytes": dict(noscroll=True),
    "no flag record": dict(noflag=True),
    "side 2 flag frame $0a88": dict(badframe=True),
}


def cases(n):
    random.seed(22986)
    seed0 = None
    out = []
    # natural pokes-free seeds
    seeds = [None, 0, 1, 0xFFFFFFFF] + [random.getrandbits(32) for _ in range(n - 4)]
    for s in seeds:
        out.append(("seed", s, []))
    # poked variants on top of three seeds: each exercises a branch the natural build leaves unused
    for s in seeds[:3] + seeds[4:7]:
        S1, S2 = 0x470FE, 0x47238
        out += [
            ("pos110 side1+2 positive, count 40", s, [("ww", S1 + 110, 0x0A0C), ("ww", S2 + 110, 0x3030), ("ww", S1 + 90, 40), ("ww", S2 + 90, 40)]),
            ("count 3000 (pass 2 exhausts the map)", s, [("ww", S1 + 90, 3000), ("ww", S2 + 90, 3000)]),
            ("count 0 side 2", s, [("ww", S2 + 90, 0)]),
            ("count 399 (entity array nearly full), side 2 local", s, [("ww", S1 + 90, 399), ("ww", S2 + 90, 5), ("ww", 0x4739C, 2)]),
            ("count 450 (entity array runs out)", s, [("ww", S1 + 90, 450), ("ww", S2 + 90, 450)]),
            ("pos110 side 1 only, new body bytes", s, [("ww", S1 + 110, 0x1F05), ("wb", S1 + 95, 0x5A), ("wb", S1 + 97, 0xA5), ("ww", S1 + 92, 0x1234), ("ww", S1 + 98, 0x7777), ("ww", S1 + 100, 0x8888), ("ww", S1 + 102, 0x9999)]),
        ]
    return out


def run_case(i, seed, pokes):
    snap = os.path.join(WORK, f"c{i}.snap")
    js = os.path.join(WORK, f"c{i}.json")
    pre = "" if seed is None else f"w 47382 {seed:08x}\n"
    script = pre + "u 2295a 50000000\n" + "".join(f"{op} {a:x} {v:x}\n" for op, a, v in pokes)
    script += f"snap {snap}\ncallcap 22986 20000000 {js}\nq\n"
    r = subprocess.run(["dotnet", "exec", DLL, "resume", ENTRY, "repl"], input=script, capture_output=True, text=True, cwd=ROOT)
    if "--- callcap $022986: returned" not in r.stdout:
        sys.exit(f"case {i}: callcap did not return\n{r.stdout[-1200:]}{r.stderr[-500:]}")
    ram, _ = load_ram(snap)
    cap = json.load(open(js))
    for f in (snap, snap + ".prov.json", js):
        os.remove(f)
    return bytearray(ram), cap


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
    os.makedirs(WORK, exist_ok=True)
    cs = cases(n)
    stats = {}
    ctl = {k: {} for k in CONTROLS}
    for i, (label, seed, pokes) in enumerate(cs):
        ram, cap = run_case(i, seed, pokes)
        emu = bytearray(ram)
        for a, _o, v in cap["mem"]:
            emu[a] = v
        mod = place(ram)
        bad = [a for a in range(len(ram)) if mod[a] != emu[a] and not 0x12000 <= a < 0x12600]
        ok = not bad
        placed = sum(1 for a in range(ENT0, ENTEND, 52) if emu[a + 12] and not ram[a + 12])
        key = label if label != "seed" else "natural/random seed"
        st = stats.setdefault(key, [0, 0, []])
        st[0] += ok
        st[1] += 1
        st[2].append(placed)
        if not ok:
            print(f"case {i} {label} seed {seed}: {len(bad)} bytes differ, first {[hex(a) for a in bad[:8]]}")
        for cn, kw in CONTROLS.items():
            cm = place(ram, **kw)
            c = ctl[cn].setdefault(key, [0, 0])
            c[0] += all(cm[a] == emu[a] for a in range(len(ram)) if not 0x12000 <= a < 0x12600)
            c[1] += 1
    tot_ok = sum(v[0] for v in stats.values())
    tot = sum(v[1] for v in stats.values())
    for k, (o, t, pl) in stats.items():
        print(f"{k}: model == emulator {o}/{t}; walkers placed min {min(pl)} max {max(pl)}")
    print(f"TOTAL {tot_ok}/{tot} cases, whole RAM equal except the dead stack")
    for cn in CONTROLS:
        print(f"control '{cn}': equal in {sum(v[0] for v in ctl[cn].values())}/{tot}")


if __name__ == "__main__":
    main()
