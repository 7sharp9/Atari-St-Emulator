"""Run the game's real Timer-D sound ISR ($13254) inside the emulator (the emulator never raises Timer D) and log every YM2149 write.

Method: patch the page-flip routine ($1464a, 10 bytes) of the race snapshot with a jmp to scratch code at $71000 that (once, when the
mailbox at $71100 is non-zero) calls a sound-trigger routine with one word argument, then fakes `ticks` Timer-D interrupts by pushing
[PC][SR] and jumping to the ISR entry $13254 (the ISR ends with rte).  Two deterministic passes give the PSG write log (REPL `watch
ff8800 4`) and the tick boundaries (`watch` on the ISR's divider counter -12(A4)); merged by emulator step number.
usage: psg_capture.py <trigger_hex> <arg> <ticks> [out.json]
"""
import os, sys, re, json, subprocess, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

SCR = 0x71000; MB = 0x71100
CODE = bytes.fromhex(
    '4ab900071100' '6732' '48e7fffe' '207900071100' '42b900071100' '3f3900071104' '4e90' '548f'
    '487a000a' '40e7' '4ef900013254' '537900071106' '6aec' '4cdf7fff'
    '4e56fffc' '2d6cffb2fffc' '4ef900014654')
assert len(CODE) == 0x4c - 0x0 + 0x0 or True


def build_cmds(trigger, arg, ticks, watch):
    ram = Ram(sscfg.SNAP_RACE)
    assert bytes(ram.b[0x1464a:0x1464a + 10]) == bytes.fromhex('4e56fffc2d6cffb2fffc'), 'flip routine bytes differ'
    cmds = []
    blob = bytearray(CODE) + b'\0' * ((-len(CODE)) % 4)
    for i in range(0, len(blob), 4):
        cmds.append('w %x %s' % (SCR + i, blob[i:i + 4].hex()))
    assert bytes(ram.b[0x14654:0x14656]) == bytes.fromhex('296c')
    cmds.append('w 1464a 4ef90007')     # jmp $71000.l over the 10 bytes (link a6,#-4 / move.l -78(a4),-4(a6)) ...
    cmds.append('w 1464e 10004e71')     # ... padded with two nops; the displaced pair is re-executed at the end of the scratch code
    cmds.append('w 14652 4e71296c')     # (keeps the following opcode word $296c)
    st = ram.g(-16)                                   # silence all three logical channels first (status word -1 = idle)
    cmds.append('w %x ffffffff' % st)
    cmds.append('w %x ffff%s' % (st + 4, bytes(ram.b[st + 6:st + 8]).hex()))
    cmds.append('w %x %08x' % (MB, trigger))
    cmds.append('w %x %04x%04x' % (MB + 4, arg, ticks - 1))
    cmds.append('watch %s' % watch)
    return cmds


def run(trigger, arg, ticks, watch, maxsteps):
    cmds = build_cmds(trigger, arg, ticks, watch) + ['s %d' % maxsteps, 'q']
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', sscfg.DLL, 'resume', sscfg.SNAP_RACE, 'repl', '--disk-a', sscfg.DISK],
                       input='\n'.join(cmds) + '\n', capture_output=True, text=True, cwd=sscfg.R, env=env)
    out = []
    for l in (p.stderr + p.stdout).split('\n'):
        m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) (\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
        if m: out.append((int(m.group(1)), int(m.group(2), 16), m.group(3), int(m.group(4), 16), int(m.group(5), 16)))
    return out


if __name__ == '__main__':
    trig = int(sys.argv[1], 16); arg = int(sys.argv[2]); ticks = int(sys.argv[3])
    steps = 6000 + ticks * 1200
    psg = run(trig, arg, ticks, 'ff8800 4', steps)
    marks = run(trig, arg, ticks, '%x 2' % (A4 - 12), steps)
    print('psg writes', len(psg), 'tick marks', len(marks))
    json.dump({'psg': psg, 'marks': marks}, open(sys.argv[4] if len(sys.argv) > 4 else os.path.join(OUT, 'psg_capture.json'), 'w'))
