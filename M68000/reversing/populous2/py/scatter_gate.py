"""Populous II tree scatter $1f870 (world build): callcap against a literal model, byte for byte.

Model (read from $1f870 and $1f8a2):
  clusters = rand() mod N + N/2 + 1                         N = word $30e8c
  per cluster: c = rand() & $3f3f (high byte y, low byte x of the centre)
    r = rand(); frame index f = (r mod 8) & ~1; attempts = r mod M + bonus + 1    M = word $30e8a
      bonus: D2 is the side when it is 1 or 2 (side record +83 >> 4); at this call D2 is $ff9d, the
      hill table's terminator left by gen_land, and the code indexes $46fc4 + sign16(D2*$13a) = $3f656,
      so the bonus is byte $3f6a9 >> 4: inside the scenery array itself (record 45, byte 9).
    per attempt: r = rand(); o = offset table $30e96[(r mod $5a) / 2]; p = (o + c) & $ffff
      skip if p & $c0c0 (off the map), the cell (x = p & $ff, y = p >> 8) is sea (b1 = 0), its shape
      has flag $40 in $3697a, or it already has an occupant (word 2)
      take the first free record of $3f42a (side 0); none free ends the cluster
      record: +0 $16, +1 byte $30e89, +6 x, +7 $80, +8 y, +9 $80, +10 frame $30e8e[f], +12 side 3;
      r = rand(); if r mod $5a == 0 the frame is $30e8e[0]; link it at the head of the cell's list
Compared after each callcap: the scenery array ($3f42a..$3ff1a), the cell map and the seed.
Controls: the occupied-cell test dropped; the bonus taken as 0. The second half of the cases pokes
$3f6a9 = $80 at entry (record 45 is still free, so it is overwritten only once 46 trees exist) so the
stale-D2 bonus fires: 8 extra attempts per cluster.

$1fa6c (the next pass) is the same scatter for type $18 records with its own tables ($1fc68 N,
$1fc66 M, $1fc65 counter, $1fc6a frames, $1fc72 offsets), no bonus, and a full array skipping one
attempt instead of ending the cluster; --fa6c gates it the same way (no poked half).

usage: uv run python reversing/populous2/py/scatter_gate.py <snap stopped at the entry> [n] [--fa6c]
"""
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from corners import ROOT  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

CELLS, SCEN, ENT = 0x3979E, 0x3F42A, 0x3FF1A


def w16(m, a):
    return (m[a] << 8) | m[a + 1]


PASSES = {  # entry: (type, N, M, counter byte, frames, offsets, bonus from stale D2)
    0x1F870: (0x16, 0x30E8C, 0x30E8A, 0x30E89, 0x30E8E, 0x30E96, True),
    0x1FA6C: (0x18, 0x1FC68, 0x1FC66, 0x1FC65, 0x1FC6A, 0x1FC72, False),
}


def scatter(ram0, seed, d2, bonus_rule=True, occ_check=True, entry=0x1F870):
    typ, aN, aM, acnt, afr, aoff, has_bonus = PASSES[entry]
    bonus_rule = bonus_rule and has_bonus
    m = bytearray(ram0)
    st = [seed]

    def rand():
        if st[0] == 0:
            st[0] = 0xBC614E
        st[0] = (st[0] * 0xBB40E62D) & 0xFFFFFFFF
        return (st[0] >> 8) & 0x7FFF

    N, M, cnt = w16(m, aN), w16(m, aM), m[acnt]
    frames = [w16(m, afr + 2 * i) for i in range(4)]
    offs = [w16(m, aoff + 2 * i) for i in range(45)]
    clusters = rand() % N + N // 2 + 1
    for _ in range(clusters):
        c = rand() & 0x3F3F
        r = rand()
        f = (r % 8) & 0xFE
        attempts = r % M
        sd = d2 & 0xFFFF
        if bonus_rule and sd != 0 and (sd - 0x10000 if sd & 0x8000 else sd) <= 2:
            if True:
                off = (sd * 0x13A) & 0xFFFF
                a = 0x46FC4 + (off - 0x10000 if off & 0x8000 else off)
                attempts += m[a + 83] >> 4
        for _ in range((attempts & 0xFFFF) + 1):
            r = rand()
            p = (offs[((r % 0x5A) & 0xFE) // 2] + c) & 0xFFFF
            if p & 0xC0C0:
                continue
            x, y = p & 0xFF, p >> 8
            o = CELLS + (y * 64 + x) * 4
            b1 = m[o + 1]
            if b1 == 0 or w16(m, 0x3697A + 2 * b1) & 0x40 or (occ_check and w16(m, o + 2)):
                continue
            slot = next((a for a in range(SCEN, ENT, 14) if m[a + 12] == 0), None)
            if slot is None:
                if entry == 0x1F870:
                    break   # $1f956: a full array ends the cluster
                continue    # $1fb52: $1fa6c only skips the attempt
            m[slot + 12] = 3
            m[slot] = typ
            m[slot + 1] = cnt
            fr = frames[f // 2]
            if rand() % 0x5A == 0:
                fr = frames[0]
            m[slot + 10:slot + 12] = fr.to_bytes(2, "big")
            m[slot + 6], m[slot + 7], m[slot + 8], m[slot + 9] = x, 0x80, y, 0x80
            m[slot + 2:slot + 6] = b"\0\0\0\0"
            me = (slot - ENT) & 0xFFFF
            head = w16(m, o + 2)
            if head:
                m[slot + 2:slot + 4] = head.to_bytes(2, "big")
                h = ENT + (head - 0x10000 if head & 0x8000 else head)
                m[h + 4:h + 6] = me.to_bytes(2, "big")
            m[o + 2:o + 4] = me.to_bytes(2, "big")
    return m, st[0]


def main():
    snap = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
    entry = 0x1FA6C if "--fa6c" in sys.argv else 0x1F870
    ram0, _ = load_ram(snap)
    regs = subprocess.run(["dotnet", "exec", os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll"), "resume", snap, "repl"],
                          input="r\nq\n", capture_output=True, text=True, cwd=ROOT).stdout
    d2 = int(regs.split("D2:")[1][:8], 16) & 0xFFFF
    random.seed(13)
    seed0 = int.from_bytes(ram0[0x47382:0x47386], "big")
    seeds = [seed0, 0, 1] + [random.getrandbits(32) for _ in range(n - 3)]
    out = f"scratchpad/populous2/build/scatter_gate_{entry:x}"
    os.makedirs(os.path.join(ROOT, out), exist_ok=True)
    cases = [(s, 0) for s in seeds] + ([(s, 0x80) for s in seeds] if entry == 0x1F870 else [])
    script = "".join(f"w 47382 {s:08x}\nwb 3f6a9 {p:02x}\ncallcap {entry:x} 20000000 {out}/s{i}.json\n"
                     for i, (s, p) in enumerate(cases))
    r = subprocess.run(["dotnet", "exec", os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll"), "resume", snap, "repl"],
                       input=script + "q\n", capture_output=True, text=True, cwd=ROOT)
    if r.stdout.count(f"--- callcap ${entry:06x}: returned") != len(cases):
        sys.exit(f"callcaps did not all return\n{r.stdout[-1500:]}")
    ok = [0, 0]
    ctl = [0, 0]
    nob = [0, 0]
    trees = []
    for i, (s, p) in enumerate(cases):
        h = int(p != 0)
        base = bytearray(ram0)
        if entry == 0x1F870:
            base[0x3F6A9] = p
        cap = json.load(open(os.path.join(ROOT, out, f"s{i}.json")))
        emu = bytearray(base)
        emu[0x47382:0x47386] = s.to_bytes(4, "big")
        for a, _o, v in cap["mem"]:
            emu[a] = v
        m, seed = scatter(base, s, d2, entry=entry)
        c, _ = scatter(base, s, d2, occ_check=False, entry=entry)
        nb, _ = scatter(base, s, d2, bonus_rule=False, entry=entry)
        reg = lambda b: bytes(b[SCEN:ENT]) + bytes(b[CELLS:CELLS + 0x4000])
        same = reg(emu) == reg(m) and int.from_bytes(emu[0x47382:0x47386], "big") == seed
        ok[h] += same
        ctl[h] += reg(emu) == reg(c)
        nob[h] += reg(emu) == reg(nb)
        trees.append(sum(1 for a in range(SCEN, ENT, 14) if emu[a + 12]) - sum(1 for a in range(SCEN, ENT, 14) if ram0[a + 12]))
        if not same:
            d = [hex(a) for a in range(SCEN, ENT) if emu[a] != m[a]][:8]
            print(f"seed {s:08x}: scenery bytes differ at {d}")
    n = len(seeds)
    print(f"D2 at entry ${d2:04x}")
    print(f"natural: scenery array, cell map and seed equal to the model {ok[0]}/{n}; "
          f"controls: no occupied-cell test {ctl[0]}/{n}, no bonus {nob[0]}/{n}")
    if entry == 0x1F870:
        print(f"$3f6a9 poked $80: equal to the model {ok[1]}/{n}; "
              f"controls: no occupied-cell test {ctl[1]}/{n}, no bonus {nob[1]}/{n}")
    print(f"records placed: min {min(trees)} max {max(trees)}")


if __name__ == "__main__":
    main()
