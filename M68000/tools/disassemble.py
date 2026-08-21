"""Standalone 68000 disassembler for TOS100UK.IMG, used to hand-verify what the real ROM says at
a given address before implementing/debugging an opcode - see the atari-st-emulator-next-instructions
memory entry's "decode from code, not memory" discipline: bitfield layouts here are cross-checked
against the actual active patterns in ../Instructions.fs (not recalled from the 68000 ISA manual),
so this tool's decode and the emulator's decode can't silently drift apart.

This is a debugging aid, not part of the emulator - it never runs any code, only reads ROM bytes.

Usage:
    python disassemble.py fc159e fc1a34          # disassemble from each address, stop at
                                                  # rts/rte/jmp/bra/illegal/trap/unknown, ~40 instrs max
    python disassemble.py --linear fc0000 40     # walk `count` instructions straight through,
                                                  # ignoring branches (for tracing a fixed byte range,
                                                  # e.g. the low-memory ROM mirror/reset trampoline)
    python disassemble.py --rom path\to\rom.img fc159e   # override the ROM path

Known gaps (extend as needed, following the same "verify against Instructions.fs first" discipline):
TAS's ea-operand form, line-A/line-F opcodes, ABCD/SBCD/NBCD, CHK, TRAPV, RESET's operands (none),
and any instruction family the real emulator hasn't hit yet either.
"""
import sys
import os

DEFAULT_ROM_PATH = os.path.join(os.path.dirname(__file__), "..", "TOS100UK.IMG")
ROM_BASE = 0xfc0000


def load_rom(path):
    with open(path, 'rb') as f:
        return f.read()


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


def sext8(v):
    return v - 0x100 if v & 0x80 else v


SIZES = {0: '.b', 1: '.w', 2: '.l'}
SIZES_MOVE = {1: '.b', 3: '.w', 2: '.l'}  # MOVE's size field: 01=b, 11=w, 10=l - see Instructions.fs (|Move|_|)

CONDITION_NAMES = {0: 't', 1: 'f', 2: 'hi', 3: 'ls', 4: 'cc', 5: 'cs', 6: 'ne', 7: 'eq',
                   8: 'vc', 9: 'vs', 10: 'pl', 11: 'mi', 12: 'ge', 13: 'lt', 14: 'gt', 15: 'le'}


class Disassembler:
    def __init__(self, rom, rom_base=ROM_BASE):
        self.rom = rom
        self.rom_base = rom_base

    def rw(self, addr):
        off = addr - self.rom_base
        return (self.rom[off] << 8) | self.rom[off + 1]

    def rl(self, addr):
        return (self.rw(addr) << 16) | self.rw(addr + 2)

    def ea_str(self, mode, reg, addr, size):
        """Returns (text, next_addr) for an effective address, consuming extension words from addr."""
        rw, rl = self.rw, self.rl
        if mode == 0:
            return f"D{reg}", addr
        if mode == 1:
            return f"A{reg}", addr
        if mode == 2:
            return f"(A{reg})", addr
        if mode == 3:
            return f"(A{reg})+", addr
        if mode == 4:
            return f"-(A{reg})", addr
        if mode == 5:
            disp = sext16(rw(addr))
            return f"{disp}(A{reg})", addr + 2
        if mode == 6:
            ext = rw(addr)
            idxreg, idxa, wl = (ext >> 12) & 7, (ext >> 15) & 1, (ext >> 11) & 1
            disp8 = sext8(ext & 0xff)
            idxname = ('A' if idxa else 'D') + str(idxreg)
            return f"{disp8}(A{reg},{idxname}{'.l' if wl else '.w'})", addr + 2
        if mode == 7:
            if reg == 0:
                return f"${rw(addr):x}.w", addr + 2
            if reg == 1:
                return f"${rl(addr):x}.l", addr + 4
            if reg == 2:
                disp = sext16(rw(addr))
                return f"{disp}(PC) == ${addr + disp:x}", addr + 2
            if reg == 3:
                ext = rw(addr)
                idxreg, idxa, wl = (ext >> 12) & 7, (ext >> 15) & 1, (ext >> 11) & 1
                disp8 = sext8(ext & 0xff)
                idxname = ('A' if idxa else 'D') + str(idxreg)
                return f"{disp8}(PC,{idxname}{'.l' if wl else '.w'})", addr + 2
            if reg == 4:
                if size == 0:
                    return f"#${rw(addr) & 0xff:x}", addr + 2
                if size == 1:
                    return f"#${rw(addr):x}", addr + 2
                if size == 2:
                    return f"#${rl(addr):x}", addr + 4
        return f"???mode{mode}reg{reg}", addr

    def decode_one(self, addr):
        """Returns (disassembly_text, next_instruction_addr)."""
        rw, rl, ea_str = self.rw, self.rl, self.ea_str
        op = rw(addr)
        nxt = addr + 2
        top = (op >> 12) & 0xf

        if top in (1, 2, 3):  # MOVE/MOVEA - Instructions.fs (|Move|_|)
            sizec = SIZES_MOVE[top]
            sizearg = {1: 0, 3: 1, 2: 2}[top]
            destreg, destmode = (op >> 9) & 7, (op >> 6) & 7
            srcmode, srcreg = (op >> 3) & 7, op & 7
            src, nxt = ea_str(srcmode, srcreg, nxt, sizearg)
            dst, nxt = ea_str(destmode, destreg, nxt, sizearg)
            if destmode == 1:
                return f"movea{sizec} {src},A{destreg}", nxt
            return f"move{sizec} {src},{dst}", nxt

        if top == 4:  # misc - Instructions.fs's various 0100-family patterns
            if op == 0x4e75:
                return "rts", nxt
            if op == 0x4e73:
                return "rte", nxt
            if op == 0x4e77:
                return "rtr", nxt
            if op == 0x4e70:
                return "reset", nxt
            if op == 0x4e71:
                return "nop", nxt
            if op == 0x4afc:
                return "illegal", nxt
            if op == 0x4e72:
                return f"stop #${rw(nxt):x}", nxt + 2
            if (op & 0xfff0) == 0x4e40:
                return f"trap #{op & 0xf}", nxt
            if (op & 0xff00) == 0x4a00 and (op & 0xc0) != 0xc0:
                size = (op >> 6) & 3
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"tst{SIZES.get(size, '?')} {ea}", nxt
            if (op & 0xffc0) == 0x4ac0:
                return (f"tas D{op & 7}" if ((op >> 3) & 7) == 0 else "tas ea?"), nxt
            if (op & 0xf1c0) == 0x41c0:  # LEA
                reg = (op >> 9) & 7
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 2)
                return f"lea {ea},A{reg}", nxt
            if (op & 0xfb80) == 0x4880 and ((op >> 3) & 7) != 0:
                # MOVEM - mask/required per Instructions.fs (|MOVEM|_|): 0xfb80/0x4880;
                # eamode 000 excluded there (reserved for EXT, an opcode-space alias)
                size = 2 if (op & 0x40) else 1
                direction = (op >> 10) & 1  # 0=reg->mem, 1=mem->reg
                mask = rw(nxt)
                ea, nxt2 = ea_str((op >> 3) & 7, op & 7, nxt + 2, size)
                szc = '.l' if size == 2 else '.w'
                return (f"movem{szc} {ea},#${mask:04x}" if direction
                        else f"movem{szc} #${mask:04x},{ea}"), nxt2
            if (op & 0xffc0) == 0x4840:
                return f"swap D{op & 7}", nxt
            if (op & 0xfff8) == 0x4e58:
                return f"unlk A{op & 7}", nxt
            if (op & 0xfff8) == 0x4e50:
                disp = sext16(rw(nxt))
                return f"link A{op & 7},#{disp}", nxt + 2
            if (op & 0xff00) == 0x4200 and ((op >> 6) & 3) != 3:  # CLR (size=11 -> below, unused slot)
                size = (op >> 6) & 3
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"clr{SIZES.get(size, '?')} {ea}", nxt
            if (op & 0xff00) == 0x4400 and ((op >> 6) & 3) != 3:  # NEG
                size = (op >> 6) & 3
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"neg{SIZES.get(size, '?')} {ea}", nxt
            if (op & 0xff00) == 0x4600 and ((op >> 6) & 3) != 3:  # NOT (size=11 slot -> MOVE ea,SR below)
                size = (op >> 6) & 3
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"not{SIZES.get(size, '?')} {ea}", nxt
            if (op & 0xff00) == 0x4000 and ((op >> 6) & 3) != 3:  # NEGX (size=11 slot -> MOVE SR,ea below)
                size = (op >> 6) & 3
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"negx{SIZES.get(size, '?')} {ea}", nxt
            if (op & 0xffc0) == 0x4ec0:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 2)
                return f"jmp {ea}", nxt
            if (op & 0xffc0) == 0x4e80:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 2)
                return f"jsr {ea}", nxt
            if (op & 0xfff8) == 0x4880:
                return f"ext.w D{op & 7}", nxt
            if (op & 0xfff8) == 0x48c0:
                return f"ext.l D{op & 7}", nxt
            # Opcode-space aliases living in the size=11 slot of NEGX/NOT's families - see
            # 68k-opcode-space-aliasing memory. Must be checked (as done above) alongside their
            # host family since they share the same top-byte mask.
            if (op & 0xffc0) == 0x40c0:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"move SR,{ea}", nxt
            if (op & 0xffc0) == 0x46c0:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"move {ea},SR", nxt
            if (op & 0xffc0) == 0x44c0:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"move {ea},CCR", nxt
            return f"???(0x{op:04x} misc)", nxt

        if top == 5:  # ADDQ/SUBQ/Scc/DBcc - Instructions.fs (|ADDQ|_|)/(|SUBQ|_|)/(|Scc|_|)/(|DBcc|_|)
            if (op & 0xf0c0) == 0x50c0 and (op & 0x38) == 0x08:  # DBcc (eamode=001 exact match)
                reg, cond = op & 7, (op >> 8) & 0xf
                disp = sext16(rw(nxt))
                return f"db{CONDITION_NAMES[cond]} D{reg},#{disp} == ${addr + 2 + disp:x}", nxt + 2
            if (op & 0xf0c0) == 0x50c0:  # Scc (any other eamode)
                cond = (op >> 8) & 0xf
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 0)
                return f"s{CONDITION_NAMES[cond]} {ea}", nxt
            data = (op >> 9) & 7
            data = 8 if data == 0 else data
            size = (op >> 6) & 3
            ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
            mn = "addq" if ((op >> 8) & 1) == 0 else "subq"
            return f"{mn}{SIZES.get(size, '?')} #{data},{ea}", nxt

        if top == 6:  # Bcc/BSR/BRA - Instructions.fs (|BCC|_|); cond=0001 is BSR, not "never branch"
            cond = (op >> 8) & 0xf
            disp8 = op & 0xff
            if disp8 == 0:
                disp = sext16(rw(nxt))
                target, nxt = addr + 2 + disp, nxt + 2
            else:
                target = addr + 2 + sext8(disp8)
            bcc_name = 'ra' if cond == 0 else 'sr' if cond == 1 else CONDITION_NAMES[cond]
            return f"b{bcc_name} ${target:x}", nxt

        if top == 7:  # MOVEQ - Instructions.fs (|MOVEQ|_|)
            reg = (op >> 9) & 7
            return f"moveq #{sext8(op & 0xff)},D{reg}", nxt

        if top == 8:  # OR/DIVU/DIVS - Instructions.fs (|OR|_|)/(|DIVU|_|)
            reg, opmode = (op >> 9) & 7, (op >> 6) & 7
            if opmode == 3:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"divu {ea},D{reg}", nxt
            if opmode == 7:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"divs {ea},D{reg}", nxt
            size, dir_ = opmode & 3, (opmode >> 2) & 1
            ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
            return (f"or{SIZES.get(size, '?')} D{reg},{ea}" if dir_
                    else f"or{SIZES.get(size, '?')} {ea},D{reg}"), nxt

        if top == 9:  # SUB/SUBA - Instructions.fs (|SUB|_|)
            reg, opmode = (op >> 9) & 7, (op >> 6) & 7
            if opmode in (3, 7):
                size = 1 if opmode == 3 else 2
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"suba{SIZES.get(size, '?')} {ea},A{reg}", nxt
            size, dir_ = opmode & 3, (opmode >> 2) & 1
            ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
            return (f"sub{SIZES.get(size, '?')} D{reg},{ea}" if dir_
                    else f"sub{SIZES.get(size, '?')} {ea},D{reg}"), nxt

        if top in (0xa, 0xf):  # line-A/line-F - not decoded, ROM hasn't needed these yet
            return f"(line-{'A' if top == 0xa else 'F'} 0x{op:04x})", nxt

        if top == 0xb:  # CMP/CMPA/EOR - Instructions.fs (|CMP|_|)
            reg, opmode = (op >> 9) & 7, (op >> 6) & 7
            if opmode in (3, 7):
                size = 1 if opmode == 3 else 2
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"cmpa{SIZES.get(size, '?')} {ea},A{reg}", nxt
            size, is_eor = opmode & 3, (opmode >> 2) & 1
            ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
            return (f"eor{SIZES.get(size, '?')} D{reg},{ea}" if is_eor
                    else f"cmp{SIZES.get(size, '?')} {ea},D{reg}"), nxt

        if top == 0xc:  # AND/MULU/MULS/EXG - Instructions.fs (|AND|_|)/(|MULU|_|)/(|EXG|_|)
            reg, opmode = (op >> 9) & 7, (op >> 6) & 7
            if opmode == 3:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"mulu {ea},D{reg}", nxt
            if opmode == 7:
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                return f"muls {ea},D{reg}", nxt
            if (op & 0xf130) == 0xc100:  # EXG - opcode-space alias, see 68k-opcode-space-aliasing memory
                exgmode, r2 = (op >> 3) & 0x1f, op & 7
                if exgmode == 0b01000:
                    return f"exg D{reg},D{r2}", nxt
                if exgmode == 0b01001:
                    return f"exg A{reg},A{r2}", nxt
                if exgmode == 0b10001:
                    return f"exg D{reg},A{r2}", nxt
            size, dir_ = opmode & 3, (opmode >> 2) & 1
            ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
            return (f"and{SIZES.get(size, '?')} D{reg},{ea}" if dir_
                    else f"and{SIZES.get(size, '?')} {ea},D{reg}"), nxt

        if top == 0xd:  # ADD/ADDA - Instructions.fs (|ADD|_|)
            reg, opmode = (op >> 9) & 7, (op >> 6) & 7
            if opmode in (3, 7):
                size = 1 if opmode == 3 else 2
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
                return f"adda{SIZES.get(size, '?')} {ea},A{reg}", nxt
            size, dir_ = opmode & 3, (opmode >> 2) & 1
            ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, size)
            return (f"add{SIZES.get(size, '?')} D{reg},{ea}" if dir_
                    else f"add{SIZES.get(size, '?')} {ea},D{reg}"), nxt

        if top == 0xe:  # shift/rotate - not yet cross-checked against Instructions.fs's ShiftRotate
            size = (op >> 6) & 3
            names = {0: 'as', 1: 'ls', 2: 'rox', 3: 'ro'}
            if size == 3:  # memory shift, count/size implicitly 1/word
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 1)
                d = 'l' if (op >> 8) & 1 else 'r'
                return f"{names[(op >> 9) & 3]}{d} {ea}", nxt
            count_or_reg, ir = (op >> 9) & 7, (op >> 5) & 1
            d = 'l' if (op >> 8) & 1 else 'r'
            src = f"D{count_or_reg}" if ir else f"#{8 if count_or_reg == 0 else count_or_reg}"
            return f"{names[(op >> 3) & 3]}{d}{SIZES.get(size, '?')} {src},D{op & 7}", nxt

        if top == 0:  # ORI/ANDI/SUBI/ADDI/EORI/CMPI/bit-ops/MOVEP - several Instructions.fs patterns
            if (op & 0xff00) == 0x0800:  # static bit ops, e.g. (|BTSTImmediate|_|)
                btype = (op >> 6) & 3
                bitnum = rw(nxt)
                ea, nxt2 = ea_str((op >> 3) & 7, op & 7, nxt + 2, 0)
                names = {0: 'btst', 1: 'bchg', 2: 'bclr', 3: 'bset'}
                return f"{names[btype]} #{bitnum},{ea}", nxt2
            if (op & 0xf100) == 0x0100 and ((op >> 3) & 7) != 1:  # (|BitOpDynamic|_|); eamode=001 -> MOVEP
                btype, reg = (op >> 6) & 3, (op >> 9) & 7
                ea, nxt = ea_str((op >> 3) & 7, op & 7, nxt, 0)
                names = {0: 'btst', 1: 'bchg', 2: 'bclr', 3: 'bset'}
                return f"{names[btype]} D{reg},{ea}", nxt
            # Immediate-to-CCR/SR aliases (mode=111,reg=100 inside ORI/ANDI/EORI's general EA space) -
            # must be checked before the generic immediate-to-ea decode below, since they share the
            # same immop/size/mode/eareg bit positions. See 68k-opcode-space-aliasing memory.
            ccr_sr_aliases = {0x003c: "ori #${:x},CCR", 0x007c: "ori #${:x},SR",
                               0x023c: "andi #${:x},CCR", 0x027c: "andi #${:x},SR",
                               0x0a3c: "eori #${:x},CCR", 0x0a7c: "eori #${:x},SR"}
            if op in ccr_sr_aliases:
                return ccr_sr_aliases[op].format(rw(nxt)), nxt + 2
            immop, size = (op >> 9) & 7, (op >> 6) & 3
            names = {0: 'ori', 1: 'andi', 2: 'subi', 3: 'addi', 5: 'eori', 6: 'cmpi'}
            if immop in names:
                if size == 0:
                    imm, nxt2 = rw(nxt) & 0xff, nxt + 2
                elif size == 1:
                    imm, nxt2 = rw(nxt), nxt + 2
                else:
                    imm, nxt2 = rl(nxt), nxt + 4
                ea, nxt2 = ea_str((op >> 3) & 7, op & 7, nxt2, size)
                return f"{names[immop]}{SIZES.get(size, '?')} #${imm:x},{ea}", nxt2
            if (op & 0xf138) == 0x0108:  # MOVEP - Instructions.fs (|MOVEP|_|)
                dreg, areg, opmode2 = (op >> 9) & 7, op & 7, (op >> 6) & 7
                disp, nxt2 = sext16(rw(nxt)), nxt + 2
                movep_forms = {4: f"movep.w {disp}(A{areg}),D{dreg}", 5: f"movep.l {disp}(A{areg}),D{dreg}",
                               6: f"movep.w D{dreg},{disp}(A{areg})", 7: f"movep.l D{dreg},{disp}(A{areg})"}
                if opmode2 in movep_forms:
                    return movep_forms[opmode2], nxt2
            return f"???(0x{op:04x} top0)", nxt

        return f"???(0x{op:04x})", nxt

    def disassemble(self, start, count=40, stop_at_control_flow=True):
        """Walks forward from `start`, returning [(addr, text), ...]. Stops early at the first
        rts/rte/jmp/bra/illegal/trap/unknown unless stop_at_control_flow is False (e.g. for
        tracing a fixed byte range like the low-memory ROM mirror, where you want every
        instruction in the range regardless of what it is)."""
        addr = start
        lines = []
        stops = ('rts', 'rte', 'jmp', 'bra', 'illegal', 'trap')
        for _ in range(count):
            a0 = addr
            try:
                text, addr = self.decode_one(addr)
            except (IndexError, KeyError) as e:
                lines.append((a0, f"<error {e}>"))
                addr = a0 + 2
                continue
            lines.append((a0, text))
            if stop_at_control_flow and (text.startswith(stops) or 'unknown' in text or '???' in text):
                break
        return lines


def main():
    args = sys.argv[1:]
    rom_path = DEFAULT_ROM_PATH
    if '--rom' in args:
        i = args.index('--rom')
        rom_path = args[i + 1]
        args = args[:i] + args[i + 2:]

    dis = Disassembler(load_rom(rom_path))

    if args and args[0] == '--linear':
        addr = int(args[1], 16)
        count = int(args[2]) if len(args) > 2 else 40
        for pc, txt in dis.disassemble(addr, count=count, stop_at_control_flow=False):
            print(f"  ${pc:06x}: {txt}")
        return

    for a in args:
        addr = int(a, 16)
        print(f"=== {a} ===")
        for pc, txt in dis.disassemble(addr):
            print(f"  ${pc:06x}: {txt}")
        print()


if __name__ == "__main__":
    main()
