"""Populous II fight round, entity state $e ($238dc): is the damage random?

Read from $2391e..$23976 (A0 the attacker, A1 the defender from +30, strength the long +26, K the word $30af0):
    r = rand()                                  $215dc, advances the seed $47382
    D1 = (def / K) * ((r & 3) + 1) * (att / K)  computed, then cleared by moveq #0,D1 at $23956
    D2 = ((r >> 2) & 3) + 1                     computed, never read
    base = att / K                              (divu quotient, low word)
    def.strength -= att.byte25 * base + 10
    att.strength -= def.byte25 * base + 10
So the random draw advances the generator but does not reach the damage (the model to test).
Control 'random': base multiplied by ((r >> 2) & 3) + 1, the use the dead D2 suggests.

From a snapshot stopped at $2391e (a natural state-$e round), each case pokes the seed and optionally the two
strengths, runs to $2397a (both subtractions done) and compares both strengths and the seed with the model.

Whole fight: the model iterated to the first round that leaves a strength <= 0, against the emulator run on to the
resolution $247e2 (A2 the winner, A3 the loser; read): who wins, both final strengths, and the mana long +0 of
both side records, read at $247e2 and 2,000 steps on, moved by 400 (the base reward, word $36da6, for a loser that is no leader and has +13 bit 1
clear and is not a settlement), the winner's side up and the loser's down.

usage: uv run python reversing/populous2/py/fight_gate.py <snap at $2391e> [n]
"""
import os
import random
import re
import subprocess
import sys

ROOT = os.path.abspath(__file__)
while not os.path.exists(os.path.join(ROOT, "tools", "rdis.py")):
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

DLL = os.path.join(ROOT, "bin/Debug/net8.0/M68000.dll")


def rand(seed):
    """$215dc as py/rand_gate.py models it (50/50): 0 becomes $bc614e; seed' = seed * $bb40e62d mod 2^32;
    returns (seed', D0 = (seed' >> 8) & $7fff)."""
    s = ((seed or 0xBC614E) * 0xBB40E62D) & 0xFFFFFFFF
    return s, (s >> 8) & 0x7FFF


def regs_from_log(snap):
    r = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl"], input="r\nq\n", capture_output=True,
                       text=True, cwd=ROOT)
    m = re.search(r"A0:([0-9a-f]{8}) A1:([0-9a-f]{8})", r.stdout)
    return int(m.group(1), 16), int(m.group(2), 16)


def run(snap, seed, att, dfn, a0, a1):
    s = f"w 47382 {seed:08x}\n"
    if att is not None:
        s += f"w {a0 + 26:x} {att:08x}\nw {a1 + 26:x} {dfn:08x}\n"
    s += f"bp 2397a 200000\nm {a0 + 26:x} 4\nm {a1 + 26:x} 4\nm 47382 4\nq\n"
    r = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl"], input=s, capture_output=True, text=True,
                       cwd=ROOT, env={**os.environ, "ATARI_NOTRACE": "1"})
    if "breakpoint $0002397a hit" not in r.stdout:
        sys.exit(f"did not reach $2397a\n{r.stdout[-800:]}")
    vals = [int("".join(l.split()[:4]), 16) for l in r.stdout.splitlines() if re.fullmatch(r"([0-9a-f]{2} ){3}[0-9a-f]{2}", l.strip())]
    return vals[-3:]


def main():
    snap = os.path.abspath(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    m, _ = load_ram(snap)
    a0, a1 = regs_from_log(snap)
    L = lambda a: int.from_bytes(m[a:a + 4], "big")  # noqa: E731
    K = (m[0x30AF0] << 8) | m[0x30AF1]
    b0, b1 = m[a0 + 25], m[a1 + 25]
    seed0 = L(0x47382)
    print(f"attacker ${a0:x} strength {L(a0 + 26)} byte25 {b0}; defender ${a1:x} strength {L(a1 + 26)} byte25 {b1}; "
          f"K {K}; seed {seed0:08x}")
    random.seed(0x238DC)
    cases = [(seed0, None, None)] + [(random.getrandbits(32), None, None) for _ in range(n // 2 - 1)]
    cases += [(random.getrandbits(32), random.randrange(1, 4000), random.randrange(1, 4000)) for _ in range(n - len(cases))]
    ok = ctl = 0
    outcomes = set()
    for seed, att, dfn in cases:
        A = L(a0 + 26) if att is None else att
        D = L(a1 + 26) if dfn is None else dfn
        got = run(snap, seed, att, dfn, a0, a1)
        ns, r = rand(seed)
        base = (A // K) & 0xFFFF
        want = [(A - (b1 * base + 10)) & 0xFFFFFFFF, (D - (b0 * base + 10)) & 0xFFFFFFFF, ns]
        cb = (base * (((r >> 2) & 3) + 1)) & 0xFFFF
        alt = [(A - (b1 * cb + 10)) & 0xFFFFFFFF, (D - (b0 * cb + 10)) & 0xFFFFFFFF, ns]
        ok += got == want
        ctl += got == alt
        if att is None:
            outcomes.add(tuple(got[:2]))
        if got != want:
            print(f"seed {seed:08x} att {A} def {D}: emu {got} model {want}")
    print(f"model == emulator {ok}/{len(cases)} (both strengths and the seed); control 'random' {ctl}/{len(cases)}")
    print(f"natural strengths, {n // 2} seeds: {len(outcomes)} distinct outcome(s)")
    whole(snap, m, a0, a1, K, b0, b1)


def whole(snap, m, a0, a1, K, b0, b1):
    L = lambda a: int.from_bytes(m[a:a + 4], "big")  # noqa: E731
    A, D, rounds = L(a0 + 26), L(a1 + 26), 0
    while A > 0 and D > 0:
        base = A // K
        D -= b0 * base + 10
        A -= b1 * base + 10
        rounds += 1
    sa, sd = 0x46FC4 + m[a0 + 12] * 0x13A, 0x46FC4 + m[a1 + 12] * 0x13A
    script = f"bp 247e2 20000000\nr\nm {sa:x} 4\nm {sd:x} 4\nm {a0 + 26:x} 4\nm {a1 + 26:x} 4\ns 2000\nm {sa:x} 4\nm {sd:x} 4\nq\n"
    r = subprocess.run(["dotnet", "exec", DLL, "resume", snap, "repl"], input=script, capture_output=True, text=True,
                       cwd=ROOT, env={**os.environ, "ATARI_NOTRACE": "1"})
    v = [int("".join(l.split()), 16) for l in r.stdout.splitlines() if re.fullmatch(r"([0-9a-f]{2} ){3}[0-9a-f]{2}", l.strip())]
    g = re.findall(r"A2:([0-9a-f]{8}) A3:([0-9a-f]{8})", r.stdout)
    sg = lambda x: x - (1 << 32) if x & 0x80000000 else x  # noqa: E731
    if A <= 0 and D <= 0:
        print(f"whole fight: model says both die after {rounds} rounds; emulator A2/A3 {g[:1]}")
        return
    win, lose = (a1, a0) if A <= 0 else (a0, a1)
    sw, sl = (sd, sa) if A <= 0 else (sa, sd)
    mana0 = {sa: v[0], sd: v[1]}
    mana1 = {sa: v[4], sd: v[5]}
    checks = [
        ("winner and loser", g and (int(g[0][0], 16), int(g[0][1], 16)) == (win, lose)),
        ("attacker final strength", sg(v[2]) == A),
        ("defender final strength", sg(v[3]) == D),
        ("winner's side mana +400", mana1[sw] - mana0[sw] == 400),
        ("loser's side mana -400", mana0[sl] - mana1[sl] == 400),
    ]
    print(f"whole fight: model {rounds} rounds, attacker {A}, defender {D}, winner ${win:x}; emulator attacker "
          f"{sg(v[2])}, defender {sg(v[3])}, mana {mana0} -> {mana1}")
    print(f"whole fight checks {sum(c for _, c in checks)}/{len(checks)}: " + ", ".join(k for k, c in checks if not c))


if __name__ == "__main__":
    main()
