"""Differential-test harness: poke state into a snapshot through the REPL, call a routine with `callcap`, return the changed
bytes; a shadow copy of RAM tracks the pokes so a Python reference can be run on the exact same input state."""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from repl import Repl


class CallDiff:
    def __init__(self, snap=None):
        self.snap = snap or sscfg.SNAP_RACE
        self.ram = bytearray(Ram(self.snap).b)          # shadow: snapshot + every poke
        self.r = Repl(self.snap)
        _, regs = self.r.cmd('m 0 4')                    # NOTE: Repl.cmd appends its own 'r'; never send a bare 'r'
        self.sp0 = regs['A7']
        self.tmp = os.path.join(OUT, 'callcap_tmp.json')

    def poke(self, addr, data):
        """write bytes at addr (any alignment/length) using longword `w` commands, read-modify-write on the shadow"""
        for i, b in enumerate(data):
            self.ram[addr + i] = b
        a0 = addr & ~3; a1 = (addr + len(data) + 3) & ~3
        for a in range(a0, a1, 4):
            self.r.cmd('w %x %s' % (a, self.ram[a:a + 4].hex()))

    def poke_word(self, addr, val):
        self.poke(addr, struct.pack('>H', val & 0xFFFF))

    def poke_long(self, addr, val):
        self.poke(addr, struct.pack('>I', val & 0xFFFFFFFF))

    def call(self, addr, args=b'', maxsteps=2000000, presets=''):
        """args = bytes at 8(A6) upward (i.e. at the entry SP). returns (outcome, {addr: newbyte})"""
        if args:
            a = args + b'\0' * ((-len(args)) % 4)
            self.poke(self.sp0, a)
        if os.path.exists(self.tmp): os.remove(self.tmp)
        self.r.cmd('callcap %x %d %s %s' % (addr, maxsteps, self.tmp, presets))
        d = json.load(open(self.tmp))
        return d['outcome'], {ad: x1 for ad, x0, x1 in d['mem']}, d

    def apply(self, base_bytes, base_addr, changes):
        out = bytearray(base_bytes)
        for ad, v in changes.items():
            if base_addr <= ad < base_addr + len(out):
                out[ad - base_addr] = v
        return out

    def close(self):
        self.r.close()
