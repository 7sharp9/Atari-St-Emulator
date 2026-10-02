"""The order senders and executors against the real 68000.

    cd M68000 && .venv/bin/python scratchpad/pm141/agents/orders/gate_orders.py [name-substring] [reuse]

Each case is a state (a start snapshot plus byte edits made on a Python copy of its RAM, written to the emulator as
aligned `w` longword pokes and rolled back after the call), a callcap target with register presets, and a model call
(`orders_ref.call_*`) run on the edited RAM.  Compared: every byte the real call changed against every byte the model
changed over the whole of RAM except the stack, plus the registers the routine hands back.  A byte missing on either side is
a mismatch.  One emulator run per start snapshot (callcap restores the machine; the pokes are undone by hand).
"""
import collections
import json
import numpy as np
import os
import random
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
import pm_fsm_ref as P
import orders_ref as O
from scan_groups import groups

WORK = "scratchpad/pm141/agents/orders"      # data (callcap JSON, natural snapshots) lives here, not beside the script
DATA = ROOT / WORK
NAT = DATA / "nat"
OUT = DATA / "g"
OUT.mkdir(parents=True, exist_ok=True)
REL = OUT.relative_to(ROOT).as_posix()
DISK = "scratchpad/powermonger.st"
OBJ, GROUP, LEADERS, SETTL = P.OBJ, P.GROUP, P.LEADERS, P.SETTL
BASES = {
    "m1": "scratchpad/pm123/win/m1_ready.snap",
    "k25": "scratchpad/pm121/run/k25_s4.snap",
    "k5": "scratchpad/pm121/run/k5_s4.snap",
}
only = next((a for a in sys.argv[1:] if a != "reuse"), None)
reuse = "reuse" in sys.argv


class Case:
    def __init__(self, name, base, target, presets, setup, model, regs=()):
        self.name, self.base, self.target, self.presets = name, base, target, presets
        self.setup = setup      # setup(m) -> None: byte edits on the Python RAM copy
        self.model = model      # model(m) -> dict of returned registers (or None)
        self.regs = regs        # names of returned registers to compare, e.g. ("D0", "A0")


# ----------------------------------------------------------------------------- state helpers
def free_obj_slot(m, used=()):
    for s in range(511, 0, -1):
        a = OBJ + s * 50
        if m.bu(a + 5) == 0 and m.bu(a + 6) == 0 and m.bu(a + 7) == 0 and m.wu(a + 8) == 0 and a not in used:
            return a
    raise RuntimeError("no free slot")


def plant(m, cell, side, cat, flags=0, a=None, extra=None):
    """A record of category `cat` in a free OBJ slot, bucket-linked into `cell` (x = cell & 63, y = cell >> 6)."""
    a = a or free_obj_slot(m)
    for i in range(50):
        m.wb(a + i, 0)
    m.wb(a + 5, side)
    m.wb(a + 6, cat)
    m.wb(a + 7, flags)
    m.ww(a + 8, ((cell & 63) << 8) | 0x80)
    m.ww(a + 10, ((cell >> 6) << 8) | 0x80)
    for off, v in (extra or {}).items():
        m.wb(a + off, v)
    P.call_16808(m, cell, (a - OBJ) & 0xffff)
    return a


def plant_drop(m, cell, food=0, goods=(0,) * 8):
    """A $2c goods-drop record in a free $4bb4e slot (28 bytes), linked into `cell`."""
    for a in range(0x4bb4e, 0x4bdee, 28):
        if s8_(m.bu(a + 6)) <= 0:
            break
    else:
        raise RuntimeError("no drop slot")
    for i in range(28):
        m.wb(a + i, 0)
    m.wb(a + 6, 0x2c)
    m.ww(a + 8, cell)
    m.ww(a + 10, food)
    for i, g in enumerate(goods):
        m.ww(a + 12 + 2 * i, g)
    P.call_16808(m, cell, (a - OBJ) & 0xffff)
    return a


def s8_(v):
    return v - 256 if v >= 128 else v


def roster(m, g):
    out, d = [], g["first"]
    while d and len(out) < 64:
        out.append((OBJ + P.s16(d)) & 0xfffff)
        d = m.wu(out[-1] + 26)
    return out


def leader_of(m, side):
    return [a for a in range(LEADERS, 0x4f914, 0x20) if m.bu(a) == side]


def free_cell(m, avoid=()):
    """A cell with an empty bucket."""
    rnd = random.Random(7)
    while True:
        c = rnd.randrange(64 * 20, 64 * 100)
        if m.wu(P.BUCKETS + 2 * c) == 0 and c not in avoid and 5 <= (c & 63) < 58:
            return c


def xy(cell):
    return cell & 63, cell >> 6


# ----------------------------------------------------------------------------- the emulator
def run_base(base, cases):
    snap = BASES[base]
    ram0 = ram_from_snap(str(ROOT / snap))
    cmds, meta = [], []
    for c in cases:
        m1 = P.Mem(ram0)
        P.init_tables(ram0)
        O.TRACE.clear()
        c.setup(m1)
        pk = bytes(m1.r)
        pokes = sorted({int(a) & ~3 for a in diff_idx(ram0, pk)})
        for b in pokes:
            cmds.append("w %x %08x" % (b, struct.unpack_from(">I", pk, b)[0]))
        pre = "".join(" %s=%x" % (k, v & 0xffffffff) for k, v in c.presets.items())
        cmds.append("callcap %s 3000000 %s/%s.json%s" % (c.target, REL, c.name, pre))
        for b in pokes:
            cmds.append("w %x %08x" % (b, struct.unpack_from(">I", ram0, b)[0]))
        meta.append((c, pk))
    run = (not reuse) or any(not (OUT / (c.name + ".json")).exists() for c in cases)
    if run:
        for c in cases:
            (OUT / (c.name + ".json")).unlink(missing_ok=True)
        script = "\n".join(cmds) + "\nq\n"
        (OUT / (base + ".cmds")).write_text(script)
        p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", DISK],
                           input=script, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"),
                           timeout=1800)
        (OUT / (base + ".log")).write_text(p.stdout + p.stderr)
    return ram0, meta


def diff_idx(a, b):
    return np.nonzero(np.frombuffer(bytes(a), np.uint8) != np.frombuffer(bytes(b), np.uint8))[0]


SCREEN = (0x78000, 0x7fd00)      # the display: $17a46 redraws the selected group's panel icons (the model leaves it untracked)
REGN = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def judge(c, ram0, pk):
    """Returns (ok_bytes, total_bytes, problems, trace)."""
    f = OUT / (c.name + ".json")
    if not f.exists():
        return 0, 0, ["no output"], []
    j = json.load(open(f))
    if j.get("outcome") != "returned":
        return 0, 0, ["outcome %s steps %s" % (j.get("outcome"), j.get("steps"))], []
    sp = j["entrySP"]
    lo, hi = sp - 0x800, sp + 0x40
    real = {a: b1 for a, b0, b1 in j["mem"] if not lo <= a < hi and not SCREEN[0] <= a < SCREEN[1]}
    P.init_tables(ram0)
    m = P.Mem(pk)
    O.TRACE.clear()
    try:
        ret = c.model(m)
    except AssertionError as e:
        return 0, 0, ["EXCLUDED model assert: %s" % str(e)[:80]], list(O.TRACE)
    tr = list(O.TRACE)
    model = {int(a): m.r[a] for a in diff_idx(pk, m.r) if not lo <= a < hi and not SCREEN[0] <= a < SCREEN[1]}
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, pk[a]) != model.get(a, pk[a])]
    probs = ["%#x real %02x model %02x (was %02x)" % (a, real.get(a, pk[a]), model.get(a, pk[a]), pk[a]) for a in sorted(bad)[:6]]
    tot = len(keys)
    ok = tot - len(bad)
    if c.regs and ret is not None:
        for r in c.regs:
            want = ret[r]
            got = j["regN"][REGN.index(r)]
            mask = 0xffffffff if r.startswith("A") else 0xffff
            tot += 1
            if (want & mask) != (got & mask):
                probs.append("reg %s real %x model %x" % (r, got & mask, want & mask))
            else:
                ok += 1
    return ok, tot, probs, tr


# ----------------------------------------------------------------------------- case builders
def group_cases(base, m0, g, add):
    tag = "%s_s%dk%d" % (base, g["side"], g["k"])
    D2 = g["off"]
    A3 = g["A3"]
    lead = (OBJ + P.s16(g["lead"])) & 0xfffff
    side = g["own"]
    cell_free = free_cell(m0)
    cx, cy = xy(cell_free)

    # ---- the cell senders on a free cell
    for nm, mf in (("3888", O.call_3888), ("38ce", O.call_38ce), ("390e", O.call_390e)):
        add(Case("%s_%s" % (nm, tag), base, nm, dict(D0=cx, D1=cy, D2=D2),
                 lambda m: None, (lambda mf_: lambda m: mf_(m, cx, cy, D2))(mf)))

    # ---- $3248 get men: a cell holding a man of the group's side; none; wrong side; in a group (bit 6)
    other = (side % 4) + 1 if (side % 4) + 1 != side else (side % 4) + 2
    for kind in ("man", "grouped", "enemy", "building", "two", "empty"):
        c = free_cell(m0, avoid=(cell_free,))

        def setup(m, kind=kind, c=c):
            if kind == "man":
                plant(m, c, side, 0)
            elif kind == "grouped":
                plant(m, c, side, 0, flags=0x40)
            elif kind == "enemy":
                plant(m, c, other, 0)
            elif kind == "building":
                plant(m, c, side, 2)
            elif kind == "two":
                plant(m, c, side, 0, flags=0x40)
                plant(m, c, side, 0)
                plant(m, c, side, 0)
        x, y = xy(c)
        add(Case("3248_%s_%s" % (kind, tag), base, "3248", dict(D0=x, D1=y, D2=D2, D5=side), setup,
                 lambda m, x=x, y=y: O.call_3248(m, x, y, D2, side)))



def settl_records(m):
    cnt = m.wu(0x51536)
    return [a for a in range(SETTL, SETTL + cnt, 0x12) if m.bu(a + 6) in (2, 0x10)]


def rng_for(name):
    return random.Random(sum(ord(ch) * (i + 1) for i, ch in enumerate(name)))


def group_cases2(base, m0, g, add):
    """The executors that take a group (and the lead) as the caller leaves them."""
    tag = "%s_s%dk%d" % (base, g["side"], g["k"])
    D2 = g["off"]
    A3 = g["A3"]
    lead = (OBJ + P.s16(g["lead"])) & 0xfffff
    side = g["own"]
    sets = settl_records(m0)
    lords = leader_of(m0, side)
    foreign = [a for a in range(LEADERS, 0x4f914, 0x20) if m0.bu(a) not in (0, side)]
    cell_free = free_cell(m0)
    cx, cy = xy(cell_free)

    def lead_to(m, c):
        m.ww(lead + 8, ((c & 63) << 8) | 0x80)
        m.ww(lead + 10, ((c >> 6) << 8) | 0x80)

    # ---------------- $39d4 direct (D7 0/1/2, shifts), $3956 (D7 = 1 then the lord search)
    kinds = ("free", "drop", "settl_own", "settl_foreign", "bit5", "full")
    for kind in kinds:
        for D7, D0, D5 in ((1, 0, 0), (1, 2, 0), (1, 2, 5), (2, 1, 0), (0, 0, 0), (0, 3, 0), (2, 0, 0), (1, 20, 0), (1, 20, 5), (1, 0, 5)):
            if kind in ("bit5", "full") and (D7, D0) not in ((1, 0), (2, 1), (0, 3)):
                continue
            nm = "39d4_%s_d7%d_s%d_5%d_%s" % (kind, D7, D0, D5, tag)
            r = rng_for(nm)

            def setup(m, kind=kind, r=r):
                lead_to(m, cell_free)
                m.ww(A3 + 36, r.choice([0, 7, 200, 30000]))
                for i in range(8):
                    m.ww(A3 + 84 + 12 * i, r.choice([0, 0, 3, 50]))
                m.wb(lead + 44, r.choice([0, 0, 0x0e, 0x10, 0x12]))
                if kind == "drop":
                    plant_drop(m, cell_free, food=r.choice([0, 5]), goods=[r.choice([0, 0, 4]) for _ in range(8)])
                elif kind == "settl_own":
                    settl_plant(m, cell_free, lords[0])
                elif kind == "settl_foreign":
                    rec = settl_plant(m, cell_free, foreign[0] if foreign else LEADERS)
                elif kind == "bit5":
                    m.wb(lead + 7, m.bu(lead + 7) | 0x20)
                elif kind == "full":
                    for a_ in range(0x4bb4e, 0x4bdee, 28):
                        m.wb(a_ + 6, 1)
            add(Case(nm, base, "39d4", dict(A3=A3, D0=D0, D7=D7, D5=D5), setup,
                     lambda m, D0=D0, D7=D7, D5=D5: O.call_39d4(m, A3, D0, D7, D5)))

    for kind, D5 in (("free", 0), ("free", 7), ("drop", 0), ("settl_own", 0), ("none", 0)):
        nm = "3956_%s_5%d_%s" % (kind, D5, tag)
        r = rng_for(nm)

        def setup(m, kind=kind, r=r):
            lead_to(m, cell_free)
            m.ww(A3 + 36, r.choice([0, 9, 400, 30000]))
            m.ww(A3 + 60, r.choice([2, 3, 4]))
            if kind == "drop":
                plant_drop(m, cell_free, food=3)
            elif kind == "settl_own":
                settl_plant(m, cell_free, lords[0])
            elif kind == "none":
                m.wb(lead + 5, 9)
        add(Case(nm, base, "3956", dict(A1=lead, D5=D5), setup, lambda m, D5=D5: O.call_3956(m, lead, D5)))

    # ---------------- $3da4 spy arrival
    for kind in ("empty", "occupied"):
        nm = "3da4_%s_%s" % (kind, tag)

        def setup(m, kind=kind):
            rec = settl_plant(m, cell_free, foreign[0] if foreign else lords[0])
            m.wb(rec + 5, 3)
            if kind == "occupied":
                m.ww(rec + 10, (free_obj_slot(m) - OBJ) & 0xffff)
            m.ww(A3 + 24, (rec - OBJ) & 0xffff)
        add(Case(nm, base, "3da4", dict(A1=lead, A3=A3), setup, lambda m: O.call_3da4(m, lead, A3)))

    # ---------------- $5fa0 set men to work: an own leader, a foreign leader
    for kind in ("own", "foreign"):
        for L in (lords if kind == "own" else foreign)[:6]:
            nm = "5fa0_%s_%x_%s" % (kind, L, tag)
            for A5 in (0, 0x51b66 + 50 * 7):
                def setup(m, L=L):
                    m.ww(A3 + 24, (L - OBJ) & 0xffff)
                add(Case(nm + "_a5%d" % (A5 != 0), base, "5fa0", dict(A1=lead, A3=A3, A5=A5), setup,
                         lambda m, A5=A5: O.call_5fa0(m, lead, A3, A5)))

    # ---------------- $35f4 direct: the contact break-up and its marker ($3744)
    GAR, GEND = 0x4cff8, 0x4d250
    for kind in ("plain", "bit5", "blk_bld", "blk_12", "other_marker", "full_free", "full_evict", "full_none"):
        nm = "35f4_%s_%s" % (kind, tag)

        def setup(m, kind=kind):
            c = P._cell_of(m.bu(lead + 8), m.wu(lead + 10))
            if kind == "bit5":
                m.wb(lead + 7, m.bu(lead + 7) | 0x20)
            elif kind == "blk_bld":
                settl_plant(m, c, lords[0])
            elif kind == "blk_12":
                plant(m, c, 3, 6, flags=0x12)
            elif kind == "other_marker":
                plant(m, c, 3, 6, flags=0x11)
            elif kind.startswith("full"):
                m.ww(GEND, 0x258)
                for a_ in range(GAR, GEND, 10):
                    m.wb(a_ + 5, 3)
                    m.wb(a_ + 7, 0x13)
                if kind == "full_free":
                    m.wb(GAR + 70 + 5, 0)
                elif kind == "full_evict":
                    m.wb(GAR + 120 + 7, 0x11)
                    m.ww(GAR + 120 + 8, c)
        add(Case(nm, base, "35f4", dict(A3=A3), setup, lambda m: O.call_35f4(m, A3)))

    # ---------------- $600a the gatherer's deposit (mode $42 arrival)
    men_ = roster(m0, g)[:2]
    for mi, man in enumerate(men_):
        for kind in (2, 4, 6, 8, 0xa, 0xc, 0xe, 0x10):
            for food, bit6, thr in ((100, 0, 1), (0, 0, 9), (1, 0, 9), (2, 0, 9), (3, 0, 1), (0x8001, 0, 9), (100, 1, 1), (1, 1, 9)):
                if kind not in (2, 4, 0xc, 0x10) and (food, bit6, thr) not in ((100, 0, 1), (0, 0, 9), (100, 1, 1)):
                    continue
                nm = "600a_m%d_k%x_f%x_b%d_t%d_%s" % (mi, kind, food, bit6, thr, tag)
                recs = [r_ for r_ in sets if m0.bu(r_ + 6) == 2 and (OBJ + P.s16(m0.wu(r_ + 14)) if False else True)]
                rec = sets[(mi * 3 + kind) % len(sets)]
                Lr = (LEADERS + P.s16(m0.wu(rec + 14))) & 0xfffff

                def setup(m, man=man, kind=kind, food=food, bit6=bit6, thr=thr, rec=rec, Lr=Lr):
                    m.ww(man + 46, (rec - OBJ) & 0xffff)
                    m.ww(Lr + 12, kind)
                    m.ww(Lr + 6, food)
                    m.ww(Lr + 16, thr)
                    st = (SETTL + P.s16(m.wu(man + 34))) & 0xfffff
                    m.wb(man + 5, m.bu(st + 5))                         # keep $16848's owner reconcile off its assert arm
                    m.wb(man + 7, (m.bu(man + 7) & ~0x50) | (0x40 if bit6 else 0))
                    m.ww(man + 36, (rec - OBJ) & 0xffff)                # kind 4: the building whose counters tick
                    m.ww(rec + 8, [0, 1, 3][thr % 3])
                    m.ww(rec + 10, [1, 5, 0][thr % 3])
                add(Case(nm, base, "600a", dict(A1=man), setup, lambda m, man=man: O.call_600a(m, man)))

    # ---------------- $61f8 / $6128 take equipment, $63f4 trade, $6352 / $638c equipment hand-over
    def kit_world(m, r):
        """men's equipment bytes, carried stock, flag bits."""
        for a_ in [lead] + roster(m, g):
            m.wb(a_ + 33, r.choice([0, 0, 0, 8, 10]))
            m.wb(a_ + 44, r.choice([0, 0, 2, 4, 6, 0x0e, 0x10]))
            m.wb(a_ + 7, (m.bu(a_ + 7) & ~0x10) | r.choice([0, 0x10]))
        for i in range(8):
            m.ww(A3 + 84 + 12 * i, r.choice([0, 0, 0, 2, 9]))

    for kind in ("kit", "drop", "k18", "empty", "lord", "dropfood"):
        for rep in range(2):
            nm = "61f8_%s%d_%s" % (kind, rep, tag)
            r = rng_for(nm)

            def setup(m, kind=kind, r=r):
                kit_world(m, r)
                m.ww(A3 + 60, r.choice([2, 3, 4]))
                if kind == "kit":
                    plant(m, cell_free, 0, 0x0a, extra={33: r.choice([0, 8, 10]), 44: r.choice([0, 4, 6, 0x0e, 0x10])})
                    m.ww(A3 + 24, 2 * cell_free)
                elif kind == "drop":
                    plant_drop(m, cell_free, food=0, goods=[r.choice([0, 0, 5, 40]) for _ in range(8)])
                    m.ww(A3 + 24, 2 * cell_free)
                elif kind == "dropfood":
                    plant_drop(m, cell_free, food=11, goods=[r.choice([0, 3]) for _ in range(8)])
                    m.ww(A3 + 24, 2 * cell_free)
                elif kind == "k18":
                    plant(m, cell_free, 0, 0x18, flags=0x10)
                    m.ww(A3 + 24, 2 * cell_free)
                elif kind == "empty":
                    m.ww(A3 + 24, 2 * cell_free)
                elif kind == "lord":
                    L = lords[0]
                    for i in range(8):
                        m.wb(L + 24 + i, r.choice([0, 0, 6, 255]))
                    m.ww(A3 + 24, (L - OBJ) & 0xffff)
            add(Case(nm, base, "61f8", dict(A3=A3), setup, lambda m: O.call_61f8(m, A3)))

    for rep in range(6):
        nm = "63f4_%d_%s" % (rep, tag)
        r = rng_for(nm)
        L = r.choice(lords + foreign)

        def setup(m, r=r, L=L):
            kit_world(m, r)
            m.ww(A3 + 24, (L - OBJ) & 0xffff)
            m.ww(A3 + 60, r.choice([2, 3, 4, 2, 3, 4, 0]))
            m.ww(A3 + 36, r.choice([0, 50, 400, 2000]))
            for i in range(8):
                m.wb(L + 24 + i, r.choice([0, 0, 3, 40, 255]))
            m.ww(L + 6, r.choice([0, 100]))
            for i in range(8):
                m.ww(A3 + 84 + 12 * i, r.choice([0, 0, 0, 2, 9, 120]))
        add(Case(nm, base, "63f4", dict(A3=A3), setup, lambda m: O.call_63f4(m, A3)))

    for rep in range(10):
        D3 = (2, 4, 6, 8, 10, 12, 14, 16)[rep % 8]
        nm = "6352_%d_%s" % (rep, tag)
        r = rng_for(nm)
        amt = r.choice([1, 2, 5, 9])
        D5 = 12 * (D3 // 2 - 1)

        def setup(m, r=r):
            kit_world(m, r)
        add(Case(nm, base, "6352", dict(A3=A3, D2=amt, D3=D3, D5=D5), setup,
                 lambda m, amt=amt, D3=D3, D5=D5: {"D2": O.call_6352(m, A3, amt, D3, D5)}, regs=("D2",)))

    for rep in range(10):
        D3 = (2, 4, 6, 8, 10, 12, 14, 16)[rep % 8]
        nm = "638c_%d_%s" % (rep, tag)
        r = rng_for(nm)
        amt = r.choice([1, 2, 5])
        who = [lead] + roster(m0, g)
        A2 = r.choice(who)

        def setup(m, r=r):
            kit_world(m, r)
        add(Case(nm, base, "638c", dict(A3=A3, A2=A2, D2=amt, D3=D3), setup,
                 lambda m, amt=amt, D3=D3, A2=A2: {"D2": O.call_638c(m, A3, A2, amt, D3)}, regs=("D2",)))


def settl_plant(m, cell, leader):
    """A settlement-type record (byte6 2) linked into `cell`, led by `leader`: planted in an unused OBJ slot (the model
    and the routine only read byte 6, 5, 14 and the chain)."""
    a = plant(m, cell, 0, 2, extra={14: (leader - LEADERS) & 0xff})
    m.ww(a + 14, (leader - LEADERS) & 0xffff)
    return a


def misc_cases(base, m0, add):
    """Routines keyed on registers only: $3bc8, $60dc, $311a, $6128, $4a7a."""
    lords = [a for a in range(LEADERS, 0x4f914, 0x20) if m0.bu(a)]
    gs = [g for g in groups(bytes(m0.r)) if g["men"] > 0]
    for sd in (0, 1, 2, 3, 4, 9):
        for off in (6, 8):
            for zero in (False, True):
                nm = "3bc8_s%d_o%d_z%d_%s" % (sd, off, zero, base)

                def setup(m, zero=zero, off=off):
                    if zero:
                        for L in range(LEADERS, 0x4f914, 0x20):
                            m.ww(L + off, 0)
                add(Case(nm, base, "3bc8", dict(D2=sd, D3=off), setup,
                         lambda m, sd=sd, off=off: dict(zip(("A0", "D0", "D4"), O.call_3bc8(m, sd, off))), regs=("A0", "D0", "D4")))
    for L in lords[:8]:
        for kind in (2, 4, 6, 8, 0xa, 0xc, 0xe, 0x10):
            for thr in (1, 5, 0):
                nm = "60dc_%x_k%x_t%d_%s" % (L, kind, thr, base)
                r = rng_for(nm)

                def setup(m, L=L, kind=kind, thr=thr, r=r):
                    m.ww(L + 12, kind)
                    m.ww(L + 16, thr)
                    for i in range(8):
                        m.wb(L + 24 + i, r.choice([0, 7, 255]))
                add(Case(nm, base, "60dc", dict(A3=L), setup, lambda m, L=L: O.call_60dc(m, L)))
    r = random.Random(11)
    for rep in range(24):
        sd, d1, sd2 = r.choice([0, 1, 2, 3, 4, 200]), r.choice([2, 2, 2, 100, 0xfffe, 0xff9c]), r.choice([0, 1, 2, 3, 4, 255])
        nm = "311a_%d_%s" % (rep, base)
        v15 = r.choice([0, 10, 98, 99, 100, 150, 0x9c, 255])

        def setup(m, sd=sd, sd2=sd2, v15=v15):
            A5 = 0x580a6 + ((P.s8(sd) * 0x20) & 0xffff)
            m.wb(A5 + 15 + P.s8(sd2), v15)
        add(Case(nm, base, "311a", dict(D0=sd, D1=d1, D2=sd2), setup, lambda m, sd=sd, d1=d1, sd2=sd2: O.call_311a(m, sd, d1, sd2)))

    # ---- the cell scanners: $4a7a (march and engage) and $6128 (take equipment)
    g = gs[0]
    D2 = g["off"]
    side = g["own"]
    other = (side % 4) + 1 if (side % 4) + 1 != side else (side % 4) + 2
    L0 = (lords[0] - LEADERS) & 0xffff
    combos = {
        "bld_enemy": [("b", other)], "bld_own": [("b", side)], "man_enemy": [("m", other)], "man_own": [("m", side)],
        "man_neutral": [("m", 0)], "man_dead": [("m", 0xff)], "two_men": [("m", other), ("m", 3 if other != 3 else 4)],
        "a4_kind8": [("c", 8)], "a4_kind14": [("c", 0x14)], "a4_kind16": [("c", 0x16)], "a5_kind4": [("c", 4)],
        "bld_after_men": [("m", other), ("b", other)], "men_after_bld": [("b", other), ("m", other)],
        "man_beats_a4": [("c", 8), ("m", other)], "a4_beats_a5": [("c", 4), ("c", 8)], "a5_a4_a4": [("c", 4), ("c", 0x14), ("c", 0x16)],
        "kind0e": [("e", other)], "own_bld_enemy_man": [("b", side), ("m", other)], "none": [],
    }
    for nm_, items in combos.items():
        c = free_cell(m0)
        x, y = xy(c)

        def setup(m, items=items, c=c):
            for k, v in items:
                if k == "b":
                    settl_plant(m, c, lords[0])
                    # settl_plant makes side 0: set the owner
                    a_ = m.wu(P.BUCKETS + 2 * c)
                    m.wb(OBJ + P.s16(a_) + 5, v)
                elif k == "m":
                    plant(m, c, v, 0)
                elif k == "e":
                    plant(m, c, v, 0x0e)
                elif k == "c":
                    plant(m, c, 0, v, extra={})
                    a_ = OBJ + P.s16(m.wu(P.BUCKETS + 2 * c))
                    m.ww(a_ + 10, ((c & 0x1fc0) | 0) | 0)
        add(Case("4a7a_%s_%s" % (nm_, base), base, "4a7a", dict(D0=x, D1=y, D2=D2), setup,
                 lambda m, x=x, y=y: O.call_4a7a(m, x, y, D2)))
        for kind in ("a", "b"):
            pass
    # $6128
    kinds6 = {
        "kit": [(0x0a, 0)], "drop": [(0x2c, 0)], "k18_10": [(0x18, 0x10)], "k18_other": [(0x18, 0x00)], "none": [(0x05, 0)],
        "k18_ctl1": [(0x18, 0x10)], "k18_ctl65": [(0x18, 0x10)], "empty": [],
    }
    for nm_, items in kinds6.items():
        c = free_cell(m0)
        x, y = xy(c)

        def setup(m, items=items, c=c, nm_=nm_):
            for b6, b7 in items:
                plant(m, c, 0, b6, flags=b7)
            if nm_ == "k18_ctl1":
                m.wb(0x3f86c + c + 1, 1)
            if nm_ == "k18_ctl65":
                m.wb(0x3f86c + c + 65, 1)
        add(Case("6128_%s_%s" % (nm_, base), base, "6128", dict(D0=x, D1=y, D2=D2), setup,
                 lambda m, x=x, y=y: {"D0": O.call_6128(m, x, y, D2)}, regs=("D0",)))


def nat_cases(cases):
    """Natural entries: nat/<name>.json from nat_capture.sh (player clicks) and tools/capture_hits.py (the land runs)."""
    for jf in sorted(NAT.glob("*.json")):
        stem = jf.stem
        if not stem.startswith("n"):
            continue
        entries = json.load(open(jf))
        target = {"n3888": "3888", "n390e": "390e", "n4a7a": "4a7a", "n38ce": "38ce", "n3248": "3248", "n6128": "6128",
                  "n600a": "600a", "n39d4": "39d4", "n35f4": "35f4", "n5fa0": "5fa0", "n61f8": "61f8",
                  "n63f4": "63f4", "n3da4": "3da4", "n3956": "3956"}[stem.split("_")[0]]
        for e in entries:
            R = e["regs"]
            base = "nat_%s_%d" % (stem, e["hit"])
            BASES[base] = e["snap"]
            nm = base
            if target in ("3888", "38ce", "390e", "4a7a", "6128"):
                fn = {"3888": O.call_3888, "38ce": O.call_38ce, "390e": O.call_390e, "4a7a": O.call_4a7a, "6128": O.call_6128}[target]
                regs = ("D0",) if target == "6128" else ()
                pre = dict(D0=R["D0"], D1=R["D1"], D2=R["D2"])
                cases[base].append(Case(nm, base, target, pre, lambda m: None,
                                        (lambda fn_, R_: (lambda m: {"D0": fn_(m, R_["D0"], R_["D1"], R_["D2"])} if fn_ is O.call_6128
                                                          else fn_(m, R_["D0"], R_["D1"], R_["D2"])))(fn, R), regs=regs))
            elif target == "3248":
                cases[base].append(Case(nm, base, "3248", dict(D0=R["D0"], D1=R["D1"], D2=R["D2"], D5=R["D5"]), lambda m: None,
                                        lambda m, R=R: O.call_3248(m, R["D0"], R["D1"], R["D2"], R["D5"])))
            elif target == "39d4":
                # the natural entry of the drop-food icon ($6c96): its own D0 (shift), D7 = 1 and its stale D5; the army's food varied
                for food in (None, 0, 1, 2):
                    nm2 = nm + ("" if food is None else "_food%d" % food)

                    def setup(m, food=food, R=R):
                        if food is not None:
                            m.ww(R["A3"] + 36, food)
                    cases[base].append(Case(nm2, base, "39d4", dict(A3=R["A3"], D0=R["D0"], D7=R["D7"], D5=R["D5"]), setup,
                                            lambda m, R=R: O.call_39d4(m, R["A3"], R["D0"], R["D7"], R["D5"] & 0xffff)))
                # the lead standing in the open (a free cell): food 0 / 1 shifted to nothing, with the natural stale D5
                for food in (0, 1, 2, 300):
                    def setup2(m, food=food, R=R):
                        lead_ = (OBJ + P.s16(m.wu(R["A3"] - 12))) & 0xfffff
                        c = free_cell(m)
                        m.ww(lead_ + 8, ((c & 63) << 8) | 0x80)
                        m.ww(lead_ + 10, ((c >> 6) << 8) | 0x80)
                        m.ww(R["A3"] + 36, food)
                    cases[base].append(Case(nm + "_open_food%d" % food, base, "39d4",
                                            dict(A3=R["A3"], D0=R["D0"], D7=R["D7"], D5=R["D5"]), setup2,
                                            lambda m, R=R: O.call_39d4(m, R["A3"], R["D0"], R["D7"], R["D5"] & 0xffff)))
            elif target == "5fa0":
                cases[base].append(Case(nm, base, "5fa0", dict(A1=R["A1"], A3=R["A3"], A5=R["A5"]), lambda m: None,
                                        lambda m, R=R: O.call_5fa0(m, R["A1"], R["A3"], R["A5"])))
            elif target == "61f8":
                cases[base].append(Case(nm, base, "61f8", dict(A3=R["A3"]), lambda m: None, lambda m, R=R: O.call_61f8(m, R["A3"])))
            elif target == "63f4":
                cases[base].append(Case(nm, base, "63f4", dict(A3=R["A3"]), lambda m: None, lambda m, R=R: O.call_63f4(m, R["A3"])))
            elif target == "3da4":
                cases[base].append(Case(nm, base, "3da4", dict(A1=R["A1"], A3=R["A3"]), lambda m: None,
                                        lambda m, R=R: O.call_3da4(m, R["A1"], R["A3"])))
            elif target == "3956":
                cases[base].append(Case(nm, base, "3956", dict(A1=R["A1"], D5=R["D5"]), lambda m: None,
                                        lambda m, R=R: O.call_3956(m, R["A1"], R["D5"] & 0xffff)))
            elif target == "35f4":
                cases[base].append(Case(nm, base, "35f4", dict(A3=R["A3"]), lambda m: None,
                                        lambda m, R=R: O.call_35f4(m, R["A3"])))
            elif target == "600a":
                cases[base].append(Case(nm, base, "600a", dict(A1=R["A1"]), lambda m: None,
                                        lambda m, R=R: O.call_600a(m, R["A1"])))


def build_cases():
    cases = collections.defaultdict(list)
    rams = {b: ram_from_snap(str(ROOT / s)) for b, s in BASES.items()}
    for base, ram in rams.items():
        P.init_tables(ram)
        m0 = P.Mem(ram)
        for g in groups(ram):
            if g["men"] == 0:
                continue
            group_cases(base, m0, g, cases[base].append)
            group_cases2(base, m0, g, cases[base].append)
        misc_cases(base, m0, cases[base].append)
    nat_cases(cases)
    return cases, rams


def main():
    cases, rams = build_cases()
    tot = ok = n = 0
    arms = collections.Counter()
    per = collections.defaultdict(lambda: [0, 0, 0, 0])
    fails = []
    for base, cs in cases.items():
        cs = [c for c in cs if not only or only in c.name]
        if not cs:
            continue
        ram0, meta = run_base(base, cs)
        for c, pk in meta:
            o, t, probs, tr = judge(c, ram0, pk)
            per[c.target][0] += 1
            per[c.target][1] += o
            per[c.target][2] += t
            if c.name.startswith("nat_"):
                per[c.target][3] += 1
            arms.update(tr)
            tot += t
            ok += o
            n += 1
            st = "ok" if not probs else "FAIL"
            print("%-28s %4d/%-4d %s %s" % (c.name, o, t, st, " ".join(tr)))
            for p in probs:
                print("      ", p)
            if probs:
                fails.append(c.name)
    print("\nBYTES+REGS %d/%d over %d states; arms %s" % (ok, tot, n, dict(arms)))
    print("per routine (states, matched/total bytes+regs, natural-entry states):")
    for t_, (n_, o_, tt_, nat_) in sorted(per.items()):
        print("  $%-5s %4d states  %6d/%-6d  %d natural" % (t_, n_, o_, tt_, nat_))
    print("FAILED:", fails)


if __name__ == "__main__":
    main()
