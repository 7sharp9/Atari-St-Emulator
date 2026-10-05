"""melee_gate.py <calls.txt>: check the enemy-melee-versus-player test ($fa10 -> $fb8c -> $fc34) at every call.
   calls.txt (lua/reclog.lua, CB_FA10=1): one CALL line per entry of $fa10 (the pool C hit-box record in A6, 32 bytes, and the first 128 bytes of the P1 record),
   and a HIT line when the melee damage writer $fc9e fired right after a call.
   Prediction: the record's box = $69000[+2][+3][+4][+20] (words R, L, B, T) + (x +8, y +12 of the record); P1 vulnerable: +0 bit 7 set, +0 bits 0,1 clear, +23 bit 7 clear,
   +0 bit 4 clear, +24 not in {a b c d e f 12 13 14 16 17}, +4 != b, +88 bit 2 clear, +58 bit 4 clear; body box = P1 +64..70;
   hit iff Rbody >= Latk and Lbody < Ratk and Bbody >= Tatk and Tbody < Batk  (the cmp/bmi/bpl chain of $fb9c..$fbb8, first box = D0..D3 = the record's)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
def s16(v): return v - 65536 if v >= 32768 else v
lines = open(sys.argv[1]).read().split("\n")
bad_pose = {0xa, 0xb, 0xc, 0xd, 0xe, 0xf, 0x12, 0x13, 0x14, 0x16, 0x17}
tp = fp = fn = tn = skipped = 0; shown = 0
for i, ln in enumerate(lines):
    if not ln.startswith("CALL"): continue
    _, fr, a6, rec, pl = ln.split(); r = bytes.fromhex(rec); P = bytes.fromhex(pl)
    nxt = lines[i + 1] if i + 1 < len(lines) else ""
    obs = nxt.startswith("HIT")
    vul = P[0] & 0x80 and not (P[0] & 3) and not (P[23] & 0x80) and not (P[0] & 0x10) and P[24] not in bad_pose and P[4] != 0xb and not (P[88] & 4) and not (P[58] & 0x10)
    try:
        a = l(0x69000 + 4 * r[2]); a = l(a + 4 * r[3]); a = l(a + 4 * r[4]); a = l(a + 4 * r[20])
        x = struct.unpack(">H", r[8:10])[0]; y = struct.unpack(">H", r[12:14])[0]
        box = [s16(w(a + 2 * k)) + (x if k < 2 else y) for k in range(4)]
    except Exception:
        skipped += 1; continue
    body = [s16(struct.unpack(">H", P[64 + 2 * k:66 + 2 * k])[0]) for k in range(4)]
    pred = bool(vul) and body[0] >= box[1] and body[1] < box[0] and body[2] >= box[3] and body[3] < box[2]  # first box = the record's (D0..D3), second = the player's body (D4..D7): R2 >= L1 and L2 < R1, B2 >= T1 and T2 < B1
    if pred and obs: tp += 1
    elif pred and not obs: fp += 1
    elif obs and not pred:
        fn += 1
        if shown < 5: shown += 1; print("observed only: frame", fr, "type", r[2], "state", r[3], "dir", r[4], "frame", r[20], "box", box, "body", body, "vul", bool(vul))
    else: tn += 1
print("calls %d (skipped %d unreadable): predicted and observed %d, predicted only %d, observed only %d, neither %d" % (tp + fp + fn + tn, skipped, tp, fp, fn, tn))
