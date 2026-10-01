"""join08_watch.py <mode> [args]: REPL script generator for the join run, resumed from <outdir>/clicked.snap
(made by join08_cmds.py; the lead is marching to the town with group state 3).
  hits <steps> <snap-out>      : bp at the lead's arrival ($15122), dump the before-state, count hits over <steps>
                                 on the whole join path, dump the after-state, snapshot
  trace <steps> <every> <men.. > : bp at $15122, then every <every> steps dump mode bytes of the listed man
                                 offsets (hex, e.g. 64,32), the lead and the group record, lord 0's troops_field
Dumps use `m` (hex bytes); parse them with join08_report.py."""
import sys

LEAD = 0x51f80
GRP = 0x51538 + 0x188
LORD0 = 0x4e514
OBJ = 0x51b66
PATH = "15122 34f2 15264 1501a 15282 1b2a 1d70 3c08 35f4 14f08 15302 14fdc 5bd2 1b8c"


def dump(men, tag):
    o = [f"echo {tag}"] if False else []
    o.append(f"m {LEAD:x} 50")
    o.append(f"m {GRP-48:x} 52")          # -48 .. +4 of the group record (owner, first man, men, lead, state)
    o.append(f"m {GRP+24:x} 2")           # target link
    o.append(f"m {LORD0:x} 32")
    for m in men:
        o.append(f"m {OBJ+m:x} 50")
    return o


mode = sys.argv[1]
men = [0x32, 0x64, 0xc8, 0xfa, 0x12c, 0x15e]   # records 1, 2, 4, 5, 6, 7 (4 of them are live side-1 men)
out = ["bp 15122 60000000"]
if mode == 'hits':
    steps = int(sys.argv[2]); snap = sys.argv[3]
    out += dump(men, 'before')
    out += [f"hits {steps} {PATH}"]
    out += dump(men, 'after')
    out += [f"snap {snap}", "q"]
elif mode == 'trace':
    steps = int(sys.argv[2]); every = int(sys.argv[3])
    if len(sys.argv) > 4:
        men = [int(x, 16) for x in sys.argv[4].split(',')]
    out += dump(men, 'step0')
    for _ in range(steps // every):
        out += [f"s {every}"] + dump(men, 'x')
    out += ["q"]
print('\n'.join(out))
