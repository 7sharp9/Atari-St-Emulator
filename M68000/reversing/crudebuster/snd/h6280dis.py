#!/usr/bin/env python3
"""HuC6280 disassembler for the Crude Buster sound CPU, with recursive descent over the MPR-banked address space.

The opcode table is parsed out of MAME's own 6280dasm.cpp (scratchpad/crudebuster/src/), so the instruction lengths and
mnemonics are MAME's by construction; `check_mame.py` then compares against MAME's live debugger output.

usage:
  h6280dis.py linear <phys-hex> <n-bytes> [--mpr 00,01,...]   linear listing of physical ROM bytes (logical = phys & 0x1fff + 0xe000 style via --base)
  h6280dis.py rd [--out file]                                  recursive descent from the five vectors with MPR tracking

Address model: logical 16-bit, 8 banks of 8 KiB. MPR[i] selects physical bank (phys = mpr<<13 | addr&0x1fff).
Physical ROM is $0000-$ffff (banks 0-7, bank 5 is blank). At reset every MPR is 0 (MAME h6280_device::device_reset), so the
vectors at logical $fff6-$ffff read physical $1ff6-$1fff and the first code at $e000 is physical $0000.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CB = os.path.join(ROOT, 'scratchpad', 'crudebuster')
SRC = os.path.join(CB, 'src', '6280dasm.cpp')
ROMPATH = os.path.join(CB, 'rom', 'cbuster_huc.bin')

# ---------------------------------------------------------------- opcode table from MAME's source
_src = open(SRC).read()
_tok = re.search(r'token\[\]=\s*\{(.*?)\};', _src, re.S).group(1)
TOKENS = re.findall(r'"([a-z0-9]+)"', _tok)
ENUM = ("adc and asl bcc bcs beq bit bmi bne bpl brk bvc bvs clc cld cli clv cmp cpx cpy dec dex dey eor inc inx iny jmp jsr lda ldx ldy "
        "lsr nop ora pha php pla plp rol ror rti rts sbc sec sed sei sta stx sty tax tay tsx txa txs tya ill "
        "bra stz trb tsb dea ina sax bsr phx phy plx ply csh csl tam tma cla cly clx st0 st1 st2 tst set tdd tia tii tin tai say sxy "
        "sm0 sm1 sm2 sm3 sm4 sm5 sm6 sm7 rm0 rm1 rm2 rm3 rm4 rm5 rm6 rm7 bs0 bs1 bs2 bs3 bs4 bs5 bs6 bs7 br0 br1 br2 br3 br4 br5 br6 br7").split()
assert len(ENUM) == len(TOKENS), (len(ENUM), len(TOKENS))
NAME = dict(zip(ENUM, TOKENS))
_tab = re.search(r'op6280\[512\]=\s*\{(.*?)\};', _src, re.S).group(1)
PAIRS = re.findall(r'_(\w\w\w),_(\w\w\w)', _tab)
assert len(PAIRS) == 256, len(PAIRS)
OPS = [(NAME[a], m) for a, m in PAIRS]

LEN = {'non': 1, 'acc': 1, 'imp': 1, 'imm': 2, 'abs': 3, 'zpg': 2, 'zpx': 2, 'zpy': 2, 'zpi': 2, 'abx': 3, 'aby': 3, 'rel': 2,
       'idx': 2, 'idy': 2, 'ind': 3, 'iax': 3, 'blk': 7, 'zrl': 3, 'imz': 3, 'izx': 3, 'ima': 4, 'imx': 4}


def fmt(mn, mode, args, pc, op=0):
    """MAME-style text. args = operand bytes."""
    a = args
    w = lambda i: a[i] | (a[i + 1] << 8)
    nxt = pc + LEN[mode]
    if mode == 'acc': return '%-5sa' % mn
    if mode == 'non': return '%-5s$%02X' % (mn, op)
    if mode == 'imp': return mn
    if mode == 'rel': return '%-5s$%04X' % (mn, (pc + 2 + (a[0] - 256 if a[0] > 127 else a[0])) & 0xffff)
    if mode == 'imm': return '%-5s#$%02X' % (mn, a[0])
    if mode == 'zpg': return '%-5s$%02X' % (mn, a[0])
    if mode == 'zpx': return '%-5s$%02X,x' % (mn, a[0])
    if mode == 'zpy': return '%-5s$%02X,y' % (mn, a[0])
    if mode == 'idx': return '%-5s($%02X,x)' % (mn, a[0])
    if mode == 'idy': return '%-5s($%02X),y' % (mn, a[0])
    if mode == 'zpi': return '%-5s($%02X)' % (mn, a[0])
    if mode == 'abs': return '%-5s$%04X' % (mn, w(0))
    if mode == 'abx': return '%-5s$%04X,x' % (mn, w(0))
    if mode == 'aby': return '%-5s$%04X,y' % (mn, w(0))
    if mode == 'ind': return '%-5s($%04X)' % (mn, w(0))
    if mode == 'iax': return '%-5s($%04X),X' % (mn, w(0))
    if mode == 'blk': return '%-5s$%04X $%04X $%04X' % (mn, w(0), w(2), w(4))
    if mode == 'zrl': return '%-5s$%02X $%04X' % (mn, a[0], (pc + 3 + (a[1] - 256 if a[1] > 127 else a[1])) & 0xffff)
    if mode == 'imz': return '%-5s#$%02X $%02X' % (mn, a[0], a[1])
    if mode == 'izx': return '%-5s#$%02X $%02X,x' % (mn, a[0], a[1])
    if mode == 'ima': return '%-5s#$%02X $%04X' % (mn, a[0], w(1))
    if mode == 'imx': return '%-5s#$%02X $%04X,x' % (mn, a[0], w(1))
    raise ValueError(mode)


class Rom:
    def __init__(self, path=ROMPATH):
        self.d = open(path, 'rb').read()
        assert len(self.d) == 0x10000

    def phys(self, mpr, addr):
        return ((mpr[(addr >> 13) & 7] << 13) | (addr & 0x1fff))

    def rd(self, mpr, addr):
        p = self.phys(mpr, addr & 0xffff)
        return self.d[p] if p < len(self.d) else 0xff   # logical reads above ROM are chip/RAM: not static


def decode(rom, mpr, pc):
    op = rom.rd(mpr, pc)
    mn, mode = OPS[op]
    n = LEN[mode]
    args = [rom.rd(mpr, pc + 1 + i) for i in range(n - 1)]
    return op, mn, mode, n, args


# ---------------------------------------------------------------- recursive descent with MPR tracking
IDEPS = 'bcc bcs beq bmi bne bpl bvc bvs'.split()


class Walker:
    """State = (pc, mpr tuple, A) per path.  A is tracked only through lda #imm / cla / tax / tay / txa so that `lda #n / tam #m`
    sequences resolve; any other write to A makes it unknown (None) and a tam with unknown A leaves that MPR unknown (None).
    A None MPR is reported and the path continues treating it as the previously known value (flagged in `warn`)."""

    def __init__(self, rom):
        self.rom = rom
        self.insn = {}       # (phys) -> (logical, text, bytes, mpr snapshot)
        self.phys_seen = {}  # phys -> set of logical pcs
        self.xrefs = {}      # target logical -> set(from logical)
        self.warn = []
        self.seen = set()
        self.calls = {}
        self.mprs_at = {}    # phys -> set of mpr tuples (for each decoded instruction)

    def run(self, roots, mpr0):
        work = [(r, tuple(mpr0), None, None, None) for r in roots]
        while work:
            pc, mpr, a, x, y = work.pop()
            while True:
                key = (pc, mpr)
                if key in self.seen:
                    break
                self.seen.add(key)
                p = self.rom.phys(mpr, pc)
                if p >= 0x10000:
                    self.warn.append('pc %04x -> phys %06x outside ROM' % (pc, p))
                    break
                op, mn, mode, n, args = decode(self.rom, mpr, pc)
                txt = fmt(mn, mode, args, pc, op)
                self.insn.setdefault(p, (pc, txt, bytes([op] + args), mpr, n))
                self.mprs_at.setdefault(p, set()).add(mpr)
                nxt = (pc + n) & 0xffff
                # register tracking
                if mn == 'lda' and mode == 'imm': a = args[0]
                elif mn == 'lda' and mode == 'abs' and self.rom.phys(mpr, args[0] | args[1] << 8) < 0x10000 and \
                        (args[0] | args[1] << 8) >= 0x4000:
                    a = self.rom.rd(mpr, args[0] | args[1] << 8)   # constant read from a ROM-mapped page
                elif mn == 'cla': a = 0
                elif mn == 'ldx' and mode == 'imm': x = args[0]
                elif mn == 'clx': x = 0
                elif mn == 'ldy' and mode == 'imm': y = args[0]
                elif mn == 'cly': y = 0
                elif mn == 'txa': a = x
                elif mn == 'tya': a = y
                elif mn == 'tax': x = a
                elif mn == 'tay': y = a
                elif mn in ('lda', 'pla', 'adc', 'sbc', 'and', 'ora', 'eor', 'asl', 'lsr', 'rol', 'ror', 'dea', 'ina', 'tma', 'sax', 'say') and mode != 'imm' or \
                        (mn in ('adc', 'sbc', 'and', 'ora', 'eor') ):
                    a = None
                if mn in ('ldx', 'plx', 'inx', 'dex', 'tsx', 'sxy', 'sax') and not (mn == 'ldx' and mode == 'imm'): x = None
                if mn in ('ldy', 'ply', 'iny', 'dey', 'sxy', 'say') and not (mn == 'ldy' and mode == 'imm'): y = None
                if mn == 'tam':
                    m = list(mpr)
                    for i in range(8):
                        if args[0] & (1 << i):
                            if a is None:
                                self.warn.append('tam #$%02x at logical %04x phys %05x with unknown A' % (args[0], pc, p))
                            else:
                                m[i] = a
                    mpr = tuple(m)
                    nxt = pc + n
                # control flow
                if mn in ('bra',):
                    tgt = int(txt.split('$')[1], 16)
                    self.xrefs.setdefault(tgt, set()).add(pc)
                    pc = tgt
                    continue
                if mn in IDEPS or mn == 'bsr' or mode == 'zrl':
                    tgt = int(txt.split('$')[-1], 16)
                    self.xrefs.setdefault(tgt, set()).add(pc)
                    if mn == 'bsr':
                        self.calls.setdefault(tgt, set()).add(pc)
                        work.append((tgt, mpr, None, None, None))   # callee entry state: conservatively unknown regs, same MPRs
                    else:
                        work.append((tgt, mpr, a, x, y))
                    pc = nxt
                    continue
                if mn == 'jsr':
                    tgt = int(txt.split('$')[1], 16)
                    self.xrefs.setdefault(tgt, set()).add(pc)
                    self.calls.setdefault(tgt, set()).add(pc)
                    work.append((tgt, mpr, None, None, None))
                    pc = nxt
                    continue
                if mn == 'jmp':
                    if mode == 'abs':
                        tgt = int(txt.split('$')[1], 16)
                        self.xrefs.setdefault(tgt, set()).add(pc)
                        pc = tgt
                        continue
                    self.warn.append('indirect jmp at %04x phys %05x: %s' % (pc, p, txt))
                    break
                if mn in ('rts', 'rti', 'brk'):
                    break
                pc = nxt
                # after a register-clobbering call, tracking restarts (callee may change A,X,Y); MPR kept as in the caller
                if mn == 'jsr' or mn == 'bsr':
                    a = x = y = None


def full_walk(rom):
    """Recursive descent from reset, then (with the MPRs of the idle loop) IRQ2, IRQ1, timer and the 72 sequencer opcode handlers of the table at $E97A."""
    w = Walker(rom)
    mpr0 = (0,) * 8
    vec = lambda off: rom.d[0x1ff6 + off] | rom.d[0x1ff7 + off] << 8
    roots = {'reset': vec(8), 'irq2': vec(0), 'irq1': vec(2), 'timer': vec(4), 'nmi': vec(6)}
    w.run([roots['reset']], mpr0)
    extra = [rom.d[0x97a + 2 * i] | rom.d[0x97b + 2 * i] << 8 for i in range(72)]
    idle = None
    for p, (pc, txt, b, m, n) in sorted(w.insn.items()):
        if txt.startswith('bra') and txt.endswith('$%04X' % pc): idle = m
    for name in ('irq2', 'irq1', 'timer'):
        w.run([roots[name]], idle or mpr0)
    w.run(extra, idle or mpr0)
    return w, roots, idle

if __name__ == '__main__':
    argv = sys.argv[1:]
    rom = Rom()
    if argv and argv[0] == 'linear':
        base = 0xe000
        mpr = [0] * 8
        args = argv[1:]
        pa = int(args[0], 16); n = int(args[1], 16)
        i = 2
        while i < len(args):
            if args[i] == '--mpr': mpr = [int(v, 16) for v in args[i + 1].split(',')]; i += 2
            elif args[i] == '--base': base = int(args[i + 1], 16); i += 2
            else: i += 1
        # logical address from phys: base + (pa & 0x1fff) when bank maps there
        pc = base + (pa & 0x1fff)
        end = pc + n
        while pc < end:
            op, mn, mode, ln, a = decode(rom, mpr, pc)
            print('%04X: %-12s %s' % (pc, ' '.join('%02x' % b for b in [op] + a), fmt(mn, mode, a, pc, op)))
            pc += ln
    if argv and argv[0] == 'rd':
        outp = None
        if '--out' in argv: outp = argv[argv.index('--out') + 1]
        w, roots, idle = full_walk(rom)
        print('idle loop mpr=%s' % ','.join('%02x' % v for v in idle))
        print('vectors', {k: '%04x' % v for k, v in roots.items()})
        print('insns', len(w.insn), 'warnings', len(w.warn))
        for s_ in w.warn: print('WARN', s_)
        lines = []
        prev_end = None
        for p in sorted(w.insn):
            pc, txt, b, m, n = w.insn[p]
            if prev_end is not None and p != prev_end:
                lines.append('  ; ---- gap phys %05x..%05x (%d bytes) ----' % (prev_end, p, p - prev_end))
            lab = ''
            if pc in w.xrefs: lab = 'L%04x' % pc
            lines.append('%05x %04x: %-14s %-26s %s' % (p, pc, ' '.join('%02x' % v for v in b), txt, lab))
            prev_end = p + n
        if outp:
            open(outp, 'w').write('\n'.join(lines) + '\n')
        else:
            print('\n'.join(lines))
