"""Python client for `stserver` (DEVELOPING.md, "Memory hooks and the `stserver` process"): one emulator process
driven over newline-delimited JSON-RPC from a script, so a gate that runs a routine thousands of times prints only its
counts.

    import sys; sys.path.insert(0, '<root>/tools'); from stclient import StServer
    s = StServer(root)                       # root = the M68000 dir (holds server/bin/.../stserver.dll)
    s('load', snapshot=snap, disk=disk)      # any method from the DEVELOPING.md table, params as keywords
    s.read(addr, n) -> bytes; s.reg('a7') -> int
    s.call(entry, ret=0x800)                 # run one routine from a planted return address, interrupts masked
    s.call(entry, stops=[pc])                # ... or until it reaches pc (before an interrupt wait)
    s.close()

`call` pushes `ret` below the snapshot's stack (`sp` is fixed at the first call: SSP - 64), sets SR = $2700 and the
given registers, and runs until PC = `ret`; `ret` only needs to be an address the routine never reaches. Worked
example: reversing/midwinter/py/army/gate_army.py (1000 chained calls of `$c136` in about 5 s).
A REPL `mouse` click that registers may still not register through `stserver`'s `mouse` (Midwinter's handoff trap):
make the click in the REPL, snapshot, and load that here.
"""
import json
import os
import subprocess
import sys


class StServer:
    def __init__(self, root, dll=None):
        dll = dll or os.path.join(root, 'server', 'bin', 'Debug', 'net8.0', 'stserver.dll')
        self.p = subprocess.Popen(['dotnet', 'exec', dll], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, cwd=root)
        self.seq = 0
        self.sp = None

    def __call__(self, method, **params):
        self.seq += 1
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.seq, 'method': method, 'params': params}) + '\n')
        self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())
        if 'error' in r:
            sys.exit(f'stserver {method}: {r["error"]["message"]}')
        return r['result']

    def read(self, addr, n):
        return bytes.fromhex(self('read', addr=addr, len=n))

    def reg(self, name):
        return int(str(self('regs')[name.lower()]).lstrip('$'), 16)

    def call(self, entry, ret=0x800, max_steps=400000, stops=(), **regs):
        """`stops`: more PCs that end the call (for a routine that would go on to wait on an interrupt); the
        result's PC says which was reached."""
        if self.sp is None:
            self.sp = self.reg('a7') - 64
        self('poke', addr=self.sp, width=4, value=ret)
        self('set_reg', name='a7', value=self.sp)
        for name, value in regs.items():
            self('set_reg', name=name, value=value)
        self('set_reg', name='sr', value=0x2700)
        self('set_reg', name='pc', value=entry)
        r = self('run', max_steps=max_steps, until_pc=[ret, *stops] if stops else ret)
        if r['reason'] != 'until':
            sys.exit(f'${entry:x} did not return to ${ret:x} ({r})')
        return r

    def close(self):
        self.p.stdin.close()
        self.p.wait()
