"""Compact fingerprint of every state body of a pool A type handler (see states.py): velocities (px/frame, 16.16 fixed), next states,
spawned objects, sounds, timers, brain/terrain calls.  usage: fingerprint.py <type> [<type> ...]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import states
def sv(x):
    x = int(x, 16)
    if x >= 0x80000000: x -= 1 << 32
    return x / 65536.0
def body(t, entry, nxt):
    return [(a, tx) for a, tx in ((int(m.group(1), 16), m.group(2)) for m in (re.match(r"\s+\$([0-9a-f]+):\s*(.*)", l) for l in states.LIN) if m) if entry <= a < nxt]
def fp(t):
    s, e = states.hrange(t)
    tabs = states.tables(t)
    ents = {}
    for a, T, ent in tabs:
        for i, v in enumerate(ent): ents.setdefault(v, []).append(i)
    starts = sorted(v for v in ents if s <= v < e)
    out = []
    for k, v in enumerate(starts):
        nxt = starts[k+1] if k + 1 < len(starts) else e
        L = body(t, v, nxt)
        info = []
        d6 = None; d7 = None
        for a, tx in L:
            m = re.match(r"move\.l #\$([0-9a-f]+),22\(A6\)", tx)
            if m: info.append("vx=%+.3f" % sv(m.group(1)))
            m = re.match(r"move\.l #\$([0-9a-f]+),26\(A6\)", tx)
            if m: info.append("vy=%+.3f" % sv(m.group(1)))
            m = re.match(r"move\.b #\$([0-9a-f]+),3\(A6\)", tx)
            if m: info.append("->%x" % int(m.group(1), 16))
            m = re.match(r"move\.b #\$([0-9a-f]+),D6", tx)
            if m: d6 = int(m.group(1), 16)
            m = re.match(r"moveq #(\d+),D6", tx)
            if m: d6 = int(m.group(1))
            m = re.match(r"moveq #(\d+),D7", tx)
            if m: d7 = int(m.group(1))
            m = re.match(r"move\.b #\$([0-9a-f]+),D7", tx)
            if m: d7 = int(m.group(1), 16)
            m = re.match(r"move\.w #\$([0-9a-f]+),D7", tx)
            if m: d7 = int(m.group(1), 16)
            if "jsr $e1c.l" in tx: info.append("snd %s" % d7)
            if "jsr $21e72.l" in tx: info.append("spawnC(type %s)" % d6)
            if "jsr $21eb6.l" in tx: info.append("spawnA(type %s,var %s)" % (d6, d7))
            if "jsr $21efa.l" in tx: info.append("spawnB(type %s,var %s)" % (d6, d7))
            if "jsr $1c8a.l" in tx: info.append("load_assets(%s)" % d7)
            if "$22856" in tx: info.append("arc")
            if "$2438a" in tx: info.append("BRAIN")
            if "$226e4" in tx: info.append("walk_collide")
            if "$22664" in tx and "bsr" in tx or "jsr $22664.l" in tx: info.append("move")
            if "$2297a" in tx or "$228f4" in tx or "$2288c" in tx or "$22a4a" in tx or "$22ab0" in tx: info.append("land")
            m = re.match(r"cmpi\.([bw]) #\$([0-9a-f]+),(30|31|37|36)\(A6\)", tx)
            if m: info.append("timer+%s>=%x" % (m.group(3), int(m.group(2), 16)))
            m = re.match(r"move\.b #\$([0-9a-f]+),5\(A6\)", tx)
            if m: info.append("hp=%d" % int(m.group(1), 16))
        seen = []; 
        for i in info:
            if i not in seen: seen.append(i)
        out.append((ents[v], v, seen))
    return out
if __name__ == "__main__":
    for t in map(int, sys.argv[1:]):
        print("== type %d  handler $%x" % (t, states.H[t]))
        for ids, v, info in fp(t):
            print("  state %-14s $%06x  %s" % (",".join("%x" % i for i in ids), v, " ".join(info)))
