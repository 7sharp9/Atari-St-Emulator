"""Gate: the Populous II computer god $25652 against its Python model (god_model.py).

At every natural entry of $25652 in a run from a snapshot (stserver `run until_pc`), fork, read RAM, call the
routine ($25652 under `call`, interrupts masked), read RAM again, restore, and compare the set of bytes the
routine changed with the model's. Optional --poke ADDR:WIDTH:VALUE,... applied to the whole run from the start
(labelled in the output); --variants applies per-state pokes to the forked state only (plan list, counts) and
re-reads RAM so the model sees the same poked state.

usage: uv run python reversing/populous2/py/god/god_gate.py <snap> <ticks> [--poke a:w:v,...] [--variants] [--control NAME]
"""
import os, sys, json, collections
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, "tools", "rdis.py")):
    nd = os.path.dirname(d)
    if nd == d: sys.exit("cannot find M68000/")
    d = nd
ROOT = d
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stclient import StServer
from god_model import God

N_RAM = 0x48000
ENT_BASE = 0x3FF1A
SIDES = (0x470FE, 0x47238)


def variants(s, ram):
    """Per-state pokes (labelled variants) returned as (name, [(addr,width,value)])."""
    w = lambda a: int.from_bytes(ram[a:a + 2], "big")
    out = []
    for si, b in enumerate(SIDES):
        pk = [(b + 26, 2, 4), (b + 76, 2, 1), (b + 104, 2, 0), (b + 0, 4, 100000), (b + 24, 2, si + 1)]
        # plan list: slots 1..6 hold (power, kind) with every kind 0,2,4,6,8,10; powers from the side's own list
        plan = [(0x6, 0), (0x6, 2), (0x6, 4), (0x6, 6), (0x6, 8), (0x48, 0xA)]
        for i, (p_, k) in enumerate(plan):
            pk += [(b + 156 + 4 * i, 2, p_), (b + 158 + 4 * i, 2, k)]
        for slot in range(1, 7):
            name = f"side{si+1}_plan_slot{slot}_kind{plan[slot-1][1]}"
            extra = [(b, 4, 1000000), (b + 4, 4, 5000), (SIDES[1 - si] + 4, 4, 10)] if slot == 6 else []
            out.append((name, pk + extra + [(b + 148, 2, 7), (b + 38, 2, 4 * slot), (0x3979A, 4, 400)]))
        w30 = int.from_bytes(ram[b + 30:b + 32], "big")
        fb = [(b + 26, 2, 4), (b + 76, 2, 1), (b + 104, 2, 0), (b + 24, 2, si + 1)]
        out.append((f"side{si+1}_flush_entity_cmd", fb + [(b + 54, 2, w30)]))
        out.append((f"side{si+1}_flush_queued_power", fb + [(b + 56, 2, 6), (b + 58, 2, 0x0A0B), (b, 4, 100000)]))
        out.append((f"side{si+1}_flush_queued_power_short", fb + [(b + 56, 2, 6), (b + 58, 2, 0x0A0B), (b, 4, 0)]))
        out.append((f"side{si+1}_flush_queued_power_32", fb + [(b + 56, 2, 0x32), (b + 58, 2, 0x0A0B), (b, 4, 100000)]))
        out.append((f"side{si+1}_flush_walker_mailbox_ctl12", fb + [(b + 26, 2, 0x12), (b + 50, 2, 1), (b + 52, 2, 0x0C0D)]))
        out.append((f"side{si+1}_level_ctl12", fb + [(b + 26, 2, 0x12), (b + 46, 2, w30), (b + 44, 2, 1), (b, 4, 100000)]))
    # magnet and mode: own settlement count above 30, leader present, with and without the enemy's settlement
    for si, b in enumerate(SIDES):
        base = [(b + 26, 2, 4), (b + 76, 2, 1), (b + 104, 2, 0), (b + 36, 2, 40), (b + 0, 4, 100000)]
        out.append((f"side{si+1}_magnet_count40", base))
        out.append((f"side{si+1}_magnet_mode10", base + [(b + 12, 2, 0x10)]))
        lead = base + [(b + 8, 2, int.from_bytes(ram[b + 30:b + 32], "big"))]
        ent = ENT_BASE + (lambda o: o - 0x10000 if o & 0x8000 else o)(int.from_bytes(ram[b + 30:b + 32], "big"))
        lead += [(ent + 26, 4, 0x3000), (b + 10, 2, int.from_bytes(ram[b + 34:b + 36], "big")), (b + 150, 2, 2)]
        eb = SIDES[1 - si]
        w34s = int.from_bytes(ram[b + 34:b + 36], "big")
        w34e = int.from_bytes(ram[eb + 34:eb + 36], "big")
        for strength, tgt, tname in ((0x3000, w34e, "strong"), (0x100, w34s, "weak"), (0x3000, w34s, "strong_far")):
            for w12 in (0, 0x10):
                for w40 in (1, 5):
                    out.append((f"side{si+1}_magnet_{tname}_w12_{w12:x}_w40_{w40}",
                                lead[:-3] + [(ent + 26, 4, strength), (b + 10, 2, tgt), (b + 150, 2, 2), (b + 12, 2, w12), (b + 40, 2, w40)]))
        out.append((f"side{si+1}_power_k8_leader", [(b + 26, 2, 4), (b + 76, 2, 1), (b + 104, 2, 0), (b + 0, 4, 100000), (b + 8, 2, int.from_bytes(ram[b + 30:b + 32], "big")), (ent + 26, 4, 0x3000), (b + 148, 2, 7), (b + 156, 2, 6), (b + 158, 2, 8), (b + 38, 2, 4), (0x3979A, 4, 400)]))
        out.append((f"side{si+1}_magnet_lowcount_mode10", [(b + 26, 2, 4), (b + 76, 2, 1), (b + 104, 2, 0), (b + 12, 2, 0x10), (b + 36, 2, 5)]))
    return out


def main():
    a = sys.argv[1:]
    snap, ticks = a[0], int(a[1])
    pokes = []
    if "--poke" in a:
        for t in a[a.index("--poke") + 1].split(","):
            ad, wd, v = (int(x, 0) for x in t.split(":"))
            pokes.append((ad, wd, v))
    control = tuple(a[a.index("--control") + 1].split(",")) if "--control" in a else ()
    do_var = "--variants" in a
    s = StServer(ROOT)
    s("load", snapshot=snap)
    for ad, wd, v in pokes:
        s("poke", addr=ad, width=wd, value=v)
    stage = collections.Counter()
    ok = bad = states = nontrivial = 0
    first_bad = []
    cmd_posts = collections.Counter()
    paths = collections.Counter()
    for t in range(ticks):
        r = s("run", max_steps=3_000_000, until_pc=0x25652)
        if r["reason"] != "until":
            print("run stopped:", r); break
        fid = s("fork")["id"]
        regs0 = s("regs")
        d4, d5 = int(regs0["d4"].lstrip("$"), 16), int(regs0["d5"].lstrip("$"), 16)
        cases = [("natural", [])] + (variants(s, s.read(0, N_RAM)) if do_var and t % 7 == 0 else [])
        for name, pk in cases:
            for ad, wd, v in pk:
                s("poke", addr=ad, width=wd, value=v)
            ram0 = s.read(0, N_RAM)
            try:
                s.call(0x25652)
            except SystemExit as e:
                print('call did not return:', name, e)
                s('restore', id=fid); continue
            ram1 = s.read(0, N_RAM)
            sp = s.sp
            real = {i: ram1[i] for i in range(N_RAM) if ram1[i] != ram0[i] and not (sp - 512 <= i < sp + 8)}
            m = God(ram0, d4, d5, control)
            try:
                want = m.run()
            except ValueError as e:
                want = {"err": str(e)}
            want = {i: v for i, v in want.items() if not (isinstance(i, int) and sp - 512 <= i < sp + 8)}
            states += 1
            if want == real:
                ok += 1
            else:
                bad += 1
                if len(first_bad) < 6:
                    diff = sorted(set(real.items()) ^ set(want.items()))[:10]
                    first_bad.append((t, name, [(hex(i), v) for i, v in diff]))
            paths.update(m.paths)
            posted = [(hex(x), n) for x, n, p in m.log if p]
            for x, n, p in m.log:
                if p: stage[n] += 1
            cmds = [ram1[0x473B0 + 10 * k + 1] for k in range(2)]
            if real: nontrivial += 1
            s("restore", id=fid)
        s("drop", id=fid)
    print(f"states {states}: model equals callcap (changed bytes, both sides) {ok}/{states}"
          f"{'  [control ' + ','.join(control) + ']' if control else ''}; states with any change {nontrivial}")
    print("stages that posted (model):", dict(stage))
    print("paths taken (model):", dict(sorted(paths.items())))
    for fb in first_bad: print("  mismatch", fb)
    s.close()


main()
