"""139th: the shepherd cycle (entity modes $80 $84 $86 $88 $82, handlers $15f80 $15f96 $15e30 $15eb0 $15eee) vs the real 68000
through callcap 14b62, the iterator isolated to one record (every other live record's owner byte zeroed, the 93rd convention).

Tracked: pm_fsm_ref.REGIONS plus the animal pool and the RNG seed.  Natural states: shepherds (job 8, byte 7 & $1f == 8) in
the snapshots of a time series of two land builds (`series` below); synthetic states poke the mode byte to $88 / $82 and put a
shepherd on top of a free animal of its chain ($86 arrival) or turn a chain's animals into $12 (the release in $82).

    cd M68000
    python reversing/powermonger/py/build_series.py 0      # land 0 and land 5 built, then 30 snapshots 700000 steps apart each
    python reversing/powermonger/py/build_series.py 5      # (scratchpad/pm139/series/k<k>_<NN>.snap)
    python reversing/powermonger/py/gate_shepherd.py [name-substring]
"""
import collections
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness, State
from disassemble import ram_from_snap

S = os.environ.get("PM_SERIES", "scratchpad/pm139/series")      # PM_SERIES / PM_GATE_OUT: another roll, `build_series.py` with `PAGES0=1`
OUT = os.environ.get("PM_GATE_OUT", "scratchpad/pm139/g3")
(ROOT / OUT).mkdir(parents=True, exist_ok=True)
P.REGIONS = P.REGIONS + [(P.ANIMALS, P.ANIMAL_COUNT + 2, "animals"), (P.RNG_SEED, P.RNG_SEED + 4, "rng")]
MODES = (0x80, 0x82, 0x84, 0x86, 0x88)


def ram_of(name):
    ram = ROOT / S / f"{name}.ram"
    if not ram.exists():
        ram.write_bytes(ram_from_snap(str(ROOT / S / f"{name}.snap")))
    return ram.read_bytes()


def shepherds(r):
    out = []
    for s in range(1, 512):
        a = P.OBJ + s * P.REC
        if 0 < r[a + 5] < 128 and r[a + 6] == 0 and r[a + 7] & 0x1f == 8:
            out.append(s)
    return out


def chain(r, s):
    a = P.OBJ + s * P.REC
    c, d = [], int.from_bytes(r[a + 42:a + 44], "big")
    while d and len(c) < 12:
        c.append(P.ANIMALS + P.s16(d))
        d = int.from_bytes(r[c[-1] + 16:c[-1] + 18], "big")
    return c


ram_of("k0_00")
h = Harness(f"{S}/k0_00.snap", f"{S}/k0_00.ram", disk="scratchpad/powermonger.st", out_dir=OUT)
only = next((a for a in sys.argv[1:] if a != "reuse"), None)


def st(name, ram_name, slot, extra=(), tag=""):
    r = ram_of(ram_name)
    return State(name, h.disable_others(r, [slot]) + list(extra), tag=tag or f"m{r[P.OBJ + slot * P.REC + 31]:02x}",
                 snap=f"{S}/{ram_name}.snap", ram=f"{S}/{ram_name}.ram")


def bp(r, pairs):
    return h.bytepokes(bytearray(r), pairs)


def build():
    states = []
    # natural: up to two shepherds per snapshot, preferring the rarer modes
    for k in (0, 5):
        for i in range(0, 30):
            nm = f"k{k}_{i:02d}"
            r = ram_of(nm)
            sl = shepherds(r)
            sl.sort(key=lambda s: (r[P.OBJ + s * P.REC + 31] not in MODES, r[P.OBJ + s * P.REC + 31] == 0x84))
            for s in sl[:2]:
                if r[P.OBJ + s * P.REC + 31] in MODES:
                    states.append(st(f"{nm}_{s}", nm, s))
    # synthetic, on a handful of snapshots
    for nm in ("k0_04", "k0_17", "k5_06", "k5_20"):
        r = ram_of(nm)
        for s in shepherds(r)[:4]:
            a = P.OBJ + s * P.REC
            ch = chain(r, s)
            for mode in (0x88, 0x82):
                pk = {a + 31: mode}
                if mode == 0x82:                          # a herd to release: every animal of the chain is $12
                    for c in ch:
                        pk[c + 7] = 0x12
                        pk[c + 12] = r[c + 12] | 0x40
                        pk[c + 13] = r[c + 13] | 0x40
                states.append(st(f"{nm}_{s}_to{mode:02x}", nm, s, bp(r, pk), f"syn{mode:02x}"))
            if ch:                                         # $86 arrival: the shepherd on top of its first free animal
                c = ch[0]
                pk = {a + 31: 0x86, c + 7: 0x11}
                for off in (8, 9, 10, 11):
                    pk[a + off] = r[c + off]
                states.append(st(f"{nm}_{s}_arrive", nm, s, bp(r, pk), "syn86arrive"))
                pk2 = {a + 31: 0x86, c + 7: 0x11}
                for off in (8, 9, 10, 11):
                    pk2[a + off] = r[c + off]
                pk2[a + 9] = (r[c + 9] + 0x30) & 0xff
                states.append(st(f"{nm}_{s}_near", nm, s, bp(r, pk2), "syn86near"))
            # no free animal left: mode $86 with the whole chain herded
            pk = {a + 31: 0x86}
            for c in ch:
                pk[c + 7] = 0x12
            states.append(st(f"{nm}_{s}_none", nm, s, bp(r, pk), "syn86none"))
            # no chain at all
            states.append(st(f"{nm}_{s}_nochain", nm, s, bp(r, {a + 31: 0x86, a + 42: 0, a + 43: 0}), "syn86nochain"))
    return states


res = h.run_corpus(build(), min_states=40, min_branches=8, only=only)
sys.exit(0 if res["passed"] else 1)
