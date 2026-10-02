"""98th-pass acceptance: re-prove the 93rd pass (dwell/upkeep core of $14b62 -
modes $12/$68/$8a) against the GRADUATED tools/pm_fsm_ref.py + pm_fsm_diff.py,
reusing the 93rd's own cached callcap deltas (scratchpad/pm93/o_*.json).

Expected: 675/675 tracked bytes identical over 22 states.

Ported verbatim from scratchpad/pm93/diff_fsm.py build_poke_corpus().
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC

h = Harness("scratchpad/pm88_f1.snap", "scratchpad/pm88_f1.ram", out_dir="scratchpad/pm93")
M68 = h.m68


def ram(name):
    return (M68 / "scratchpad" / f"{name}.ram").read_bytes()


def base(ram0):
    return h.disable_others(ram0, keep=[], trio=True)


def only(ram0, slot):
    return h.disable_others(ram0, keep=[slot], trio=False)


def find(ram0, mode):
    return h.slots_in_mode(ram0, mode, positive_only=True)


def build_corpus():
    states = []
    # --- naturals (trio records only) ---
    for nm, snap in (("pm88_f1", "scratchpad/pm88_f1.snap"),
                     ("pm78_settle", "scratchpad/pm78_settle.snap"),
                     ("pm74_late", "scratchpad/pm74_late.snap"),
                     ("pm73_fight", "scratchpad/pm73_fight.snap")):
        r = ram(nm)
        short = {"pm88_f1": "88f1", "pm78_settle": "settle",
                 "pm74_late": "late", "pm73_fight": "fight"}[nm]
        states.append(State(short, base(r), tag="nat", snap=snap, ram=f"scratchpad/{nm}.ram"))

    r = ram("pm88_f1")
    snap = "scratchpad/pm88_f1.snap"
    rf = "scratchpad/pm88_f1.ram"
    s12 = find(r, 0x12)
    s68 = find(r, 0x68)

    b = OBJ + s12[0] * REC
    states.append(State("88f1_dw1", base(r) + [(b + 18, 0x00000001)], tag="dw", snap=snap, ram=rf))
    b = OBJ + s12[1] * REC
    states.append(State("88f1_dw0", base(r) + [(b + 18, 0x00000000)], tag="dw", snap=snap, ram=rf))
    b = OBJ + s12[2] * REC
    states.append(State("88f1_step", base(r) + [(b + 12, 0x40400000)], tag="step", snap=snap, ram=rf))
    b = OBJ + s12[3] * REC
    states.append(State("88f1_negy", base(r) + [(b + 10, 0xFFF00000)], tag="veto", snap=snap, ram=rf))

    tick_lo = struct.unpack_from(">H", r, 0x4bb40)[0]
    b = OBJ + s68[0] * REC
    phase = struct.unpack_from(">H", r, b + 24)[0]
    trig = (tick_lo + phase) & 0x3ff
    states.append(State("88f1_anim",
                        base(r) + [(b + 34, (trig << 16) | struct.unpack_from(">H", r, b + 36)[0])],
                        tag="anim", snap=snap, ram=rf))
    b = OBJ + s68[1] * REC
    phase = struct.unpack_from(">H", r, b + 24)[0]
    trig = (tick_lo + phase) & 0x3ff
    states.append(State("88f1_animfrz",
                        base(r) + [(b + 34, (trig << 16) | struct.unpack_from(">H", r, b + 36)[0]),
                                   (b + 4, (r[b + 4] << 24) | (r[b + 5] << 16) | (r[b + 6] << 8) | (r[b + 7] | 0x10))],
                        tag="anim", snap=snap, ram=rf))
    b = OBJ + s12[4] * REC
    states.append(State("88f1_relink",
                        base(r) + [(b + 8, ((r[b + 8] + 1) << 24) | (r[b + 9] << 16) | (r[b + 10] << 8) | r[b + 11])],
                        tag="relink", snap=snap, ram=rf))
    b = OBJ + s68[1] * REC
    lw = (r[b + 44] << 24) | (1 << 16) | (r[b + 46] << 8) | r[b + 47]
    states.append(State("88f1_mor1", base(r) + [(b + 44, lw)], tag="morale", snap=snap, ram=rf))
    b = OBJ + s68[2] * REC
    lw = (r[b + 44] << 24) | (0xff << 16) | (r[b + 46] << 8) | r[b + 47]
    states.append(State("88f1_morneg", base(r) + [(b + 44, lw)], tag="morale", snap=snap, ram=rf))

    for i, s in enumerate(s12[:6]):
        states.append(State(f"88f1_only12_{i}", only(r, s), tag="only12", snap=snap, ram=rf))
    for i, s in enumerate(s68[:3]):
        states.append(State(f"88f1_only68_{i}", only(r, s), tag="only68", snap=snap, ram=rf))
    return states


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=20, min_branches=1,
                       steps=2_000_000, reuse_json="reuse" in sys.argv)
    sys.exit(0 if (res["passed"] and res["ok"] == res["tot"] == 675) else 1)
