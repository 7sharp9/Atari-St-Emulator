"""Raw whole-text scan (every even address, not a linear listing) for every instruction form that can put $36 into an
object's mode byte 31(An) in PowerMonger.  Text segment $10a6..$1c48a (GEMDOS header of DATA/SPRITE40.DAT, text_segment.py);
the scan runs over [lo, hi) given (default $0..$1d000, past the end of text).
Reports: (1) move.b #imm,d16(An) with imm $36 (any displacement; 31 flagged), (2) move.w #imm,30(An) with low byte $36,
move.l #imm,28(An) with low byte $36, (3) every moveq #$36,Dn, (4) every byte/word write with displacement 31 (or word 30 /
long 28) from a register or memory source, so the caller can check its source, (5) addq/subq/addi/subi/or/and/eor on 31(An).
uv run python <this> [ram] [lo] [hi]"""
import sys
from pathlib import Path
here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / "tools" / "rdis.py").exists())
ram = (Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scratchpad/pm123/win/m1_ready.ram").read_bytes()
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x1d000
w = lambda a: (ram[a] << 8) | ram[a + 1]
out = {k: [] for k in ("imm36", "imm36_wide", "moveq36", "regsrc31", "alu31")}
for a in range(lo, hi - 8, 2):
    op = w(a)
    size = op >> 12
    dmode, dreg = (op >> 6) & 7, (op >> 9) & 7
    smode, sreg = (op >> 3) & 7, op & 7
    if size in (1, 3, 2) and dmode == 5:            # move.<b|w|l> <src>,d16(An)
        if smode == 7 and sreg == 4:                # immediate source
            if size == 1:
                imm, disp = w(a + 2) & 0xff, w(a + 4)
                if imm == 0x36:
                    out["imm36"].append((a, f"move.b #$36,{disp}(A{dreg})"))
            elif size == 3:
                imm, disp = w(a + 2), w(a + 4)
                if disp == 30 and imm & 0xff == 0x36:
                    out["imm36_wide"].append((a, f"move.w #${imm:04x},30(A{dreg})"))
            else:
                imm, disp = (w(a + 2) << 16) | w(a + 4), w(a + 6)
                if disp == 28 and imm & 0xff == 0x36:
                    out["imm36_wide"].append((a, f"move.l #${imm:08x},28(A{dreg})"))
        else:
            ext = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 2, 6: 2}.get(smode, None)
            if smode == 7:
                ext = {0: 2, 1: 4, 2: 2, 3: 2}.get(sreg, None)
            if ext is not None:
                disp = w(a + 2 + ext)
                want = {1: 31, 3: 30, 2: 28}[size]
                if disp == want:
                    out["regsrc31"].append((a, f"move.{'bwl'[[1,3,2].index(size)]} src(mode{smode},r{sreg}),{disp}(A{dreg})"))
    if (op & 0xf100) == 0x7000 and (op & 0xff) == 0x36:
        out["moveq36"].append((a, f"moveq #$36,D{(op >> 9) & 7}"))
    # addq/subq.b #n,31(An): 0101 nnn d 00 101 rrr
    if (op & 0xf0f8) == 0x5028 and w(a + 2) == 31:
        out["alu31"].append((a, f"{'subq' if op & 0x100 else 'addq'}.b #{((op >> 9) & 7) or 8},31(A{op & 7})"))
    # addi/subi/ori/andi/eori.b #imm,31(An)
    if (op & 0xf1f8) in (0x0028,) and (op & 0x0e00) in (0x0000, 0x0200, 0x0400, 0x0600, 0x0a00) and w(a + 4) == 31:
        out["alu31"].append((a, f"op ${op:04x} #${w(a+2)&0xff:02x},31(A{op & 7})"))
    # <op>.b Dn,31(An) (add/sub/or/and/eor to memory): 1101/1001/1000/1100/1011 ddd 1 00 101 rrr
    if (op & 0x01f8) == 0x0128 and (op >> 12) in (0xd, 0x9, 0x8, 0xc, 0xb) and w(a + 2) == 31:
        out["alu31"].append((a, f"op ${op:04x} D{(op >> 9) & 7},31(A{op & 7})"))
for k, v in out.items():
    print(f"== {k}: {len(v)}")
    for a, s in v:
        print(f"  ${a:06x}  {s}")
