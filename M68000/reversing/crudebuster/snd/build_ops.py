#!/usr/bin/env python3
"""ops.tsv: the 72 sequencer opcodes $90-$d7 (table $E97A, dispatch `jmp ($200F)` at $E977): handler, operand bytes, effect, and the MAME observations
(count of dispatches, operand count seen, channels, first chip register written afterwards).   usage: build_ops.py 'out/rt_*.log'"""
import sys, os, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import analyze_trace as T, songs as S
D = open(os.path.join(HERE, '..', '..', '..', 'scratchpad', 'crudebuster', 'rom', 'cbuster_huc.bin'), 'rb').read()
tab = [D[0x97a + 2 * i] | D[0x97b + 2 * i] << 8 for i in range(72)]
DESC = {
 0: ('rest', 'key off now, set bit4 (suppress next key-on), end the parse: the note length still elapses'),
 1: ('octave+1', '$2380,x += 1 (clamped 0..7)'), 2: ('octave-1', '$2380,x -= 1'),
 3: ('octave=n', '$2380,x = n (clamped 7)'),
 4: ('volume n', '$2200,x = n (x 11-13: n*8), re-apply TL / SSG volume ($EA49)'),
 5: ('legato', 'set bit3 of $2400,x: the gate-time key-off of the next note is skipped'),
 6: ('gate n', '$23C0,x = n; gate ticks = max(1, length*n>>8)'),
 7: ('patch ptr lo hi', 'YM2203 channels 8-10: write inline FM patch (operator regs $30-$9f, FB/ALG) from the pointer via $F53B; YM2151 channels ignore it but the 2 bytes are consumed'),
 8: ('tempo lo hi', '$08/$09 = value, tempo T=$06/$07 = $08/$09 + signed $27 ($E2A4)'),
 9: ('jump lo hi', 'stream pointer = lo|hi<<8'), 10: ('repeat n', 'push (return pointer, n) on the channel stack ($2400 page, ptr $11/$12 from $E2E2/$E2F2)'),
 11: ('end repeat', 'decrement the top count; loop back to the pointer or pop'),
 12: ('call lo hi', 'push return pointer, jump'), 13: ('return', 'pop pointer'),
 14: ('detune +n', '16-bit $2390/$2380 += n, re-apply pitch ($EE72 YM2151/FM, $EE55 SSG)'),
 15: ('transpose +n', '$2380,x += n, re-apply pitch'), 16: ('detune -n', '$2390/$2380 -= n'), 17: ('transpose -n', '$2380,x -= n'),
 18: ('pitch lo hi', '$2390,x = lo, $2380,x = hi, re-apply pitch'),
 19: ('FM TL add', 'YM2203 FM / SSG: add to a carrier operator TL (op, value) (x 11+: value only); YM2151 channels return without reading'),
 20: ('FM TL sub', 'as $a3, subtract'), 21: ('FM TL set', 'as $a3, set'),
 22: ('key on', 'key on now ($EC31): YM2151 reg $08 / YM2203 reg $28'), 23: ('key off', 'key off now ($EC09)'),
 24: ('END', 'end of channel: key off, $2400,x = 0, slot count -1; the last channel of a slot frees the slot ($2310,slot = 0)'),
 25: ('CH3 op freq +16 (op,n)', 'YM2203 channel 3 special mode: 16-bit add to operator freq $2426/$2422,op, rewrite regs $A8-$AE ($EF31)'),
 26: ('CH3 op freq hi + (op,n)', 'add to the high byte only'), 27: ('CH3 op freq -16 (op,n)', '16-bit subtract'), 28: ('CH3 op freq hi - (op,n)', 'subtract high byte only'),
 29: ('CH3 op freq set (op,lo,hi)', 'set the operator frequency, rewrite regs'),
 30: ('SSG mixer tone on', 'YM2203 reg 7 &= ~mask[x]'), 31: ('SSG mixer tone off', 'reg 7 |= mask[x]'), 32: ('SSG mixer noise on', 'reg 7 &= ~mask'), 33: ('SSG mixer noise off', 'reg 7 |= mask'),
 34: ('SSG noise period n', 'YM2203 reg 6 = n'), 35: ('noise +n', 'reg 6 += n'), 36: ('noise -n', 'reg 6 -= n'),
 37: ('volume slide n', '$2270,x = n ? ~n : 0 (target-seeking volume step in $E8BE every 4th IRQ2)'), 38: ('portamento n', '$2260,x = n ? ~n : 0 (pitch slide step $E854)'),
 39: ('PMS n', 'YM2151 reg $38+x bits 4-6'), 40: ('AMS n', 'YM2151 reg $38+x bits 0-1'), 41: ('PMD n', 'YM2151 reg $19 = n|$80'), 42: ('AMD n', 'YM2151 reg $19 = n&$7f'),
 43: ('LFO freq n', 'YM2151 reg $18 = n'), 44: ('LFO wave n', 'YM2151 reg $1b = n&3 | $62&$c0'),
 45: ('LFO sync on', '$2470,x bit7: YM2151 reg $01 test bit pulse at every key-on'), 46: ('LFO sync off', 'clear it'),
 47: ('OKI continue', 'channels 14/15: $60 = 1 so the parser continues after an OKI note trigger'),
 48: ('level n', '$2250,x = n (velocity), re-apply TL'),
 58: ('pan n', 'YM2151 reg $20+x bits 6-7 (RL) = n'),
 59: ('OKI2 start n', 'table entry n of the OKI2 table ($F651 with $53=1)'), 60: ('OKI1 start n', 'table entry n of table A ($F651 with $53=0)'),
 61: ('OKI2 stop all', 'write $78 to OKI2'), 62: ('OKI1 stop all', 'write $78 to OKI1'),
 63: ('CT=0', 'YM2151 reg $1b: $62 &= 3'), 64: ('CT=$c0', 'YM2151 reg $1b: $62 |= $c0, selects OKI2 table C (identity table)'),
 65: ('OKI vol n', '$61 = n (OKI attenuation override)'), 66: ('load patch n', 'YM2151 (x<8): load FM patch n from the patch bank (bank 6 loader $4203, data in banks 7+); YM2203: $4200'),
 67: ('clock param n', '$72 = n (read only by the clock code $FDD9)'), 68: ('$2738 n', '$2738,x = n (read only by FD50/FD77: output to the unread ring $2798)'),
 69: ('attack n', '$2230,x = n, rewrite YM2151 KS/AR regs $80-$9f ($F303)'), 70: ('release n', '$2240,x = n, rewrite D1L/RR regs $e0-$ff ($F338)'),
 71: ('fine+transpose kf tr', '$22B0,x = kf (YM2151 KF), $22C0,x = tr (semitones), re-apply pitch ($E712)'),
}
for i in range(49, 58):
    DESC[i] = ('level $%02x' % [0x10, 0x30, 0x50, 0x70, 0x80, 0x90, 0xb0, 0xd0, 0xf0][i - 49], '$2250,x = preset, re-apply TL')
paths = sorted(sum((glob.glob(a) for a in sys.argv[1:]), []))
cnt, chs, jumps = T.ops(paths)
res = T.op_regs(paths)
with open(os.path.join(HERE, 'ops.tsv'), 'w') as f:
    f.write('opcode\tidx\thandler\tname\tobserved_dispatches\toperand_counts_seen\tchannels_seen\tregs_after(first 4)\teffect\n')
    for i in range(72):
        nm, eff = DESC.get(i, ('?', '?'))
        nd = sum(chs[i].values())
        regs = ', '.join('%s:%s' % (k[0][2:], k[1]) for k, v in sorted(res.get(i, {}).items(), key=lambda kv: -kv[1])[:4])
        f.write('%02x\t%d\t%04x\t%s\t%d\t%s\t%s\t%s\t%s\n' % (0x90 + i, i, tab[i], nm, nd, dict(cnt.get(i, {})) or '-', ','.join(str(c) for c in sorted(chs[i])) or '-', regs or '-', eff))
print('wrote ops.tsv from %d traces' % len(paths))
