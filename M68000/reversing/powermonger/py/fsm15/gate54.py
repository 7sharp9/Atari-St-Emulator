"""gate54.py <capture.json>...: live differential of mode $54's lord pick ($15ada..$15b5a, handler $15ad2) at natural entries.

Input: tools/capture_hits.py corpora stopped at $15ada (the first instruction after the dwell test `subq.w #1,18(A1) / bge`),
so the dwell has run out and the loop at $15b00 is about to run.  For each entry the model below (written from the listing,
`tools/rdis.py --rom <ram> --base 0 15ad2 15b5e 15ad2`) is run on the entry RAM and compared with the emulator resumed from the
same snapshot: `u 15b54` (the `jsr $159de`), `r` (A0, A3, A4), `u 15b5a`, `m A1 50`, `m 4e514 <lords>`.

Compared per entry: A3 and A0 at $15b54, A4, the merchant record bytes 0..49 after $15b5a, and every lord's bytes 0..31 for
the slots 0..A4/32 after $15b5a.  Also prints the branch class: passes of $15b00, whether $15b14 (A3 == A4 wrap) ran,
D2 = 14(A1) & 7, A0 == A3 or A3 + 32, and whether $159de took a good (and from which lord).

    MUTANT=1 runs the positive control (the model walks A3 along the table); it must report mismatches.

    cd M68000; uv run python reversing/powermonger/py/fsm15/gate54.py scratchpad/pm162/merchant/cap/rand1.json [...]
"""
import collections, json, os, re, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ["M68000_ROOT"]) if os.environ.get("M68000_ROOT") else next(
    p for p in Path(__file__).resolve().parents if (p / "tools" / "rdis.py").exists())
LEADER, SETTL = 0x4e514, 0x4f916
MUTANT = os.environ.get("MUTANT") == "1"   # MUTANT=1: model A3 advancing (`lea 32(A3),A3`), must mismatch


def w(r, a): return (r[a] << 8) | r[a + 1]


def model(ram, A1):
    """Returns (A3, A0, A4, passes, wrapped, mem) with mem a bytearray copy after $15b5a; None for A3 when the loop does not exit."""
    m = bytearray(ram)
    A3 = LEADER
    A4 = (A3 + w(m, 0x4f914)) & 0xfffff                       # $15ae0..$15ae2
    A0 = (SETTL + w(m, A1 + 34)) & 0xfffff                     # $15ae8..$15aee
    A3 = (A3 + w(m, A0 + 14)) & 0xfffff                        # $15af2 (adda.w: word sign-extended; offsets here < $8000)
    A0 = A3                                                    # $15af6
    D2 = m[A1 + 14] & 7                                        # $15af8..$15afc
    passes, wrapped = 0, False
    while True:                                                # $15b00
        passes += 1
        if passes > 10000:
            return None, A0, A4, passes, wrapped, m             # $15b00 never exits
        if m[A3] != 0:
            D2 = (D2 - 1) & 0xffff
            if D2 == 0 or D2 & 0x8000:                         # `ble`
                break
        A0 = (A3 + 32) & 0xfffff                               # $15b0c `lea 32(A3),A0`: A0, not A3
        if MUTANT:
            A3 = A0                                            # positive control: the walk the table row describes
        if A3 == A4:                                           # $15b10
            A3 = LEADER; wrapped = True                        # $15b14
    off = (A3 - LEADER) & 0xffff
    m[A1 + 46:A1 + 48] = off.to_bytes(2, "big")                # $15b24
    c = w(m, A3 + 4)
    m[A1 + 20] = c & 0x3f; m[A1 + 21] = 0x80                   # $15b28..$15b34
    m[A1 + 22] = (c << 2 >> 8) & 0xff; m[A1 + 23] = 0x80       # $15b3a..$15b44
    m[A1 + 30] = 0x50; m[A1 + 31] = 0x10                       # $15b48, $15b4e
    D0 = w(m, 0x57fec) % 6                                     # $159de
    a = A0 + 24 + D0
    if m[a]:
        m[a] -= 1
        D0 = (D0 + 1) * 2
        m[A1 + (33 if D0 >= 8 else 44)] = D0
    return A3, A0, A4, passes, wrapped, m


def repl(snap, cmds):
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl"],
                       input="\n".join(cmds + ["q"]) + "\n", capture_output=True, text=True, cwd=ROOT, env=env)
    return p.stdout + p.stderr


def dumps(log):
    """hex-byte lines of every `m` dump, in order."""
    out, cur = [], None
    for line in log.splitlines():
        if re.fullmatch(r"(?:[0-9a-f]{2} ?)+", line.strip()):
            out.append(bytes.fromhex(line.strip()))
    return out


def main():
    tot = collections.Counter(); bad = 0; nent = 0; nbytes = 0; okbytes = 0
    for js in sys.argv[1:]:
        for e in json.loads(Path(js).read_text()):
            nent += 1
            ram = (ROOT / e["ram"]).read_bytes()
            A1 = e["regs"]["A1"]
            mA3, mA0, mA4, passes, wrapped, mm = model(ram, A1)
            nl = mA4 - LEADER + 32
            log = repl(e["snap"], ["u 15b54 200000", "r", "u 15b5a 200000", f"m {A1:x} 50", f"m {LEADER:x} {nl}"])
            reached = re.findall(r"reached PC=\$000(15b54|15b5a)", log)
            regs = {k: int(v, 16) for k, v in re.findall(r"\b(A[034]):([0-9a-f]{8})", log)}
            d = dumps(log)
            if reached != ["15b54", "15b5a"] or len(d) != 2:
                print(f"{e['snap']}: emulator did not reach $15b54/$15b5a ({reached}); model A3={mA3}")
                bad += 1; tot["noexit"] += 1; continue
            rec, lords = d
            exp_rec, exp_l = bytes(mm[A1:A1 + 50]), bytes(mm[LEADER:LEADER + nl])
            nb = len(rec) + len(lords); ob = sum(x == y for x, y in zip(rec + lords, exp_rec + exp_l))
            nbytes += nb; okbytes += ob
            ok = (regs.get("A3") == mA3 and regs.get("A0") == mA0 and regs.get("A4") == mA4 and ob == nb)
            home = ram[A1 + 14] & 7
            took = [i for i in range(nl // 32) if ram[LEADER + 32 * i + 24:LEADER + 32 * i + 30] != bytes(mm[LEADER + 32 * i + 24:LEADER + 32 * i + 30])]
            a0rel = "A3" if mA0 == mA3 else ("A3+32" if mA0 == mA3 + 32 else f"${mA0:x}")
            cls = f"D2={home} passes={passes} wrap={int(wrapped)} A0={a0rel} took={'lord %d' % took[0] if took else '-'}"
            tot[(f"A0={a0rel}", "took" if took else "none")] += 1
            if wrapped: tot["wrapped"] += 1
            if not ok:
                bad += 1
                diff = [(i, x, y) for i, (x, y) in enumerate(zip(rec, exp_rec)) if x != y]
                print(f"{Path(e['snap']).name} A1=${A1:x}: MISMATCH emu A3={regs.get('A3', 0):x} A0={regs.get('A0', 0):x} "
                      f"model A3={mA3:x} A0={mA0:x}; rec diffs {diff[:6]} {cls}")
            else:
                print(f"{Path(e['snap']).name} A1=${A1:x} home=lord {(mA3 - LEADER) // 32} ok  {cls}")
    print(f"ENTRIES {nent - bad}/{nent} match; BYTES {okbytes}/{nbytes}; classes {dict(tot)}")


if __name__ == "__main__":
    main()
