"""Decode the sound bank the driver `NewEcha` ($1b83c) indexes: header, the 56 sequences ((sample, Timer-A data) byte pairs
ended by $ff), the 58 samples (signed 8-bit PCM stored as indices into the PSG volume-triple table at $1af86), and the
12-byte sample records the driver builds at $2cba6.

    cd M68000 && .venv/bin/python reversing/powermonger/py/sound/bank.py [snap]

Writes bank_report.txt next to this script.  Everything is read from the snapshot's RAM (the bank is at $5879a, filled
by the game's own loader; the driver tables $2c9a0 / $2cba6 are built from it by NewEcha)."""
import os
import struct
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/sound"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
snap = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scratchpad/pm123/win/m1_s0.snap"
ram = ram_from_snap(snap)
BANK = 0x5879A
u16 = lambda a: struct.unpack_from(">H", ram, a)[0]
u32 = lambda a: struct.unpack_from(">I", ram, a)[0]
nsam, nseq = u16(BANK), u16(BANK + 2)          # word0 -> $2c99e, word1 -> $2c99c
tab = [u32(BANK + 4 * i) for i in range(1, nseq + nsam + 3)]
out = []
out.append(f"bank ${BANK:x}: word0 (-> $2c99e) = {nsam}, word1 (-> $2c99c) = {nseq}; offsets tab[1..] at bank+4")
assert u16(0x2C99E) == nsam and u16(0x2C99C) == nseq
seqs = []
for i in range(nseq):
    a = BANK + tab[i]
    assert u32(0x2C9A0 + 4 * i) == a, (i, hex(a))        # NewEcha's pointer table agrees with the header
    pairs = []
    p = a
    while ram[p] != 0xFF:
        pairs.append((ram[p], ram[p + 1]))
        p += 2
    seqs.append((a, pairs))
out.append(f"$2c9a0[0..{nseq-1}] == bank+tab[i]: {nseq}/{nseq} equal")
for i, (a, pairs) in enumerate(seqs):
    out.append(f"seq {i:2d} (call id {i+1:2d}) @${a:x}: {len(pairs):3d} pairs; samples used {sorted({s for s,_ in pairs})}; rates {sorted({r for _,r in pairs})}")
ok = 0
smp = []
for j in range(nsam):
    s = BANK + tab[nseq + 1 + j]
    e = BANK + tab[nseq + 2 + j]
    rec = 0x2CBA6 + 12 * j
    good = (u32(rec) == s and u32(rec + 4) == s and u32(rec + 8) == e - s)
    ok += good
    smp.append((s, e - s))
    out.append(f"sample {j:2d} @${s:x} len {e-s:5d}  record ${rec:x} matches NewEcha: {good}")
out.append(f"sample records matching: {ok}/{nsam}")
(DATA / "bank_report.txt").write_text("\n".join(out) + "\n")
print("\n".join(out[:4]), "...", out[-1])
