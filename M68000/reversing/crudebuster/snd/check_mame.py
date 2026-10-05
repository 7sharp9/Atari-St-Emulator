#!/usr/bin/env python3
"""Compare h6280dis.py with MAME's own HuC6280 disassembly (lua/dasm_banks.lua output, debugger `dasm`) over all 8 banks.
1. linear sweep of each 8 KiB bank from logical $e000: line-by-line text and length match.
2. every instruction the recursive descent reached (rd): found on MAME's chain for its bank (or reported).
Run: CB_OUT=out cbmame.sh script lua/dasm_banks.lua ; python3 check_mame.py"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h6280dis as H
OUT = os.environ.get('CB_OUT') or os.path.join(HERE, 'out')
rom = H.Rom()

def norm(s): return re.sub(r'\s+', ' ', s.strip().lower())

tot = bad = 0
mame = {}
for b in range(8):
    lines = []
    for l in open(os.path.join(OUT, 'mame_dasm_bank%d.txt' % b)):
        m = re.match(r'([0-9A-F]{4}): ((?:[0-9A-F]{2} ){1,7}?)\s*([a-z].*)$', l.rstrip('\n'))
        if m: lines.append((int(m.group(1), 16), bytes.fromhex(m.group(2).replace(' ', '')), m.group(3)))
    mpr = [0] * 8; mpr[7] = b
    # my linear sweep over the same span
    pc = 0xe000; mine = []
    while pc < 0x10000:
        op, mn, mode, n, a = H.decode(rom, mpr, pc)
        mine.append((pc, bytes([op] + a), H.fmt(mn, mode, a, pc, op))); pc += n
    mm = {x[0]: x for x in lines}
    for pc, bts, txt in mine:
        tot += 1
        x = mm.get(pc)
        if x is None or x[1] != bts or norm(x[2]) != norm(txt):
            bad += 1
            if bad <= 10: print('MISMATCH bank', b, '%04x' % pc, bts.hex(), txt, '|', x)
    mame[b] = mm
print('linear sweep: %d instructions compared, %d mismatches' % (tot, bad))

# reachable code (reset + IRQ vectors + the 72 sequencer opcode handlers)
w, roots, idle = H.full_walk(rom)
found = miss = badr = 0
off = []
for p, (pc, txt, bts, mpr, n) in sorted(w.insn.items()):
    b = p >> 13
    # MAME line for physical p in its bank at logical 0xe000 + (p & 0x1fff)
    la = 0xe000 + (p & 0x1fff)
    x = mame[b].get(la)
    if x is None:
        miss += 1; off.append((b, la, p, pc, txt, bts)); continue
    found += 1
    if x[1] != bts or norm(x[2]) != norm(txt.replace('$%04X' % pc, '$%04X' % pc)):
        # branch targets are logical addresses of the walker's mapping; MAME's bank view at $e000 differs by base: compare only mnemonic/length
        if x[1] == bts and x[2].split()[0].lower() == txt.split()[0].lower(): continue
        badr += 1
        if badr <= 10: print('REACH MISMATCH', '%04x' % pc, txt, '|', x)
print('reachable: %d instructions, %d on MAME linear chain with identical bytes and mnemonic, %d off-chain (not compared), %d mismatches' % (len(w.insn), found, miss, badr))

# the off-chain instructions: MAME's disassembler started exactly at each of them (second run, lua/dasm_points.lua reads out/offchain.txt)
with open(os.path.join(OUT, 'offchain.txt'), 'w') as f:
    for b, la, p, pc, txt, bts in off: f.write('%d %04x\n' % (b, la))
res = os.path.join(OUT, 'offchain_result.txt')
if os.path.exists(res):
    got = {}
    for l in open(res):
        pp = l.rstrip('\n').split('\t')
        if len(pp) == 3: got[(int(pp[0]), int(pp[1], 16))] = pp[2]
    okc = 0
    for b, la, p, pc, txt, bts in off:
        m = re.match(r'([0-9A-F]{4}): ((?:[0-9A-F]{2} ){1,7}?)\s*([a-z].*)$', got.get((b, la), ''))
        if m and bytes.fromhex(m.group(2).replace(' ', '')) == bts and m.group(3).split()[0].lower() == txt.split()[0].lower(): okc += 1
        else: print('OFF-CHAIN MISMATCH', b, '%04x' % la, txt, got.get((b, la)))
    print('off-chain instructions re-disassembled by MAME at their own address (lua/dasm_points.lua): bytes and mnemonic identical %d of %d' % (okc, len(off)))
