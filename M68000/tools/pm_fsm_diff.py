"""Reusable differential-test harness: tools/pm_fsm_ref.py vs the real 68000.

The method (unchanged since the 93rd pass): isolate the entity FSM tick $14b62
down to the records under test by zeroing the owner byte (offset 5) of every
other live record, run the real routine in isolation with `callcap 14b62`,
apply its captured changed-memory delta, and compare the full delta over the
tracked regions (pm_fsm_ref.REGIONS) against pm_fsm_ref.reconstruct() - which is
handed ONLY the poked base RAM and never sees the callcap output.

A per-pass differential-test script reduces to:

    from pm_fsm_diff import Harness, State
    import pm_fsm_ref

    h = Harness("scratchpad/pm98/anchor.snap", "scratchpad/pm98/anchor.ram",
                out_dir="scratchpad/pm98")

    def build_corpus():
        R = h.anchor_ram_bytes
        states = []
        states.append(State("nat", h.disable_others(R, keep=[10, 30]), tag="nat"))
        ...
        return states

    h.run_corpus(build_corpus(), min_states=15, min_branches=8)

State fields:
    name  : used for the o_<name>.json callcap dump and the report line
    pokes : list[(addr, longword)] - applied via the REPL `w` command before the
            callcap AND struct-packed into the base RAM for reconstruct()
    tag   : branch-family label, for the pre-registered coverage bar
    snap  : per-state snapshot path (M68000-relative); defaults to the anchor
    ram   : per-state RAM path      (M68000-relative); defaults to the anchor

run_corpus(states, min_states, min_branches=0, steps=2_000_000, reuse_json=False):
    reuse_json=True skips the emulator whenever <out_dir>/o_<name>.json already
    exists (the callcap output is determinism-verified ground truth - see
    `detcheck` in the tooling memo), so a graduated prior pass re-proves against
    its own cached deltas without re-running.

GOTCHA: the REPL `w` command writes a BIG-ENDIAN longword.  Poke a word at an
even offset as (v>>8)&0xff / v&0xff across the two bytes, or use lw_word().
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import pm_fsm_ref
from pm_fsm_ref import OBJ, REC, s8

TRIO = (0x12, 0x68, 0x8a)
DEFAULT_DISK = "scratchpad/pm69.st"


class State:
    __slots__ = ("name", "pokes", "tag", "snap", "ram")

    def __init__(self, name, pokes, tag="", snap=None, ram=None):
        self.name = name
        self.pokes = list(pokes)
        self.tag = tag or name
        self.snap = snap
        self.ram = ram


class Harness:
    def __init__(self, anchor_snap, anchor_ram, disk=DEFAULT_DISK,
                 out_dir="scratchpad", m68_dir=None):
        self.m68 = Path(m68_dir) if m68_dir else Path(__file__).resolve().parent.parent
        self.anchor_snap = anchor_snap
        self.anchor_ram = anchor_ram
        self.disk = disk
        self.out_dir = out_dir
        self.anchor_ram_bytes = (self.m68 / anchor_ram).read_bytes()
        pm_fsm_ref.init_tables(self.anchor_ram_bytes)

    # ----------------------------------------------------------- pure helpers
    @staticmethod
    def live_slots(ram):
        return [s for s in range(1, 512) if ram[OBJ + s * REC + 5] != 0]

    @staticmethod
    def slots_in_mode(ram, mode, positive_only=True):
        out = []
        for s in range(1, 512):
            b = OBJ + s * REC
            if ram[b + 5] == 0 or ram[b + 31] != mode:
                continue
            if positive_only and s8(ram[b + 5]) <= 0:
                continue
            out.append(s)
        return out

    @staticmethod
    def disable_others(ram, keep, *, trio=False):
        """Longword pokes that zero the owner byte (offset 5) of every live
        record not in `keep`, preserving bytes 4/6/7.  trio=True additionally
        keeps every positive-owner {$12,$68,$8a} record live (the proven
        dwell/upkeep modes - 93rd/94th convention)."""
        keep = set(keep)
        pk = []
        for s in range(1, 512):
            b = OBJ + s * REC
            if ram[b + 5] == 0 or s in keep:
                continue
            if trio and ram[b + 31] in TRIO and s8(ram[b + 5]) > 0:
                continue
            pk.append((b + 4, (ram[b + 4] << 24) | (ram[b + 6] << 8) | ram[b + 7]))
        return pk

    @staticmethod
    def lw_at(ram, a, val):
        """Longword poke setting the byte at `a` to `val`, other 3 preserved."""
        base = a & ~3
        b = bytearray(ram[base:base + 4])
        b[a - base] = val & 0xff
        return (base, struct.unpack(">I", bytes(b))[0])

    @staticmethod
    def lw_word(ram, a, val):
        """Longword poke setting the word at even `a` to `val`."""
        base = a if (a & 2) == 0 else a - 2
        b = bytearray(ram[base:base + 4])
        struct.pack_into(">H", b, a - base, val & 0xffff)
        return (base, struct.unpack(">I", bytes(b))[0])

    @staticmethod
    def bytepokes(ram, pairs):
        """{addr: byte} -> non-colliding longword pokes (byte edits merged per
        4-byte base, so adjacent-field edits don't clobber each other)."""
        buf = bytearray(ram)
        bases = set()
        for a, v in pairs.items():
            buf[a] = v & 0xff
            bases.add(a & ~3)
        return [(base, struct.unpack_from(">I", buf, base)[0]) for base in sorted(bases)]

    @staticmethod
    def poked_ram(ram, pokes):
        out = bytearray(ram)
        for a, lw in pokes:
            struct.pack_into(">I", out, a, lw)
        return out

    @staticmethod
    def tracked_delta(before, after):
        d = {}
        for lo, hi, _ in pm_fsm_ref.REGIONS:
            for a in range(lo, hi):
                if before[a] != after[a]:
                    d[a] = (before[a], after[a])
        return d

    # ----------------------------------------------------------- emulator
    def run_repl(self, cmds, snap=None):
        snap = snap or self.anchor_snap
        script = "".join(c + "\n" for c in cmds) + "q\n"
        p = subprocess.run(
            ["pwsh", "-NoProfile", "-c",
             f"./run.ps1 -NoBuild rrepl {snap} -DiskA {self.disk}"],
            input=script, capture_output=True, text=True,
            cwd=self.m68, timeout=400)
        return p.stdout + p.stderr

    # ----------------------------------------------------------- corpus loop
    def run_corpus(self, states, min_states, min_branches=0, steps=2_000_000,
                   reuse_json=False, only=None):
        if only is None and len(sys.argv) > 1:
            only = sys.argv[1]
        tot = ok = n = 0
        seen = {}
        fails = []
        for st in states:
            if only and only not in st.name:
                continue
            ram0 = (self.m68 / st.ram).read_bytes() if st.ram else self.anchor_ram_bytes
            pk = self.poked_ram(ram0, st.pokes)
            outp = self.m68 / self.out_dir / f"o_{st.name}.json"

            if not (reuse_json and outp.exists()):
                cmds = [f"w {a:x} {w:08x}" for a, w in st.pokes]
                cmds.append(f"callcap 14b62 {steps} {self.out_dir}/o_{st.name}.json")
                log = self.run_repl(cmds, st.snap)
                if not outp.exists():
                    print(f"{st.name:24} NO OUTPUT")
                    print(log[-1500:])
                    fails.append((st.name, "no-output", None, None))
                    continue

            j = json.load(open(outp))
            if j.get("outcome") != "returned":
                print(f"{st.name:24} callcap outcome={j.get('outcome')} steps={j.get('steps')}")
                fails.append((st.name, "outcome", j.get("outcome"), None))
                continue

            after_real = bytearray(pk)
            for a, b0, b1 in j["mem"]:
                after_real[a] = b1
            real = self.tracked_delta(pk, after_real)

            m = pm_fsm_ref.Mem(pk)
            try:
                pm_fsm_ref.reconstruct(m)
            except AssertionError as e:
                print(f"{st.name:24} RECON ASSERT: {e}")
                fails.append((st.name, "assert", str(e), None))
                continue
            recon = self.tracked_delta(pk, m.r)

            keys = set(real) | set(recon)
            bad = [k for k in keys if real.get(k) != recon.get(k)]
            tot += len(keys)
            ok += len(keys) - len(bad)
            n += 1
            seen[st.tag] = seen.get(st.tag, 0) + 1
            status = "ok" if not bad else f"MISMATCH x{len(bad)}"
            print(f"{st.name:24} [{st.tag:12}] steps={j['steps']:5d} "
                  f"real={len(real):3d} recon={len(recon):3d}  {status}")
            for k in sorted(bad)[:20]:
                fails.append((st.name, hex(k), real.get(k), recon.get(k)))

        print(f"\nTRACKED BYTES: {ok}/{tot} identical over {n} exercised states")
        print("branch coverage:", seen)
        passed = not fails and n >= min_states and len(seen) >= min_branches
        if fails:
            print("FAILURES:")
            for x in fails[:80]:
                print("  ", x)
        elif passed:
            print("PASS - pre-registered bar met")
        else:
            print(f"(only {n} states / {len(seen)} branches - "
                  f"need >= {min_states} / {min_branches})")
        return {"ok": ok, "tot": tot, "n": n, "branches": len(seen),
                "fails": fails, "passed": passed}
