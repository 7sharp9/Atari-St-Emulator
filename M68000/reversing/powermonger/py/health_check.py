"""health_check.py <snap> [<snap> ...]: byte 45 of an entity record is health.

Two checks, the pm134 audit's claim "byte 45 = health, not strength/morale" turned into counts:

1. Panel (live `callcap $912a`): the captain panel's health word. $912a computes
   `(45(rec) >> 4) & 7` (8 if 5(rec) < 0) and returns A5 = $a2dc + 9 + byte[$a2dc + index], the string
   "Very Sickly" ... "Very Strong", "Dead". The script pokes byte 45 of one live record to 10 values (and byte 5 negative once),
   calls $912a from the snapshot with A3 = a scratch frame whose word at 64 is the record's offset, and
   compares the returned string address with the table read from RAM.
2. Cap census (RAM only): $5c80 raises byte 45 by one random bit per tick while it is below the per-job cap
   `byte[$5ccc + (7(rec) & $1f)]` (soldier 90, farmer 82, merchant 69, fisher 79, shepherd 72, leader 95); count how many live
   persons sit exactly on their cap (the rest are mid-climb, or past the age term that lowers the cap).

Run from M68000/ (stage 1 writes the REPL script, runs the emulator, stage 2 compares).
Needs a built bin/Debug/net8.0/M68000.dll and scratchpad/powermonger.st.  Output under ${PM_WORK:-scratchpad/pmwork}/health/.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap  # noqa: E402

OBJ, STRIDE = 0x51b66, 50
CAPS, HEALTH = 0x5ccc, 0xa2dc
WORK = ROOT / os.environ.get('PM_WORK', 'scratchpad/pmwork') / 'health'
WORK.mkdir(parents=True, exist_ok=True)


def live(ram):
    # live persons as job_census.py: array of 512 records, side byte 5 in 1..127, category byte 6 = 0
    return [k for k in range(512) if 0 < ram[OBJ + k * STRIDE + 5] < 128 and ram[OBJ + k * STRIDE + 6] == 0]


def census(snap):
    ram = ram_from_snap(Path(snap))
    on = tot = 0
    for k in live(ram):
        a = OBJ + k * STRIDE
        cap = ram[CAPS + (ram[a + 7] & 0x1f)]
        tot += 1
        on += ram[a + 45] == cap
    return on, tot


def panel(snap):
    ram = ram_from_snap(Path(snap))
    k = live(ram)[1]
    a, a3 = OBJ + k * STRIDE, 0x7f000
    cmds = ['w %x %08x' % (a3 + 64, (k * STRIDE) << 16)]
    cases = []
    for v in (0x00, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x7f, 0xf0):
        b = bytearray(ram[a + 44:a + 48]); b[1] = v
        cmds += ['w %x %s' % (a + 44, b.hex()), 'callcap 912a 1000 - A3=%x' % a3]
        cases.append(((v >> 4) & 7, v))
    b = bytearray(ram[a + 4:a + 8]); b[1] = 0x80          # byte 5 < 0 (dying) -> "Dead"
    cmds += ['w %x %s' % (a + 4, b.hex()), 'callcap 912a 1000 - A3=%x' % a3, 'q']
    cases.append((8, 0x80))
    cf = WORK / (Path(snap).stem + '.cmds')
    cf.write_text('\n'.join(cmds) + '\n')
    env = dict(os.environ, ATARI_NOTRACE='1')
    out = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a',
                          'scratchpad/powermonger.st'], stdin=cf.open(), capture_output=True, text=True, cwd=ROOT, env=env)
    got = [int(l.split('A5 ')[1].split('->')[1].split()[0].lstrip('$'), 16)
           for l in (out.stdout + out.stderr).splitlines() if l.startswith('regdelta') and 'A5 ' in l]
    ok = 0
    for (idx, v), a5 in zip(cases, got):
        exp = HEALTH + 9 + ram[HEALTH + idx]
        ok += a5 == exp
        s = bytes(ram[exp:exp + 12]).split(b'\0')[0].decode()
        print('  byte45 %02x idx %d -> A5 $%x (%s) %s' % (v, idx, a5, s, 'ok' if a5 == exp else 'EXPECTED $%x' % exp))
    print('panel: %d of %d callcaps return the healthnames string' % (ok, len(cases)))


for s in sys.argv[1:]:
    on, tot = census(s)
    print('%s: %d of %d live records at their $5ccc cap' % (s, on, tot))
panel(sys.argv[1])
