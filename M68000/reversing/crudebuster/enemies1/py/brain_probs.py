"""brain_probs.py: exact next-state probabilities of the shared brain $2438a, decoded from the ROM tables and the leaf code (no sampling).

The brain (`$2438a`, 40 call sites) picks a table from the player's lane (case A: my y in (py-$20, py+$60]; B: more than $60 below; C: above), then
[type][dx >> 4] (16 buckets, dx = |px - x|, dx >= $100 forces state 7), and in case A also [player action +46 & 15][player sub-action +47]. The entry is a *leaf*
routine. A leaf is one of
  - a setter: `move.b #N,3(A6)` (plus a velocity preamble `move.w #v,D7 / jsr $2280c|$22844` for the jump setters, `$256fc`, `$25740`): state N;
  - a random chooser: `btst #7,1(A6) / beq end / jsr $ea44 / andi.w #m,D0 / lsl.w #2,D0 / lea T(PC),A0 / movea.l 0(A0,D0.w),A1 / jsr (A1)`:
    nothing happens until the animation has finished (+1 bit 7), then one of the m+1 setters in T is taken with equal probability;
  - a forwarder: `jsr X(PC) / nop / rts`.
The result for every (type, case, bucket, player action, player sub-action) is a distribution over the next state, `wait` meaning "no change this frame".
Usage: brain_probs.py [type ...]              text table (case A summed over the player's actions and sub-actions, plus the idle-player row)
       brain_probs.py --json                  every type as JSON on stdout (used by infographic/build_data.py)
Conditional leaves are shown as `N*`: state N when the player is not held, not blinking and on the ground (y + $10 >= mine, action < $a), otherwise state 6.
Needs scratchpad/crudebuster/all_lin.txt (linear listing, see ../../../sessions/crudebuster.md "Known traps") and the decrypted image."""
import collections, json, os, re, struct, sys
ROOT = os.environ.get("M68000_ROOT")
if not ROOT:
    d = os.path.abspath(os.path.dirname(__file__))
    while d != "/" and not os.path.exists(os.path.join(d, "tools", "rdis.py")): d = os.path.dirname(d)
    ROOT = d
ROM = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def L(a): return struct.unpack(">I", ROM[a:a + 4])[0]
LIN = {}
for ln in open(os.path.join(ROOT, "scratchpad/crudebuster/all_lin.txt")):
    m = re.match(r"\s*\$([0-9a-f]+):\s*(\S+)\s*(.*)", ln)
    if m: LIN[int(m.group(1), 16)] = (m.group(2), m.group(3).strip())
ADDRS = sorted(LIN)
NEXT = {a: ADDRS[i + 1] for i, a in enumerate(ADDRS[:-1])}
_memo = {}

def leaf(a, depth=0):
    """-> dict state -> probability, plus key 'wait' (no change) and 'unk' (not decoded); the sum is 1."""
    if a in _memo: return _memo[a]
    res = _leaf(a, depth); _memo[a] = res; return res

def _scan(a, n=60):
    out = []; p = a
    while p in LIN and len(out) < n:
        out.append((p, LIN[p]))
        if LIN[p][0] == "rts": break
        p = NEXT.get(p, -1)
    return out

def _leaf(a, depth):
    if depth > 6: return {"unk": 1.0}
    ins = []; p = a
    while p in LIN and len(ins) < 24:
        ins.append((p, LIN[p])); op = LIN[p][0]
        if op in ("rts", "bra", "jmp"): break
        p = NEXT.get(p, -1)
    ops = [i[1][0] + " " + i[1][1] for i in ins]
    text = "\n".join(ops)
    m = re.search(r"move\.b #\$([0-9a-f]+),3\(A6\)", text)
    if "$ea44" in text:  # random chooser
        mask = int(re.search(r"andi\.w #\$([0-9a-f]+),D0", text).group(1), 16)
        n = mask + 1
        mlea = re.search(r"lea \S+ == \$([0-9a-f]+),A0", text)
        if not mlea:  # `jsr $ea44 / andi.w #m,D0 / cmpi.w #k,D0 / beq|bne rts / move.b #N,3(A6)`: the state is taken with probability 1/n (bne) or 1 - 1/n (beq), else nothing
            sn = int(re.search(r"move\.b #\$([0-9a-f]+),3\(A6\)", "\n".join(l[1][0] + " " + l[1][1] for l in _scan(a))).group(1), 16)
            beq = "beq" in text
            pr = 1 - 1.0 / n if beq else 1.0 / n
            return {sn: pr, "wait": 1 - pr}
        tbl = int(mlea.group(1), 16)
        out = collections.Counter()
        for i in range(n):
            for s, pr in leaf(L(tbl + 4 * i), depth + 1).items(): out[s] += pr / n
        return dict(out)
    if m:
        return {int(m.group(1), 16): 1.0}
    f = re.search(r"jsr \S+ == \$([0-9a-f]+)", text)
    if f and len(ins) <= 3: return leaf(int(f.group(1), 16), depth + 1)
    # a conditional leaf (grab attempt `$24de6`, `$26150`): tests on the player's flags and lane, then sets state N or falls back to idle 6.
    # Reported as 'N*' (N when the conditions hold, else 6); the conditions are listed in the module docstring's note.
    states = []; p = a; n = 0
    while p in LIN and n < 90:
        mm = re.search(r"move\.b #\$([0-9a-f]+),3\(A6\)", LIN[p][0] + " " + LIN[p][1])
        if mm: states.append(int(mm.group(1), 16))
        if LIN[p][0] == "rts": break
        p = NEXT.get(p, -1); n += 1
    if states and 6 in states and len(set(states)) == 2:
        other = [x for x in states if x != 6][0]
        return {"%x*" % other: 1.0}
    return {"unk": 1.0}

def gated(a):
    p = a; n = 0
    while p in LIN and n < 3:
        if LIN[p][0] == "btst" and LIN[p][1].startswith("#7,1(A6)"): return True
        p = NEXT.get(p, -1); n += 1
    return False

def dist(a):
    d = dict(leaf(a))
    return d, gated(a)

BRAIN = {t: L(0x24508 + 4 * t) for t in range(80)}
DEFAULT = 0x26550

def bucket_tables(t):
    """-> {case: {bucket: leaf or {action: {sub: leaf}}}}"""
    out = {"A": {}, "B": {}, "C": {}}
    t1 = L(0x24508 + 4 * t)
    for b in range(16):
        t2 = L(t1 + 4 * b); out["A"][b] = {}
        for act in range(16):
            t3 = L(t2 + 4 * act)
            lst = []
            for k in range(16):
                if t3 + 4 * k + 4 > len(ROM): break
                v = L(t3 + 4 * k)
                if not (0x10000 <= v < 0x2c000 and v % 2 == 0): break
                lst.append(v)
            out["A"][b][act] = lst
    for case, base in (("B", 0x24644), ("C", 0x24780)):
        t1 = L(base + 4 * t)
        for b in range(16): out[case][b] = L(t1 + 4 * b)
    return out

def case_dist(leaf_addr):
    d, g = dist(leaf_addr)
    return d, g

def summarise(t, idle_action=8):
    """probabilities per bucket for the player idle (action 8, sub 0): dict case -> bucket -> (dist, gated)"""
    tabs = bucket_tables(t)
    res = {}
    for case in "ABC":
        res[case] = {}
        for b in range(16):
            if case == "A": la = tabs["A"][b][idle_action][0]
            else: la = tabs[case][b]
            res[case][b] = case_dist(la)
    return res

def case_a_by_action(t, b):
    tabs = bucket_tables(t)
    return {act: [case_dist(a) for a in tabs["A"][b][act]] for act in range(16)}

def fmt(d):
    return " ".join("%s:%d%%" % (("%x" % s) if isinstance(s, int) else s, round(100 * p)) for s, p in sorted(d.items(), key=lambda kv: str(kv[0])) if p > 0.004)

if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--json"]:
        out = {}
        for t in range(80):
            if BRAIN[t] == DEFAULT: continue
            s = summarise(t)
            out[t] = {c: {b: {"gated": g, "p": {str(k): v for k, v in d.items()}} for b, (d, g) in s[c].items()} for c in s}
        json.dump(out, sys.stdout)
        sys.exit(0)
    types = [int(a) for a in args] or [t for t in range(80) if BRAIN[t] != DEFAULT]
    for t in types:
        print("type %d (table %06x)" % (t, BRAIN[t]))
        s = summarise(t)
        for case in "ABC":
            print(" case %s, player idle:" % case)
            for b in range(16):
                d, g = s[case][b]
                print("  dx %02x-%02x %s %s" % (b * 16, b * 16 + 15, "[on anim end]" if g else "[at once]   ", fmt(d)))
