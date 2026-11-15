"""Populous II conquest battles from CONQUEST.PAK (file $c), as decrunched at $47d28 in anchors/p2_briefing.

Read from $22e8c / $2d42c / $22c40 / $22cde / $22266 (README "Conquest battles"):
  battle N uses the 250-byte record (N / 5) at $47d28 + 250 * (N / 5), copied to $30470; $22c40 copies its
  first 58 bytes to side 1's record +90.. and the next 58 to side 2's, so side s's power bytes +112.. are record
  bytes 22.. (side 1) and 80.. (side 2); the seed $47382 is the long at record +182 plus (N mod 5) * $2d7.
  $22cde builds a side's plan list from the 24 (power, kind) entries at $306a2 whose power byte
  +112[$30f48[power] / 2] is in 1..$7f (w148 = entries + 1), and the second list from the 8 at $30702 (w150).
  $22266 names battle N: v = (N * $24a1 with $24df added to the low word) & $7fff, one two-letter syllable of
  the table $22298 per 6 bits of v, low bits first.

usage: uv run python reversing/populous2/py/god/conquest_records.py [start snap ...]
  With start snapshots (battle_census.sh's b<N>_start.snap) it checks the predicted w148/w150 of both sides
  and the battle's seed against each; without, it prints the per-kind summary over all records.
"""
import os
import sys
from collections import Counter

ROOT = os.path.abspath(__file__)
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

BRIEF = os.path.join(ROOT, "scratchpad/populous2/anchors/p2_briefing.snap")
BUF, REC, LIMIT = 0x47D28, 250, 0x523F4  # FACES.PAK loads at $523f4, so 170 records survive at the briefing


def main():
    r, _ = load_ram(BRIEF)

    def w(a):
        return (r[a] << 8) | r[a + 1]

    ents = [(w(a), w(a + 2)) for a in range(0x306A2, 0x30702, 4)]
    ents2 = [(w(a), w(a + 2)) for a in range(0x30702, 0x30722, 4)]
    n_rec = (LIMIT - BUF) // REC
    syl = bytes(r[0x22298:0x22298 + 128])

    def lists(g, side):
        off = BUF + REC * g + (22 if side == 1 else 80)
        pw = r[off:off + 36]
        take = lambda p: 0 < pw[w(0x30F48 + p) >> 1] < 0x80  # noqa: E731
        return [e for e in ents if take(e[0])], [e for e in ents2 if take(e[0])]

    def seed(n):
        a = BUF + REC * (n // 5) + 182
        return ((w(a) << 16 | w(a + 2)) + (n % 5) * 0x2D7) & 0xFFFFFFFF

    def name(n):
        v = (n * 0x24A1) & 0xFFFFFFFF
        v = ((v & 0xFFFF0000) | ((v + 0x24DF) & 0xFFFF)) & 0x7FFF
        s = b""
        while v:
            s += syl[(v & 0x3F) * 2:(v & 0x3F) * 2 + 2]
            v >>= 6
        return s.decode("latin1")

    if len(sys.argv) > 1:
        ok = tot = 0
        for snap in sys.argv[1:]:
            s, _ = load_ram(snap)
            ws = lambda a: (s[a] << 8) | s[a + 1]  # noqa: E731
            n = ws(0x473A0)
            got, want = [], []
            for side in (1, 2):
                S = 0x46FC4 + side * 0x13A
                l1, l2 = lists(n // 5, side)
                got += [ws(S + 148), ws(S + 150)]
                want += [len(l1) + 1, len(l2)]
            good = got == want
            ok += good
            tot += 1
            print(f"{os.path.basename(snap)}: battle {n} '{name(n)}' w148/w150 side1,side2 emu {got} predicted {want} "
                  f"{'equal' if good else 'DIFFER'}; seed rule {seed(n):08x}")
        print(f"predicted plan sizes equal on {ok}/{tot} start snapshots")
        return
    print(f"{n_rec} records (battles 0..{5 * n_rec - 1}) below FACES.PAK at the briefing")
    for side in (1, 2):
        per = {}
        for g in range(n_rec):
            l1, _ = lists(g, side)
            for k, c in Counter(k for _, k in l1).items():
                per.setdefault(k, []).append((len(l1), g))
        empty = [g for g in range(n_rec) if not lists(g, side)[0]]
        print(f"side {side}: empty first list in {len(empty)} records {empty[:8]}")
        for k in sorted(per):
            print(f"  kind {k}: in {len(per[k])} records; shortest lists (entries, record) {sorted(per[k])[:4]}")
    print("kinds in $306a2:", sorted(Counter(k for _, k in ents).items()), " in $30702:", sorted(Counter(k for _, k in ents2).items()))
    print("names:", ", ".join(f"{n} {name(n)}" for n in (0, 10, 40, 100, 260, 285, 485, 635)))


if __name__ == "__main__":
    main()
