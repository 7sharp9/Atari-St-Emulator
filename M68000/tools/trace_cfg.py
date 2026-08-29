"""Post-processor for the emulator's structured flow-event log (ATARI_TRACE_EVENTS).

The emulator (Atari.TraceEvents, wired into AtartSt.Step) writes one compact binary
record per flow-control instruction - or per instruction with ATARI_TRACE_EVENTS_ALL=1.
This tool reconstructs, from that stream alone (no re-execution, no full disassembly):

  * basic blocks that actually executed, with their real start/end addresses and hit counts
  * a control-flow graph (Graphviz DOT), edges labelled taken / not-taken / call / ret / fall
  * a call graph (Graphviz DOT), built by simulating the call/return/trap/interrupt stack
  * an executed-address coverage map (merged byte ranges, split ROM vs RAM)

Block boundaries are derived, not disassembled, so they can be cross-checked against
tools/disassemble.py (which is itself cross-checked against ../Instructions.fs) - use
--disasm to print each ROM block's instructions from that disassembler.

Binary format (little-endian):
  header : "A68E" | version:u8 (=1) | recLen:u8 (=20) | reserved:u16 | startStep:u64
  record : stepCount:u64 | pc:u32 | target:u32 | opcode:u16 | kind:u8 | flags:u8

kind: 0 seq  1 branch-taken  2 branch-not-taken  3 call  4 ret  5 trap  6 interrupt

Usage:
  python trace_cfg.py boot.evt                       # summary + coverage to stdout
  python trace_cfg.py boot.evt --cfg cfg.dot         # write CFG DOT
  python trace_cfg.py boot.evt --callgraph cg.dot    # write call graph DOT
  python trace_cfg.py boot.evt --blocks blocks.txt   # write the block table
  python trace_cfg.py boot.evt --names names.txt     # addr<TAB>name sidecar for labels
  python trace_cfg.py boot.evt --disasm --rom ../TOS100UK.IMG   # annotate ROM blocks
  python trace_cfg.py boot.evt --range fc0000 fc4000 # restrict to a PC window
  render:  dot -Tsvg cfg.dot -o cfg.svg
"""
import argparse
import bisect
import struct
import sys
import subprocess
import os
from collections import Counter, defaultdict

KSEQ, KBTAKEN, KBNOTTAKEN, KCALL, KRET, KTRAP, KINT = range(7)
KIND_NAME = {KSEQ: "seq", KBTAKEN: "branch-taken", KBNOTTAKEN: "branch-not-taken",
             KCALL: "call", KRET: "ret", KTRAP: "trap", KINT: "interrupt"}

HEADER = struct.Struct("<4sBBHQ")
REC = struct.Struct("<QIIHBB")


def load(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, reclen, _, start = HEADER.unpack_from(data, 0)
    if magic != b"A68E":
        sys.exit(f"{path}: not an A68E event log (magic {magic!r})")
    if reclen != REC.size:
        sys.exit(f"{path}: record length {reclen} != {REC.size}, format mismatch")
    recs = []
    off = HEADER.size
    while off + REC.size <= len(data):
        sc, pc, tgt, op, kind, _flags = REC.unpack_from(data, off)
        recs.append((sc, pc, tgt, op, kind))
        off += REC.size
    return ver, start, recs


# --- terminator classification straight from the opcode word (mirrors Instructions.fs) -------

def bcc_len(op):
    """Instruction length in bytes for a Bcc / BSR word (top nibble 6)."""
    lo = op & 0xFF
    return 4 if lo == 0x00 else (6 if lo == 0xFF else 2)


def terminator_mnemonic(op, kind):
    top = (op >> 12) & 0xF
    if kind == KINT:
        return "(interrupt)"
    if top == 0xA:
        return "line-a $%04x" % op
    if top == 0xF:
        return "line-f $%04x" % op
    if top == 0x6:
        cond = (op >> 8) & 0xF
        names = ["ra", "sr", "hi", "ls", "cc", "cs", "ne", "eq",
                 "vc", "vs", "pl", "mi", "ge", "lt", "gt", "le"]
        return ("bsr" if cond == 1 else "b" + names[cond])
    if top == 0x4:
        if op in (0x4E75, 0x4E73, 0x4E77):
            return {0x4E75: "rts", 0x4E73: "rte", 0x4E77: "rtr"}[op]
        if (op & 0xFFC0) == 0x4E80:
            return "jsr"
        if (op & 0xFFC0) == 0x4EC0:
            return "jmp"
        if (op & 0xFFF0) == 0x4E40:
            return "trap #%d" % (op & 0xF)
        if op == 0x4E76:
            return "trapv"
        if op == 0x4AFC:
            return "illegal"
        if (op & 0xF1C0) == 0x4180:
            return "chk"
    if top == 0x5 and (op & 0xF0F8) == 0x50C8:
        cond = (op >> 8) & 0xF
        names = ["t", "f", "hi", "ls", "cc", "cs", "ne", "eq",
                 "vc", "vs", "pl", "mi", "ge", "lt", "gt", "le"]
        return "db" + names[cond]
    return "op $%04x" % op


def is_conditional(op):
    top = (op >> 12) & 0xF
    if top == 0x6:
        return ((op >> 8) & 0xF) >= 2          # Bcc, not BRA/BSR
    if top == 0x5:
        return (op & 0xF0F8) == 0x50C8         # DBcc
    return False


def fallthrough_addr(pc, op):
    """Address of the instruction after a conditional branch / BSR, or None if not computable."""
    top = (op >> 12) & 0xF
    if top == 0x6:
        return pc + bcc_len(op)
    if top == 0x5 and (op & 0xF0F8) == 0x50C8:
        return pc + 4
    return None


# --- reconstruction ------------------------------------------------------------------------

class Block:
    __slots__ = ("start", "end", "term_op", "term_kind", "count", "split")

    def __init__(self, start, end, op, kind):
        self.start = start          # first byte of the block
        self.end = end              # address of the terminator instruction
        self.term_op = op
        self.term_kind = kind
        self.count = 0
        self.split = False          # True if this block is an artificial head of a split run

    def key(self):
        return (self.start, self.end)


def reconstruct(recs, lo, hi):
    """Returns (blocks dict keyed (start,end), edges Counter keyed (src_end,dst_start,label),
    call_edges Counter keyed (caller,callee), func_hits Counter, leaders set, kind_counts)."""
    in_win = lambda a: lo <= a < hi

    # leaders: every place a run can begin
    leaders = set()
    for (_sc, pc, tgt, op, kind) in recs:
        leaders.add(tgt)
        ft = fallthrough_addr(pc, op)
        if ft is not None:
            leaders.add(ft)
        if kind == KINT:
            leaders.add(pc)   # the preempted instruction resumes here after the handler returns

    blocks = {}
    edges = Counter()
    call_edges = Counter()
    func_hits = Counter()
    kind_counts = Counter()

    run_start = None
    call_stack = ["ENTRY"]
    func_hits["ENTRY"] += 1
    leaders_sorted = sorted(leaders)

    def emit_run(start, end, op, kind):
        """Materialise the executed run [start, end] (end = terminator address), splitting it at
        any leader strictly inside. Wires fall-through edges between the split segments and returns
        the terminator segment's start address, or None."""
        if start is None or end < start:
            return None
        i = bisect.bisect_right(leaders_sorted, start)
        j = bisect.bisect_left(leaders_sorted, end)
        seg_starts = [start] + leaders_sorted[i:j]
        seg_starts = sorted(set(seg_starts))
        for a, b_end in zip(seg_starts, seg_starts[1:]):
            blk = blocks.get((a, b_end))
            if blk is None:
                blk = blocks[(a, b_end)] = Block(a, b_end, 0, -1)
                blk.split = True
            blk.count += 1
        last_start = seg_starts[-1]
        blk = blocks.get((last_start, end))
        if blk is None:
            blk = blocks[(last_start, end)] = Block(last_start, end, op, kind)
        blk.count += 1
        for a, b_start in zip(seg_starts, seg_starts[1:] + [last_start]):
            if a != b_start:
                edges[(a, b_start, "fall")] += 1
        return last_start

    for (_sc, pc, tgt, op, kind) in recs:
        kind_counts[kind] += 1
        if kind == KSEQ:
            continue           # linear step (ATARI_TRACE_EVENTS_ALL): not a block boundary
        if run_start is None:
            run_start = pc     # first observed run: best guess is it started at its own terminator
        if not (in_win(pc) or in_win(tgt)):
            run_start = tgt
            continue

        src = emit_run(run_start, pc, op, kind)

        # edge from this block to wherever we actually went next
        if src is not None:
            label = {KBTAKEN: "taken", KBNOTTAKEN: "not-taken", KCALL: "call",
                     KRET: "ret", KTRAP: "trap", KINT: "int"}.get(kind, "goto")
            edges[(src, tgt, label)] += 1
            # the branch's other outgoing edge (path not taken this iteration), count 0 = unexecuted
            if is_conditional(op) and kind == KBTAKEN:
                ft = fallthrough_addr(pc, op)
                if ft is not None and in_win(ft):
                    edges.setdefault((src, ft, "not-taken"), 0)

        # call-graph bookkeeping
        cur = call_stack[-1]
        if kind == KCALL:
            call_edges[(cur, tgt)] += 1
            call_stack.append(tgt)
            func_hits[tgt] += 1
        elif kind == KTRAP:
            call_edges[(cur, tgt)] += 1
            call_stack.append(tgt)
            func_hits[tgt] += 1
        elif kind == KINT:
            call_edges[(cur, tgt)] += 1
            call_stack.append(("IRQ", tgt))
            func_hits[("IRQ", tgt)] += 1
        elif kind == KRET:
            if len(call_stack) > 1:
                call_stack.pop()

        run_start = tgt

    coalesce(blocks, edges)
    return blocks, edges, call_edges, func_hits, leaders, kind_counts


def coalesce(blocks, edges):
    """Merge maximal linear chains: if block A's only successor is B (via a fall edge) and B's only
    predecessor is A, fuse them. Collapses the block splitting that interrupt preemption and shared
    fall-through leaders introduce, back into single basic blocks."""
    changed = True
    while changed:
        changed = False
        out_of = defaultdict(list)
        in_to = defaultdict(list)
        for (s, d, lbl) in edges:
            out_of[s].append((d, lbl))
            in_to[d].append((s, lbl))
        start_to_key = {k[0]: k for k in blocks}
        for a_start, outs in list(out_of.items()):
            if len(outs) != 1:
                continue
            b_start, lbl = outs[0]
            if lbl != "fall" or b_start == a_start:
                continue
            if len(in_to.get(b_start, [])) != 1:
                continue
            ka, kb = start_to_key.get(a_start), start_to_key.get(b_start)
            if ka is None or kb is None or ka not in blocks or kb not in blocks:
                continue
            A, B = blocks[ka], blocks[kb]
            merged = Block(A.start, B.end, B.term_op, B.term_kind)
            merged.count = A.count
            merged.split = A.split and B.split
            del blocks[ka]
            del blocks[kb]
            blocks[(merged.start, merged.end)] = merged
            for (s, d, l), c in list(edges.items()):
                if s == b_start:
                    del edges[(s, d, l)]
                    edges[(a_start, d, l)] += c
            del edges[(a_start, b_start, "fall")]
            changed = True
            break


# --- coverage ----------------------------------------------------------------------------

def instr_len(pc, tgt, op):
    """Best-effort byte length of the instruction at pc. Exact when the trace recorded a linear
    successor (tgt just past pc); otherwise derived from the opcode for the branch family, else 2."""
    if 2 <= tgt - pc <= 16:
        return tgt - pc
    top = (op >> 12) & 0xF
    if top == 0x6:
        return bcc_len(op)
    if top == 0x5 and (op & 0xF0F8) == 0x50C8:
        return 4
    return 2


def coverage(recs, lo, hi, exact):
    """Merged executed byte ranges. With ATARI_TRACE_EVENTS_ALL every instruction is present, so
    this is exact; with a flow-only log only the branch instructions and run boundaries are known,
    so straight-line stretches between them are inferred as covered from run start to terminator."""
    intervals = []
    if exact:
        for (_sc, pc, tgt, op, _k) in recs:
            if lo <= pc < hi:
                intervals.append((pc, pc + instr_len(pc, tgt, op)))
    else:
        run_start = None
        for (_sc, pc, tgt, op, kind) in recs:
            if kind == KSEQ:
                continue
            if run_start is None:
                run_start = pc
            if lo <= pc < hi:
                intervals.append((min(run_start, pc), pc + instr_len(pc, tgt, op)))
            run_start = tgt
    intervals.sort()
    merged = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


# --- names -------------------------------------------------------------------------------

def load_names(path):
    names = {}
    if not path:
        return names
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.replace("\t", " ").split()
            addr = int(parts[0], 16)
            names[addr] = " ".join(parts[1:]) if len(parts) > 1 else ""
    return names


def name_for(addr, names):
    if isinstance(addr, tuple):
        return "IRQ_%06x" % addr[1]
    if addr == "ENTRY":
        return "ENTRY"
    if addr in names and names[addr]:
        return names[addr]
    region = "sub" if addr >= 0xE00000 else "ram"
    return "%s_%06x" % (region, addr)


# --- disasm cross-check ----------------------------------------------------------------

def disasm_block(b, rom_path):
    tool = os.path.join(os.path.dirname(__file__), "disassemble.py")
    # a generous upper bound on instruction count for the byte span
    n = max(1, (b.end - b.start) // 2 + 1)
    try:
        out = subprocess.run([sys.executable, tool, "--rom", rom_path, "--linear",
                              "%x" % b.start, str(n)],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.rstrip()
    except Exception as e:
        return f"    (disasm failed: {e})"


# --- DOT emitters --------------------------------------------------------------------------

def write_cfg(path, blocks, edges, names):
    starts = {k[0] for k in blocks}

    def node_id(addr):
        return "b_%06x" % addr

    with open(path, "w") as f:
        f.write("digraph cfg {\n  node [shape=box fontname=\"monospace\" fontsize=9];\n")
        for k, b in sorted(blocks.items()):
            term = "split" if b.split else terminator_mnemonic(b.term_op, b.term_kind)
            nm = names.get(b.start)
            head = (nm + "\\n") if nm else ""
            f.write('  %s [label="%s$%06x-$%06x\\n%s  x%d"];\n'
                    % (node_id(b.start), head, b.start, b.end, term, b.count))
        # any edge destination that isn't itself a known block start (jump into unlogged code)
        for (src, dst, label), c in sorted(edges.items()):
            if dst not in starts:
                f.write('  %s [label="$%06x\\n(not traced)" style=dashed];\n' % (node_id(dst), dst))
                starts.add(dst)
        for (src, dst, label), c in sorted(edges.items()):
            style = {"not-taken": "dashed", "call": "bold", "ret": "dotted"}.get(label, "solid")
            color = {"call": "blue", "ret": "gray40", "int": "red", "trap": "purple"}.get(label, "black")
            lbl = label if c <= 0 else "%s x%d" % (label, c)
            f.write('  %s -> %s [label="%s" style=%s color=%s fontsize=8];\n'
                    % (node_id(src), node_id(dst), lbl, style, color))
        f.write("}\n")


def write_callgraph(path, call_edges, func_hits, names):
    def nid(a):
        if isinstance(a, tuple):
            return "irq_%06x" % a[1]
        if a == "ENTRY":
            return "entry"
        return "f_%06x" % a

    with open(path, "w") as f:
        f.write("digraph callgraph {\n  node [shape=ellipse fontname=\"monospace\" fontsize=9];\n")
        nodes = set()
        for (caller, callee) in call_edges:
            nodes.add(caller)
            nodes.add(callee)
        for a in sorted(nodes, key=lambda x: (0, "") if x == "ENTRY" else (1, str(x))):
            f.write('  %s [label="%s\\nx%d"];\n' % (nid(a), name_for(a, names), func_hits.get(a, 0)))
        for (caller, callee), c in sorted(call_edges.items(), key=lambda kv: -kv[1]):
            f.write('  %s -> %s [label="x%d" fontsize=8];\n' % (nid(caller), nid(callee), c))
        f.write("}\n")


# --- main --------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log")
    ap.add_argument("--cfg", help="write control-flow graph as Graphviz DOT")
    ap.add_argument("--callgraph", help="write call graph as Graphviz DOT")
    ap.add_argument("--blocks", help="write the basic-block table")
    ap.add_argument("--names", help="addr<TAB>name sidecar, used for graph labels")
    ap.add_argument("--range", nargs=2, metavar=("LO", "HI"),
                    help="restrict to PC window [LO,HI) (hex)")
    ap.add_argument("--disasm", action="store_true",
                    help="annotate ROM blocks via tools/disassemble.py")
    ap.add_argument("--rom", default=os.path.join(os.path.dirname(__file__), "..", "TOS100UK.IMG"))
    args = ap.parse_args()

    lo, hi = 0, 1 << 32
    if args.range:
        lo = int(args.range[0], 16)
        hi = int(args.range[1], 16)

    ver, start, recs = load(args.log)
    names = load_names(args.names)
    blocks, edges, call_edges, func_hits, leaders, kc = reconstruct(recs, lo, hi)

    print("event log       : %s" % args.log)
    print("format version  : %d   start step: %d   records: %d" % (ver, start, len(recs)))
    print("kind histogram  : " + "  ".join("%s=%d" % (KIND_NAME[k], kc[k]) for k in sorted(kc)))
    print("basic blocks    : %d" % len(blocks))
    print("call-graph nodes: %d   edges: %d" % (
        len({x for e in call_edges for x in e}), len(call_edges)))

    exact = kc[KSEQ] > 0
    cov = coverage(recs, lo, hi, exact)
    rom_bytes = sum(e - s for s, e in cov if s >= 0xE00000)
    ram_bytes = sum(e - s for s, e in cov if s < 0xE00000)
    print("coverage        : %d ranges, ROM %d bytes, RAM %d bytes  (%s)"
          % (len(cov), rom_bytes, ram_bytes,
             "exact" if exact else "approx - re-run with ATARI_TRACE_EVENTS_ALL=1 for exact"))
    print("\nexecuted address ranges [start,end):")
    for s, e in cov:
        print("  $%06x - $%06x  (%d bytes)" % (s, e, e - s))

    print("\nhottest basic blocks:")
    for b in sorted(blocks.values(), key=lambda b: -b.count)[:15]:
        term = "split" if b.split else terminator_mnemonic(b.term_op, b.term_kind)
        print("  $%06x-$%06x  x%-8d %s" % (b.start, b.end, b.count, term))

    print("\nhottest call edges:")
    for (caller, callee), c in sorted(call_edges.items(), key=lambda kv: -kv[1])[:15]:
        print("  %-18s -> %-18s x%d" % (name_for(caller, names), name_for(callee, names), c))

    if args.blocks:
        with open(args.blocks, "w") as f:
            f.write("# start   end      count    terminator\n")
            for b in sorted(blocks.values(), key=lambda b: b.start):
                term = "split" if b.split else terminator_mnemonic(b.term_op, b.term_kind)
                f.write("%08x %08x %8d  %s\n" % (b.start, b.end, b.count, term))
                if args.disasm and b.start >= 0xE00000:
                    f.write(disasm_block(b, args.rom) + "\n")
        print("\nwrote %s" % args.blocks)

    if args.cfg:
        write_cfg(args.cfg, blocks, edges, names)
        print("wrote %s  (dot -Tsvg %s -o cfg.svg)" % (args.cfg, args.cfg))
    if args.callgraph:
        write_callgraph(args.callgraph, call_edges, func_hits, names)
        print("wrote %s" % args.callgraph)


if __name__ == "__main__":
    main()
