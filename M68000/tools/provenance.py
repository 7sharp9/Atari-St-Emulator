"""Backward slice over an `stserver` recording: where the bytes at an address, or the bits of a register, came from.

    python3 tools/provenance.py <stserver.dll> <snap> <disk.st|-> <steps> <hexaddr>[:<len>] <step|end> [--every N]
                                [--depth D] [--nodes K] [--json out.json]
    python3 tools/provenance.py --recording <dir> <stserver.dll> <hexaddr>[:<len>] <step|end> [--depth D] ...

The CLI records `<steps>` steps from `<snap>` (a checkpoint every `--every`, default 500,000) and slices
`<len>` bytes (default 1) at `<hexaddr>` as they stood at `<step>` (an absolute step count, or `end`). With
`--recording`, it slices a recording already on disk (`record_start` with `dir`, or a `stdrive.Drive(record=...)`
segment), loaded with `record_load`; `end` is the recording's last step. As a library,
`Slicer(s).slice_mem(lo, hi, step)` / `.slice_reg(name, mask, step)` work on any stserver `s` (tools/stclient.py)
holding a stopped recording, and return the tree of links that `show` prints.

One move, repeated (tooling-ideas.md, idea 3; DEVELOPING.md "Record and replay"):

1. a memory location's value at step S: `last_writer lo hi S` gives the writing step W and PC; a register's bits at S:
   `last_reg_change reg S mask` gives the step W at which those bits last changed and the PC there;
2. the instruction at that PC is decoded with tools/disassemble.py's decoder (code bytes read at W-1);
3. `replay_to W-1` gives the registers the instruction ran with, from which every effective address is computed
   (with the instruction's own (An)+ / -(An) side effects in operand order);
4. the source of the tracked bytes is worked out: a memory source is sliced at W-1, a register source through
   `last_reg_change` at W-1, a value with two variable inputs (add d1,d0) branches into both. It stops at an
   immediate (or a value fixed by the code: clr, moveq, an absolute lea, a return address), at an input (DMA sector,
   journalled host write or set_reg), at an interrupt entry, at a hardware register or ROM read, and at the base of
   the recording.

Every link carries a consistency check: the value the decode says the instruction wrote (an immediate's bytes, a source
register's or source memory's bytes at W-1) is compared with the value last_writer / last_reg_change reports, and a
mismatch is printed and stops that branch. An opcode or addressing mode the slicer has no rule for, a flag input
(Scc, addx, move from SR), and a writer whose decoded destination does not cover the written bytes (an exception
frame) stop with the reason; nothing is guessed. Depth and the total number of links are bounded.

Limits: `last_reg_change` finds the last *change*, so an instruction that rewrites a register with the value it
already held is skipped and the earlier instruction that produced that value is reported. Bit dependencies through
arithmetic are conservative (add/sub/neg: the tracked bits and every lower bit of the operand; shifts and
multiplies: the whole operand).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disassemble import Disassembler, sext16  # noqa: E402

REGS = [f'd{i}' for i in range(8)] + [f'a{i}' for i in range(8)]
SZ = {'b': 1, 'w': 2, 'l': 4}
M32 = 0xffffffff


def size_mask(n):
    return (1 << (8 * n)) - 1


def low_fill(mask):
    """Bits at or below the highest bit of mask (an add's carry chain)."""
    return (1 << mask.bit_length()) - 1 if mask else 0


class Unsupported(Exception):
    pass


# ---- operand parsing over disassemble.py's text ----------------------------------------------------------------

def split_ops(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur:
        out.append(cur)
    return [o.strip() for o in out]


def num(t):
    t = t.strip()
    neg = t.startswith('-')
    t = t.lstrip('-')
    v = int(t[1:], 16) if t.startswith('$') else int(t)
    return -v if neg else v


def parse_op(t):
    t = t.split(' == ')[0].strip() if '(PC' not in t else t
    if re.fullmatch(r'D[0-7]', t):
        return ('reg', 'd' + t[1])
    if re.fullmatch(r'A[0-7]', t):
        return ('reg', 'a' + t[1])
    if t in ('USP', 'SR', 'CCR'):
        return ('special', t.lower())
    if t.startswith('#'):
        return ('imm', num(t[1:]))
    m = re.fullmatch(r'\(A([0-7])\)', t)
    if m:
        return ('ind', 'a' + m[1], 0)
    m = re.fullmatch(r'\(A([0-7])\)\+', t)
    if m:
        return ('postinc', 'a' + m[1])
    m = re.fullmatch(r'-\(A([0-7])\)', t)
    if m:
        return ('predec', 'a' + m[1])
    m = re.fullmatch(r'(-?\d+)\(A([0-7])\)', t)
    if m:
        return ('ind', 'a' + m[2], int(m[1]))
    m = re.fullmatch(r'(-?\d+)\(A([0-7]),([DA])([0-7])\.([wl])\)', t)
    if m:
        return ('index', 'a' + m[2], int(m[1]), m[3].lower() + m[4], m[5])
    m = re.fullmatch(r'\$([0-9a-f]+)\.w', t)
    if m:
        return ('abs', sext16(int(m[1], 16)) & M32)
    m = re.fullmatch(r'\$([0-9a-f]+)\.l', t)
    if m:
        return ('abs', int(m[1], 16))
    m = re.fullmatch(r'-?\d+\(PC\) == \$([0-9a-f]+)', t)
    if m:
        return ('pcrel', int(m[1], 16))
    m = re.fullmatch(r'-?\d+\(PC,([DA])([0-7])\.([wl])\) == \$([0-9a-f]+)\+[DA][0-7](\.[wl])?', t)
    if m:
        return ('pcindex', int(m[4], 16), m[1].lower() + m[2], m[3])
    raise Unsupported(f'operand {t!r}')


class Insn:
    """A decoded instruction: mnemonic, size in bytes (None if unsized), operand tuples."""

    def __init__(self, text):
        self.text = text
        mn, _, rest = text.partition(' ')
        self.base, _, sfx = mn.partition('.')
        self.size = SZ.get(sfx)
        self.raw = split_ops(rest) if rest else []
        self.ops = []
        if self.base.startswith('movem'):
            self.ops = [('mask', num(o[1:])) if o.startswith('#') else parse_op(o) for o in self.raw]
        elif self.base not in ('bra', 'bsr') and not re.fullmatch(r'b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)', self.base):
            self.ops = [parse_op(o) for o in self.raw] if not self.base.startswith('db') else [parse_op(self.raw[0])]


# ---- the slicer ------------------------------------------------------------------------------------------------

class Slicer:
    def __init__(self, s, depth=12, nodes=60):
        self.s, self.max_depth, self.max_nodes, self.count = s, depth, nodes, 0

    # machine access at a step
    def at(self, step):
        self.s('replay_to', step=step)
        r = self.s('regs')
        return {k: int(r[k].lstrip('$'), 16) for k in REGS + ['usp', 'ssp', 'pc', 'sr']}

    def mem(self, addr, n):
        return int(self.s('read', addr=addr & 0xffffff, len=n) or '0', 16)

    def decode(self, pc):
        code = bytes.fromhex(self.s('read', addr=pc & 0xffffff, len=12))
        d = Disassembler(code + bytes(4), rom_base=pc & 0xffffff)
        text, nxt = d.decode_one(pc & 0xffffff)
        return text

    @staticmethod
    def ea(op, size, regs):
        """Effective address of a memory operand, applying its own (An)+ / -(An) to regs."""
        k = op[0]
        if k == 'ind':
            return (regs[op[1]] + op[2]) & M32
        if k == 'postinc':
            a = regs[op[1]]
            regs[op[1]] = (a + (2 if op[1] == 'a7' and size == 1 else size)) & M32
            return a
        if k == 'predec':
            regs[op[1]] = (regs[op[1]] - (2 if op[1] == 'a7' and size == 1 else size)) & M32
            return regs[op[1]]
        if k == 'index':
            x = regs[op[3]]
            x = (sext16(x & 0xffff) & M32) if op[4] == 'w' else x
            return (regs[op[1]] + op[2] + x) & M32
        if k == 'abs':
            return op[1]
        if k == 'pcrel':
            return op[1]
        if k == 'pcindex':
            x = regs[op[2]]
            x = (sext16(x & 0xffff) & M32) if op[3] == 'w' else x
            return (op[1] + x) & M32
        raise Unsupported(f'not a memory operand: {op}')

    @staticmethod
    def is_mem(op):
        return op[0] in ('ind', 'postinc', 'predec', 'index', 'abs', 'pcrel', 'pcindex')

    # a source operand as a dependency: the bytes/bits of `op` (size n) that feed `bits` (a mask over the n-byte value)
    def operand_dep(self, op, n, bits, regs, why):
        if op[0] == 'imm':
            return {'kind': 'imm', 'value': op[1] & size_mask(n), 'why': why}
        if op[0] == 'reg':
            return {'kind': 'reg', 'reg': op[1], 'mask': bits & size_mask(n), 'why': why}
        if op[0] == 'special':
            if op[1] == 'usp':
                return {'kind': 'reg', 'reg': 'usp', 'mask': bits & M32, 'why': why}
            raise Unsupported(f'source {op[1].upper()} (flags)')
        a = self.ea(op, n, regs)
        idx = [i for i in range(n) if (bits >> (8 * (n - 1 - i))) & 0xff]
        if not idx:
            return None
        lo, hi = a + min(idx), a + max(idx)
        return {'kind': 'mem', 'lo': lo & 0xffffff, 'hi': hi & 0xffffff, 'why': why}

    def addr_dep(self, op, regs, why):
        """The registers an address computation (lea/pea) reads, or a constant."""
        k = op[0]
        if k in ('abs', 'pcrel'):
            return [{'kind': 'imm', 'value': op[1], 'why': why + ' (constant address)'}]
        if k == 'ind':
            return [{'kind': 'reg', 'reg': op[1], 'mask': M32, 'why': why + f' (base {op[1]} + {op[2]})'}]
        if k == 'index':
            return [{'kind': 'reg', 'reg': op[1], 'mask': M32, 'why': why + ' (base)'},
                    {'kind': 'reg', 'reg': op[3], 'mask': 0xffff if op[4] == 'w' else M32, 'why': why + ' (index)'}]
        if k == 'pcindex':
            return [{'kind': 'reg', 'reg': op[2], 'mask': 0xffff if op[3] == 'w' else M32, 'why': why + ' (index)'}]
        raise Unsupported(f'address of {op}')

    # ---- writers of memory -----------------------------------------------------------------------------------
    def mem_writer(self, ins, regs, ev_lo, ev_hi, lo, hi):
        """-> (dst_lo, dst_hi, deps, predicted value of [lo,hi] or None). deps: list of dependency dicts."""
        b, n, ops = ins.base, ins.size, ins.ops
        r = dict(regs)

        def bits_of(a0, size):
            """mask over the size-byte value at a0 that covers the tracked bytes [lo,hi]."""
            m = 0
            for i in range(size):
                if lo <= ((a0 + i) & 0xffffff) <= hi:
                    m |= 0xff << (8 * (size - 1 - i))
            return m

        def check_dst(a0, size):
            a0 &= 0xffffff
            if not (a0 <= ev_lo and ev_hi <= a0 + size - 1):
                raise Unsupported(f'decoded destination ${a0:x}..${a0 + size - 1:x} does not cover the write '
                                  f'${ev_lo:x}..${ev_hi:x} (exception frame or decode gap)')
            return a0

        if b == 'move' and len(ops) == 2 and self.is_mem(ops[1]):
            src, dst = ops
            sa = None
            if self.is_mem(src):
                sa = self.ea(src, n, r)
                dep_src = ('mem', sa)
            da = check_dst(self.ea(dst, n, r), n)
            m = bits_of(da, n)
            if sa is not None:
                idx = [i for i in range(n) if (m >> (8 * (n - 1 - i))) & 0xff]
                dep = {'kind': 'mem', 'lo': (sa + min(idx)) & 0xffffff, 'hi': (sa + max(idx)) & 0xffffff, 'why': 'move source'}
                pred = ('mem', (sa + min(idx)) & 0xffffff, len(idx))
            else:
                dep = self.operand_dep(src, n, m, r, 'move source')
                pred = ('val', (dep['value'] if dep['kind'] == 'imm' else regs[dep['reg']] if dep['kind'] == 'reg' else None), n, m)
            return da, da + n - 1, [dep], pred
        if b == 'clr' and self.is_mem(ops[0]):
            da = check_dst(self.ea(ops[0], n, r), n)
            return da, da + n - 1, [{'kind': 'imm', 'value': 0, 'why': 'clr'}], ('val', 0, n, bits_of(da, n))
        if b in ('addq', 'subq', 'addi', 'subi', 'andi', 'ori', 'eori', 'add', 'sub', 'and', 'or', 'eor',
                 'neg', 'not', 'bset', 'bclr', 'bchg', 'tas') and self.is_mem(ops[-1]):
            if b in ('bset', 'bclr', 'bchg', 'tas'):
                n = 1
            if b in ('addq', 'subq', 'addi', 'subi', 'andi', 'ori', 'eori', 'add', 'sub', 'and', 'or', 'eor'):
                src = ops[0]
                r2 = dict(r)
                sdep = None if src[0] == 'imm' else self.operand_dep(src, n, 0, r2, '')  # side effects of src first
                da = check_dst(self.ea(ops[1], n, r2), n)
            else:
                src = ops[0] if b in ('bset', 'bclr', 'bchg') else None
                da = check_dst(self.ea(ops[-1], n, r), n)
            m = bits_of(da, n)
            carry = b in ('addq', 'subq', 'addi', 'subi', 'add', 'sub', 'neg')
            dm = low_fill(m) if carry else m
            old = {'kind': 'mem', 'lo': da + min(i for i in range(n) if (dm >> (8 * (n - 1 - i))) & 0xff),
                   'hi': da + n - 1 if carry else da + max(i for i in range(n) if (dm >> (8 * (n - 1 - i))) & 0xff),
                   'why': f'{b}: old value'}
            deps = [old]
            if b in ('add', 'sub', 'and', 'or', 'eor') and src[0] != 'imm':
                deps.append(self.operand_dep(src, n, dm, dict(regs), f'{b}: other operand'))
            if b in ('bset', 'bclr', 'bchg') and src[0] == 'reg':
                deps.append({'kind': 'reg', 'reg': src[1], 'mask': 7, 'why': f'{b}: bit number'})
            return da, da + n - 1, deps, None
        if b == 'movem' and ops[0][0] == 'mask':
            mask, dst = ops[0][1], ops[1]
            if dst[0] == 'predec':
                order = [REGS[15 - i] for i in range(16) if mask >> i & 1][::-1]
                start = (r[dst[1]] - n * len(order)) & M32
            else:
                order = [REGS[i] for i in range(16) if mask >> i & 1]
                start = self.ea(dst, n, r)
            da = check_dst(start, n * len(order))
            deps, pred = [], None
            for j, reg in enumerate(order):
                m = bits_of(da + j * n, n)
                if m:
                    deps.append({'kind': 'reg', 'reg': reg, 'mask': m, 'why': f'movem slot {j}'})
                    pred = ('val', regs[reg], n, m, da + j * n) if len(deps) == 1 else None
            return da, da + n * len(order) - 1, deps, pred
        if b == 'pea':
            da = check_dst((r['a7'] - 4) & M32, 4)
            return da, da + 3, self.addr_dep(ops[0], r, 'pea'), None
        if b in ('jsr', 'bsr'):
            da = check_dst((r['a7'] - 4) & M32, 4)
            return da, da + 3, [{'kind': 'imm', 'value': None, 'why': f'{b} return address'}], None
        if b == 'link':
            da = check_dst((r['a7'] - 4) & M32, 4)
            return da, da + 3, [{'kind': 'reg', 'reg': ops[0][1], 'mask': bits_of(da, 4), 'why': 'link saves An'}], \
                ('val', regs[ops[0][1]], 4, bits_of(da, 4))
        if b in ('scc',) or re.fullmatch(r's(t|f|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)', b):
            raise Unsupported(f'{ins.text}: value from the condition codes')
        mem_dst = ins.ops and self.is_mem(ins.ops[-1])
        raise Unsupported(f'{ins.text}: no rule for this writer of memory' if mem_dst else
                          f'{ins.text} writes no memory: an interrupt stack frame pushed at this PC, or an opcode with no rule')

    # ---- writers of registers --------------------------------------------------------------------------------
    def reg_writer(self, ins, regs, R, M):
        """-> (written bits of R, deps, predicted new value or None)."""
        b, n, ops = ins.base, ins.size, ins.ops
        r = dict(regs)
        dst = ops[-1] if ops else None
        is_dst = dst is not None and dst[0] == 'reg' and dst[1] == R

        # An auto-modified by an operand of an instruction whose destination is something else
        autos = [o for o in ops if o[0] in ('postinc', 'predec') and o[1] == R]
        if autos and not is_dst and b != 'movem':
            return M32, [{'kind': 'reg', 'reg': R, 'mask': M32, 'why': f'{autos[0][0]} side effect'}], None
        if R == 'a7' and b in ('jsr', 'bsr', 'rts', 'pea', 'unlk', 'link', 'rtr'):
            if b == 'unlk' and ops[0][1] != 'a7':
                return M32, [{'kind': 'reg', 'reg': ops[0][1], 'mask': M32, 'why': 'unlk: a7 = An + 4'}], None
            return M32, [{'kind': 'reg', 'reg': 'a7', 'mask': M32, 'why': f'{b} adjusts a7'}], None
        if b in ('rte', 'trap', 'stop', 'reset'):
            raise Unsupported(f'{ins.text}: possible stack swap or exception')
        if b == 'moveq' and is_dst:
            return M32, [{'kind': 'imm', 'value': ops[0][1] & M32, 'why': 'moveq'}], ops[0][1] & M32
        if b in ('move', 'movea') and is_dst:
            src = ops[0]
            if b == 'movea' and n == 2:
                need = (M & 0xffff) | (0x8000 if M & 0xffff0000 else 0)
                written = M32
            else:
                need, written = M & size_mask(n), (M32 if b == 'movea' else size_mask(n))
            if src[0] == 'special' and src[1] == 'usp':
                return M32, [{'kind': 'reg', 'reg': 'usp', 'mask': M32, 'why': 'move USP'}], regs['usp']
            dep = self.operand_dep(src, n, need, r, f'{b} source')
            pred = None
            if dep and dep['kind'] == 'imm':
                v = dep['value']
                pred = (sext16(v) & M32) if b == 'movea' and n == 2 else v
            elif dep and dep['kind'] == 'reg':  # the register the walk follows, so the check covers the edge
                v = regs[dep['reg']] & size_mask(n)
                pred = ((sext16(v) & M32) if b == 'movea' and n == 2 else v if b == 'movea' else (regs[R] & ~size_mask(n) & M32) | v)
            elif self.is_mem(src):
                pred = ('mem', self.ea(src, n, dict(regs)), n, b == 'movea' and n == 2)
            return written, [dep] if dep else [], pred
        if b == 'move' and ins.raw and ins.raw[-1] == 'USP' and R == 'usp':
            return M32, [{'kind': 'reg', 'reg': ops[0][1], 'mask': M32, 'why': 'move An,USP'}], regs[ops[0][1]]
        if b == 'clr' and is_dst:
            return size_mask(n), [{'kind': 'imm', 'value': 0, 'why': 'clr'}], regs[R] & ~size_mask(n) & M32
        if b == 'lea' and is_dst:
            return M32, self.addr_dep(ops[0], r, 'lea'), (self.ea(ops[0], 4, dict(regs)) if ops[0][0] != 'postinc' else None)
        if b == 'exg':
            x, y = ops[0][1], ops[1][1]
            if R not in (x, y):
                raise Unsupported(f'{ins.text}: does not write {R}')
            other = y if R == x else x
            return M32, [{'kind': 'reg', 'reg': other, 'mask': M & M32, 'why': 'exg'}], regs[other]
        if b == 'swap' and is_dst:
            rot = ((M >> 16) | (M << 16)) & M32
            return M32, [{'kind': 'reg', 'reg': R, 'mask': rot, 'why': 'swap'}], ((regs[R] >> 16) | (regs[R] << 16)) & M32
        if b == 'ext' and is_dst:
            if n == 2:
                need = (M & 0xff) | (0x80 if M & 0xff00 else 0)
                return 0xffff, [{'kind': 'reg', 'reg': R, 'mask': need, 'why': 'ext.w'}], None
            need = (M & 0xffff) | (0x8000 if M & 0xffff0000 else 0)
            return M32, [{'kind': 'reg', 'reg': R, 'mask': need, 'why': 'ext.l'}], None
        if b in ('addq', 'subq', 'addi', 'subi', 'neg', 'not', 'andi', 'ori', 'eori', 'add', 'sub', 'and', 'or', 'eor',
                 'adda', 'suba', 'mulu', 'muls', 'divu', 'divs', 'asl', 'asr', 'lsl', 'lsr', 'rol', 'ror',
                 'bset', 'bclr', 'bchg') and is_dst:
            an = R.startswith('a')
            if b in ('adda', 'suba') or (an and b in ('addq', 'subq')):
                size, written = 4, M32
            elif b in ('mulu', 'muls', 'divu', 'divs'):
                size, written = 4, M32
            elif b in ('bset', 'bclr', 'bchg'):
                size, written = 4, M32
            else:
                size = n
                written = size_mask(n)
            mm = M & written
            if b in ('addq', 'subq', 'addi', 'subi', 'neg', 'add', 'sub', 'adda', 'suba'):
                need = low_fill(mm) & size_mask(size)
            elif b in ('not', 'andi', 'ori', 'eori', 'and', 'or', 'eor', 'bset', 'bclr', 'bchg'):
                need = mm
            else:
                need = size_mask(size)
            deps = [{'kind': 'reg', 'reg': R, 'mask': need, 'why': f'{b}: old value'}]
            src = ops[0] if len(ops) == 2 else None
            if src is not None and src[0] != 'imm':
                if b in ('mulu', 'muls', 'divu', 'divs'):
                    deps.append(self.operand_dep(src, 2, 0xffff, r, f'{b}: other operand'))
                elif b in ('asl', 'asr', 'lsl', 'lsr', 'rol', 'ror'):
                    deps.append({'kind': 'reg', 'reg': src[1], 'mask': 0x3f, 'why': f'{b}: shift count'})
                elif b in ('bset', 'bclr', 'bchg'):
                    deps.append({'kind': 'reg', 'reg': src[1], 'mask': 0x1f, 'why': f'{b}: bit number'})
                else:
                    sz = 2 if b in ('adda', 'suba') and n == 2 else size
                    dep = self.operand_dep(src, sz, need & size_mask(sz), r, f'{b}: other operand')
                    if dep:
                        deps.append(dep)
            return written, deps, None
        if b.startswith('db') and is_dst:
            return 0xffff, [{'kind': 'reg', 'reg': R, 'mask': low_fill(M & 0xffff), 'why': f'{b} decrement'}], None
        if b == 'movem' and ops[1][0] == 'mask':
            src, mask = ops[0], ops[1][1]
            order = [REGS[i] for i in range(16) if mask >> i & 1]
            if R not in order:
                if src[0] == 'postinc' and src[1] == R:
                    return M32, [{'kind': 'reg', 'reg': R, 'mask': M32, 'why': 'movem (An)+ side effect'}], None
                raise Unsupported(f'{ins.text}: {R} is not in the register list')
            a = self.ea(src, n, dict(r)) if src[0] != 'postinc' else r[src[1]]
            j = order.index(R)
            slot = a + j * n
            if n == 2:  # bits 0-7 from the slot's second byte, 8-15 from its first, 16-31 the sign of the first
                lo_b = slot if M & 0xffffff00 else slot + 1
                hi_b = slot + 1 if M & 0xff else slot
                return M32, [{'kind': 'mem', 'lo': lo_b & 0xffffff, 'hi': hi_b & 0xffffff,
                              'why': f'movem.w slot {j} (sign-extended)'}], ('mem', slot & 0xffffff, 2, True)
            idx = [i for i in range(4) if (M >> (8 * (3 - i))) & 0xff]
            return M32, [{'kind': 'mem', 'lo': (slot + min(idx)) & 0xffffff, 'hi': (slot + max(idx)) & 0xffffff,
                          'why': f'movem.l slot {j}'}], ('mem', slot & 0xffffff, 4, False)
        if b == 'link' and ops[0][1] == R:
            return M32, [{'kind': 'reg', 'reg': 'a7', 'mask': M32, 'why': 'link: An = a7 - 4'}], (regs['a7'] - 4) & M32
        if b == 'unlk' and ops[0][1] == R:
            return M32, [{'kind': 'mem', 'lo': regs[R] & 0xffffff, 'hi': (regs[R] + 3) & 0xffffff, 'why': 'unlk pops An'}], None
        if re.fullmatch(r's(t|f|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)', b) or ins.raw[:1] == ['SR']:
            raise Unsupported(f'{ins.text}: value from the condition codes')
        if b in ('addx', 'subx', 'negx', 'abcd', 'sbcd'):
            raise Unsupported(f'{ins.text}: X flag input')
        raise Unsupported(f'{ins.text}: no rule for this writer of {R}')

    # ---- the walk --------------------------------------------------------------------------------------------
    def slice_mem(self, lo, hi, step, depth=0, why='target'):
        node = {'kind': 'mem', 'lo': lo, 'hi': hi, 'at': step, 'why': why, 'children': []}
        if lo >= 0xff8000:
            node['stop'] = 'hardware register read (input)'
            return node
        if 0xfc0000 <= lo <= 0xfeffff or hi < 8:
            node['stop'] = 'ROM constant'
            return node
        if depth >= self.max_depth or self.count >= self.max_nodes:
            node['stop'] = 'depth/node bound'
            return node
        self.count += 1
        g = self.s('last_writer', lo=lo, hi=hi, step=step)
        e = g['event']
        if e is None:
            node['stop'] = 'unchanged since the base of the recording'
            node['value'] = self.mem(lo, hi - lo + 1) if self.at(step) else None
            return node
        W, pc = e['step'], int(e['pc'][1:], 16)
        ev_lo = int(e['addr'][1:], 16)
        ev_hi = ev_lo + e['width'] - 1
        node.update(step=W, pc=pc, write=(ev_lo, e['width'], int(e['value'][1:], 16)), source=e['source'],
                    value=int(e['value'][1:], 16))
        if e['source'] == 'dma':
            node['stop'] = 'DMA (disk sector)'
            return node
        if e['source'] == 'host':
            node['stop'] = 'input (journalled host write)'
            return node
        regs = self.at(W - 1)
        try:
            text = self.decode(pc)
        except Exception as x:  # noqa: BLE001 - a decode failure is reported, not hidden
            node['stop'] = f'decode failed at ${pc:x}: {x}'
            return node
        node['insn'] = text
        try:
            ins = Insn(text)
            dlo, dhi, deps, pred = self.mem_writer(ins, regs, ev_lo, ev_hi, lo, hi)
        except Unsupported as x:
            node['stop'] = f'unsupported: {x}'
            return node
        # the value now (at W): the tracked bytes the instruction wrote
        wlo, whi = max(lo, dlo), min(hi, dhi)
        self.s('replay_to', step=W)
        node['value'] = self.mem(wlo, whi - wlo + 1)
        node['bytes'] = (wlo, whi)
        node['check'] = self.check_mem(pred, dlo, dhi, wlo, whi, node['value'], W)
        if node['check'] == 'MISMATCH':
            node['stop'] = 'value check failed: decode or rule is wrong'
            return node
        for d in deps:
            node['children'].append(self.follow(d, W - 1, depth + 1))
        for (a, z) in ((lo, min(hi, dlo - 1)), (max(lo, dhi + 1), hi)):
            if a <= z:
                node['children'].append(self.slice_mem(a, z, W - 1, depth + 1, 'bytes not written by this instruction'))
        return node

    def check_mem(self, pred, dlo, dhi, wlo, whi, got, W):
        if pred is None:
            return 'n/a'
        if pred[0] == 'mem':
            v = self.mem_at(pred[1], pred[2], W - 1)
            return 'ok' if v == got else 'MISMATCH'
        v, n, at = pred[1], pred[2], (pred[4] if len(pred) > 4 else dlo)
        if v is None:
            return 'n/a'
        # bytes [wlo,whi] of an n-byte value v stored at `at` (dlo, or a movem slot)
        if not (at <= wlo and whi <= at + n - 1):
            return 'n/a'
        b = (v & size_mask(n)).to_bytes(n, 'big')
        want = int.from_bytes(b[wlo - at:whi - at + 1], 'big')
        return 'ok' if want == got else 'MISMATCH'

    def mem_at(self, a, n, step):
        self.s('replay_to', step=step)
        return self.mem(a, n)

    def slice_reg(self, R, M, step, depth=0, why='target'):
        node = {'kind': 'reg', 'reg': R, 'mask': M, 'at': step, 'why': why, 'children': []}
        if depth >= self.max_depth or self.count >= self.max_nodes:
            node['stop'] = 'depth/node bound'
            return node
        self.count += 1
        g = self.s('last_reg_change', reg=R, step=step, mask=M)
        e = g['event']
        if e is None:
            node['stop'] = 'unchanged since the base of the recording'
            return node
        W, pc = e['step'], int(e['pc'][1:], 16)
        node.update(step=W, pc=pc, value=int(e['value'][1:], 16), previous=int(e['previous'][1:], 16), source=e['source'])
        if e['source'] == 'host':
            node['stop'] = 'input (journalled set_reg)'
            return node
        if e['source'] == 'exception':
            node['stop'] = 'interrupt/exception entry'
            return node
        regs = self.at(W - 1)
        try:
            text = self.decode(pc)
        except Exception as x:  # noqa: BLE001
            node['stop'] = f'decode failed at ${pc:x}: {x}'
            return node
        node['insn'] = text
        try:
            written, deps, pred = self.reg_writer(Insn(text), regs, R, M)
        except Unsupported as x:
            node['stop'] = f'unsupported: {x}'
            return node
        if isinstance(pred, tuple):  # a register loaded from memory: the source bytes as they stood at W-1
            _, a, n, sx = pred
            pred = self.mem_at(a, n, W - 1)
            pred = (sext16(pred) & M32) if sx else pred
        if pred is not None:
            node['check'] = 'ok' if (pred ^ node['value']) & M & written == 0 else 'MISMATCH'
            if node['check'] == 'MISMATCH':
                node['stop'] = 'value check failed: decode or rule is wrong'
                return node
        else:
            node['check'] = 'n/a'
        for d in deps:
            node['children'].append(self.follow(d, W - 1, depth + 1))
        if M & ~written & M32:
            node['children'].append(self.slice_reg(R, M & ~written & M32, W - 1, depth + 1, 'bits not written by this instruction'))
        return node

    def follow(self, d, step, depth):
        if d is None:
            return {'kind': 'none', 'stop': 'no bits needed', 'children': []}
        if d['kind'] == 'imm':
            v = d['value']
            return {'kind': 'imm', 'value': v, 'why': d['why'], 'stop': 'immediate / fixed by the code', 'children': []}
        if d['kind'] == 'mem':
            return self.slice_mem(d['lo'], d['hi'], step, depth, d['why'])
        if d['mask'] == 0:
            return {'kind': 'none', 'stop': 'no bits needed', 'why': d['why'], 'children': []}
        return self.slice_reg(d['reg'], d['mask'], step, depth, d['why'])


def links(node):
    """Every node that names a step (a found writer), depth first."""
    out = [node] if 'step' in node else []
    for c in node['children']:
        out += links(c)
    return out


def show(node, ind=0, f=sys.stdout):
    pad = '  ' * ind
    if node['kind'] == 'mem':
        loc = f"${node['lo']:06x}" + (f"..${node['hi']:06x}" if node['hi'] != node['lo'] else '')
    elif node['kind'] == 'reg':
        loc = node['reg'] + ('' if node['mask'] == M32 else f"&${node['mask']:x}")
    elif node['kind'] == 'imm':
        v = node['value']
        f.write(f"{pad}<- immediate {'$%x' % v if v is not None else '(code address)'} [{node['why']}]\n")
        return
    else:
        f.write(f"{pad}<- {node.get('stop')}\n")
        return
    head = f"{pad}{'<- ' if ind else ''}{loc} @{node['at']} [{node['why']}]"
    if 'step' in node:
        v = node.get('value')
        vs = f'${v:x}' if isinstance(v, int) else '?'
        f.write(f"{head}: step {node['step']} pc ${node['pc']:06x} {node.get('insn', '')!s:30} value {vs}"
                f"{' check ' + node['check'] if 'check' in node else ''}\n")
    else:
        f.write(f'{head}\n')
    if 'stop' in node:
        f.write(f"{pad}   stop: {node['stop']}\n")
    kids = node['children']
    # a run of links through the same instruction (a pointer stepped through an array) prints once
    run = []
    while 'pc' in node and len(kids) == 1 and kids[0].get('pc') == node['pc'] and kids[0].get('why') == node.get('why'):
        run.append(kids[0])
        node, kids = kids[0], kids[0]['children']
    if run:
        f.write(f"{pad}   ... {len(run)} more link(s) through the same instruction, steps {run[-1]['step']}..{run[0]['step']}, "
                f"oldest value ${run[-1]['value']:x}\n")
        if 'stop' in node:
            f.write(f"{pad}   stop: {node['stop']}\n")
    for c in kids:
        show(c, ind + 1, f)


def main():
    import argparse
    from stclient import StServer
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    rec = '--recording' in sys.argv
    if rec:
        ap.add_argument('--recording', required=True)
        ap.add_argument('dll')
    else:
        ap.add_argument('dll'); ap.add_argument('snap'); ap.add_argument('disk'); ap.add_argument('steps', type=int)
    ap.add_argument('target'); ap.add_argument('at')
    ap.add_argument('--every', type=int, default=500_000); ap.add_argument('--depth', type=int, default=12)
    ap.add_argument('--nodes', type=int, default=60); ap.add_argument('--json')
    a = ap.parse_args()
    s = StServer(os.getcwd(), dll=a.dll)
    if rec:
        end = s('record_load', dir=os.path.abspath(a.recording))['end']
    else:
        B = s('load', snapshot=a.snap, disk=None if a.disk == '-' else a.disk)['step']
        s('record_start', every=a.every)
        s('step', n=a.steps)
        end = s('record_stop')['end']
    addr, _, ln = a.target.partition(':')
    lo = int(addr, 16)
    at = int(end) if a.at == 'end' else int(a.at)
    tree = Slicer(s, a.depth, a.nodes).slice_mem(lo, lo + (int(ln) if ln else 1) - 1, at)
    show(tree)
    if a.json:
        json.dump(tree, open(a.json, 'w'), indent=1)
    s.close()


if __name__ == '__main__':
    main()
