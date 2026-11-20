"""Reduce one ATARI_TRACE_EVENTS log to a small npz: call targets (direct / indirect counts),
interrupt targets, and a byte coverage bitmap over $0..$7ffff (executed spans).

usage: python reduce_evt.py <log.evt> <out.npz>

Record layout (tools/trace_cfg.py REC): u64 step, u32 pc, u32 target, u16 opcode, u8 kind, u8 flags.
Every flow-control instruction is logged, so execution between consecutive records runs sequentially
from record[i-1].target to record[i].pc; the terminator's own operand words are not counted (a
lower bound of 2 bytes for the terminator, exact for Bcc).
Call classification from the opcode: bsr (6100..61ff) and jsr with mode 7 (abs / pc-relative) are
direct; jsr with An-based modes (2,5,6) is indirect (the behaviour-table style).
"""
import os
import sys
import numpy as np

DT = np.dtype([("step", "<u8"), ("pc", "<u4"), ("tgt", "<u4"), ("op", "<u2"), ("kind", "u1"), ("fl", "u1")])
HDR = 16
MAXA = 0x80000


def reduce(path):
    raw = np.fromfile(path, dtype=np.uint8)
    assert raw[:4].tobytes() == b"A68E", "bad magic"
    rec = raw[HDR:HDR + (len(raw) - HDR) // 20 * 20].view(DT)
    pc = rec["pc"] & 0xFFFFFF
    tg = rec["tgt"] & 0xFFFFFF
    op = rec["op"].astype(np.int64)
    kind = rec["kind"]
    out = {"nrec": np.array([len(rec)]), "step0": np.array([rec["step"][0] if len(rec) else 0]),
           "step1": np.array([rec["step"][-1] if len(rec) else 0])}
    call = kind == 3
    is_bsr = (op >> 8) == 0x61
    mode = (op >> 3) & 7
    direct = call & (is_bsr | (mode == 7))
    indirect = call & ~direct
    for name, m in (("direct", direct), ("indirect", indirect)):
        t, n = np.unique(tg[m], return_counts=True)
        out[name + "_t"], out[name + "_n"] = t, n
    t, n = np.unique(tg[kind == 6], return_counts=True)
    out["int_t"], out["int_n"] = t, n
    # distinct call sites per target (pc of the jsr): lets the aggregator say how many sites call it
    sites = np.unique(np.stack([tg[call], pc[call]]).T, axis=0) if call.any() else np.zeros((0, 2), np.int64)
    out["site_t"], out["site_pc"] = sites[:, 0].astype(np.int64), sites[:, 1].astype(np.int64)
    # coverage: spans [tg[i-1], pc[i]+len]
    start = tg[:-1].astype(np.int64)
    end = pc[1:].astype(np.int64) + np.where((op[1:] >> 12) == 6,
                                              np.where((op[1:] & 0xFF) == 0, 4, np.where((op[1:] & 0xFF) == 0xFF, 6, 2)), 2)
    ok = (end > start) & (end - start < 0x10000)
    out["span_bad"] = np.array([int((~ok).sum())])
    diff = np.zeros(MAXA + 2, np.int64)
    s, e = start[ok], np.minimum(end[ok], MAXA)
    s = s[s < MAXA]
    e = np.minimum(end[ok][start[ok] < MAXA], MAXA)
    # lengths below 64 KB, so unique spans first to keep np.add.at small
    sp, c = np.unique(np.stack([s, e]).T, axis=0, return_counts=True)
    np.add.at(diff, sp[:, 0], 1)
    np.add.at(diff, sp[:, 1], -1)
    cov = np.cumsum(diff)[:MAXA] > 0
    out["cover"] = np.packbits(cov)
    return out


if __name__ == "__main__":
    o = reduce(sys.argv[1])
    np.savez_compressed(sys.argv[2], **o)
    print(f"{sys.argv[1]}: {int(o['nrec'][0])} records, steps {int(o['step0'][0])}..{int(o['step1'][0])}, "
          f"{len(o['direct_t'])} direct + {len(o['indirect_t'])} indirect targets, span_bad {int(o['span_bad'][0])}")
