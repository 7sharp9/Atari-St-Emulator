"""Check what the 255 eight-byte entries at $1af86 (`tabconv`) are: each stream byte b of a sample is looked up there and
`movep` writes entry[0..3] (reg,val,reg,val) to $ff8800.. and entry[4..5] (reg,val) -> PSG volume registers 8, 9, 10 (the three tone
channels' volumes, all tone/noise off after InitPsg).  Summing the three channels' DAC output gives a ~8 bit sample.
If that is right, the summed linear amplitude of entry b must be monotone in b read as a SIGNED byte (the sample bytes at
$5c6da look like small signed values: 05 03 01 01 fd fb f9 ...).

    cd M68000 && .venv/bin/python reversing/powermonger/py/sound/dac_table.py [snap]
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap  # noqa: E402

snap = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scratchpad/pm123/win/m1_s0.snap"
ram = ram_from_snap(snap)
TAB = 0x1AF86
# YM2149 per-channel DAC level (measured table, linear, 0..15); any monotone curve gives the same ordering test
LV = [0.0, 0.0100, 0.0145, 0.0211, 0.0307, 0.0455, 0.0645, 0.1073, 0.1266, 0.2050, 0.2922, 0.3728, 0.4986, 0.6353, 0.8056, 1.0]
amp = []
regs_ok = 0
for b in range(255):
    e = ram[TAB + 8 * b: TAB + 8 * b + 8]
    # movep.l D1 -> bytes e0,e1,e2,e3 go to $ff8800,$ff8802,$ff8804,$ff8806; movep.w -> $ff8808? no: see below
    regs_ok += (e[0], e[2], e[4]) == (8, 9, 10)
    amp.append(sum(LV[e[i] & 15] for i in (1, 3, 5)))
print(f"entries with register sequence (8,9,10): {regs_ok}/255")
sgn = lambda b: b - 256 if b > 127 else b
order = sorted(range(1, 255), key=sgn)           # byte 0 is the stream terminator
# The table is ordered "loudest at signed -128, silent at +127" (measured below): amplitude falls as the signed byte rises.
dec = sum(1 for a, b in zip(order, order[1:]) if amp[a] >= amp[b] - 1e-9)
print(f"signed order -> amplitude non-increasing steps: {dec}/{len(order) - 1}")
import numpy as np
xs = np.array([sgn(b) for b in order], float)
ys = np.array([amp[b] for b in order])
rank = lambda v: np.argsort(np.argsort(v))
rho = np.corrcoef(rank(xs), rank(ys))[0, 1]
print(f"Spearman rho(signed byte, summed channel amplitude) = {rho:.3f}")
print("amp at signed -128 / -2 / +1 / +127:", [round(amp[b & 255], 3) for b in (-128, -2, 1, 127)])
print("distinct (v8,v9,v10) triples:", len({tuple(ram[TAB + 8 * b + i] for i in (1, 3, 5)) for b in range(255)}))
# the sample bytes themselves: all 58 samples, histogram of signed value
BANK = 0x5879A
import struct
nseq, nsam = struct.unpack_from(">HH", ram, BANK)[::-1]
tab = [struct.unpack_from(">I", ram, BANK + 4 * i)[0] for i in range(1, nseq + nsam + 3)]
chunks, term_ok = [], 0
for j in range(nsam):
    a = BANK + tab[nseq + 1 + j]
    z = bytes(ram[a:a + 20000]).index(0)           # a sample stream ends at its first zero byte (FinJoue branch at $1af42)
    chunks.append(bytes(ram[a:a + z]))
    if j < nsam - 1:                                 # the length word NewEcha stores (+8) is the distance to the next start
        term_ok += (tab[nseq + 2 + j] - tab[nseq + 1 + j]) == z + 1
print(f"first zero byte is the last byte of the sample (length-1) for {term_ok}/{nsam - 1} samples (the last has no end offset)")
data = b"".join(chunks)
sg = np.frombuffer(data, np.int8)
print(f"{len(data)} sample bytes: byte 255 {int((np.frombuffer(data, np.uint8) == 255).sum())}, "
      f"|signed| <= 32: {100 * float((abs(sg.astype(int)) <= 32).mean()):.1f}%, min {int(sg.min())} max {int(sg.max())}")
cnt = np.bincount(np.frombuffer(data, np.uint8), minlength=256)
print("byte value counts  1..4:", cnt[1:5].tolist(), " 252..255:", cnt[252:256].tolist())
