"""compare.py: diff two 1 MB RAM dumps written by renderskip.py at the same tick index.

    compare.py <a.ram> <b.ram> [--ignore 57fee:4,...] [--json] [--ranges 30]

Prints, per named simulation region, the number of differing bytes (with the first few addresses and values), then
the differing bytes outside every simulation region as merged ranges labelled with the known render/ISR areas they
fall in, so "the simulation state is equal" is told apart from "nothing differs". Exit status 0 when every
simulation region is equal, 1 otherwise.

Simulation regions (the state the tick's sim routines own; each from a doc):
  lords        $4e514 + 160 x 32          economy.md 1 / commander observe.py LORDS
  settlements  $4f916 + 400 x 18          economy.md 3 / observe.py SETTL
  groups       $51538 .. $51b66 (5 x $13c) strategy.md "$51538 - group-order table"
  objects      $51b66 .. $57f98 (511 x 50) graphics.md "Isometric renderer, measured" ($14b62 walks $51b66+$32..$57f66)
  globals      $57f98 .. $58058 and        $57fba force totals, $57fce ratio, $57fec season count, $57ff6 LCG,
                                           $58016 command buffer, $58042 acting group, $580a0 world seed,
                                           $580cc/$5812c peace bits (strategy.md)
  globals2     $58078 .. $58200            (the rest of that block)
Not simulation: $58058 .. $58078 `_channel` (powermonger.sym), 16 words cleared by `_start_s` $126d6 / `_stop_so`
$12726 and read by the sound dispatcher `_do_soun` $127e6, the only code holding the absolute address (raw scan of the
text segment); the dispatcher stamps sound expiry times from the VBL counter $6f304, which a stub changes.
  rng_seed     $2df84 .. $2df88            strategy.md "RNG and determinism" (_seed)
  clocks       $2df70 .. $2df78            sim clock $2df70 (strategy.md "Where it runs")
  camera_tick  $4bb3a .. $4bb42            camera cell, master tick $4bb3e
  cell_heads   $47970 .. $4b970            per-cell entity list heads, 64 x 128 words (graphics.md $115e0 / $163ea)
  terrain      $418ad .. $45930            colour planes A ($418ad) and B ($438ee), 8257 each (graphics.md $1648e)
The RNG fields are reported on their own as well (rng: $57ff6 LCG, $57fec season count, $2df84 seed).
"""
import json, sys

SIM = [
    ('lords', 0x4e514, 0x4e514 + 160 * 32),
    ('settlements', 0x4f916, 0x4f916 + 400 * 18),
    ('groups', 0x51538, 0x51b66),
    ('objects', 0x51b66, 0x57f98),
    ('globals', 0x57f98, 0x58058),
    ('globals2', 0x58078, 0x58200),
    ('rng_seed', 0x2df84, 0x2df88),
    ('clocks', 0x2df70, 0x2df78),
    ('camera_tick', 0x4bb3a, 0x4bb42),
    ('cell_heads', 0x47970, 0x4b970),
    ('terrain', 0x418ad, 0x45930),
]
RNG = [('lcg_57ff6', 0x57ff6, 2), ('season_57fec', 0x57fec, 2), ('seed_2df84', 0x2df84, 4)]
# Known non-simulation areas, for labelling the outside diff (not exhaustive).
LABELS = [
    ('vectors+sysvars', 0x0, 0x10a6),
    ('game text/data', 0x10a6, 0x1c48e),
    ('bss low', 0x1c48e, 0x2df70),
    ('hud_master $78000', 0x78000, 0x78000 + 32000),
    ('sound _channel', 0x58058, 0x58078),
]


def label(a):
    for n, lo, hi in LABELS + SIM:
        if lo <= a < hi:
            return n
    return '?'


def ranges(diff, gap=16):
    out = []
    for a in diff:
        if out and a - out[-1][1] <= gap:
            out[-1][1] = a; out[-1][2] += 1
        else:
            out.append([a, a, 1])
    return out


def main(argv):
    a = list(argv)
    opt = lambda name, d: (a.pop(a.index(name) + 1), a.remove(name))[0] if name in a else d
    ign = opt('--ignore', '')
    nr = int(opt('--ranges', '30'))
    as_json = '--json' in a
    if as_json:
        a.remove('--json')
    A, B = open(a[0], 'rb').read(), open(a[1], 'rb').read()
    ignored = set()
    for t in filter(None, ign.split(',')):
        lo, n = t.split(':'); lo = int(lo, 16)
        ignored.update(range(lo, lo + int(n)))
    diff = [i for i in range(min(len(A), len(B))) if A[i] != B[i] and i not in ignored] if A != B else []
    dset = set(diff)
    res = dict(total=len(diff), sim={}, rng={}, outside=[])
    for n, lo, hi in SIM:
        d = [i for i in diff if lo <= i < hi]
        res['sim'][n] = dict(bytes=len(d), first=[(hex(i), A[i], B[i]) for i in d[:6]])
    for n, ad, w in RNG:
        res['rng'][n] = dict(a=A[ad:ad + w].hex(), b=B[ad:ad + w].hex(), equal=A[ad:ad + w] == B[ad:ad + w])
    insim = lambda i: any(lo <= i < hi for _, lo, hi in SIM)
    outside = [i for i in diff if not insim(i)]
    res['outside_bytes'] = len(outside)
    res['outside'] = [dict(lo=hex(lo), hi=hex(hi), changed=c, label=label(lo)) for lo, hi, c in ranges(outside)]
    sim_equal = all(v['bytes'] == 0 for v in res['sim'].values())
    res['sim_equal'] = sim_equal
    if as_json:
        print(json.dumps(res))
    else:
        print(f'total differing bytes {len(diff)}; simulation regions {"EQUAL" if sim_equal else "DIFFER"}')
        for n, v in res['sim'].items():
            print(f'  {n:12s} {v["bytes"]:6d}' + (f'  first {v["first"]}' if v['bytes'] else ''))
        for n, v in res['rng'].items():
            print(f'  rng {n:13s} a={v["a"]} b={v["b"]} {"equal" if v["equal"] else "DIFFER"}')
        print(f'  outside the simulation regions: {len(outside)} bytes in {len(res["outside"])} ranges')
        for r in res['outside'][:nr]:
            print(f'    {r["lo"]}..{r["hi"]} {r["changed"]} [{r["label"]}]')
    return 0 if sim_equal else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
