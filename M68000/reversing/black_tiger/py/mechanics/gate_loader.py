"""Gate: levelmap.scan() vs callcap $cd58 for each level file, on the play_start snapshot with the
original file bytes poked at $201c8 (labelled poke: the live map had its markers stripped already).
Usage: gate_loader.py [levels...]   (default 0..7)"""
import os, re, struct, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b, levelmap as lm

snap = os.path.join(b.WORK, "play_start.snap")
ram = bytearray(b.ram_from_snap(snap))
levels = [int(x) for x in sys.argv[1:]] or list(range(8))
tot_ok = 0
for n in levels:
    d = open(os.path.join(b.FILES, str(n)), "rb").read()
    pre = bytearray(ram)
    pre[0x201c8:0x201c8 + len(d)] = d
    w, h, words, ln = lm.load(n)
    post = bytearray(pre)
    items, actors, anchors, a2 = lm.scan(w, h, words, post)
    pred = {a: post[a] for a in range(len(pre)) if pre[a] != post[a]}
    lines = ["w %x %02x%02x%02x%02x" % (0x201c8 + i, *(d + b"\0\0\0")[i:i + 4]) for i in range(0, len(d), 4)]
    # keep pre-state bytes beyond the file end when padding a partial longword
    if len(d) % 4:
        tail = len(d) - len(d) % 4
        t = bytearray(pre[0x201c8 + tail:0x201c8 + tail + 4]); t[:len(d) - tail] = d[tail:]
        lines[-1] = "w %x %s" % (0x201c8 + tail, t.hex())
    lines.append("callcap cd58 9000000")
    out = b.repl(snap, lines)
    got = {int(m.group(1), 16): int(m.group(2), 16) for m in re.finditer(r"^mem \$([0-9a-f]+) \$[0-9a-f]+->\$([0-9a-f]+)", out, re.M) if not (0x1ee00 <= int(m.group(1), 16) < 0x1ee50)}
    # callcap reports changes relative to the poked state
    ok = pred == got
    missing = {a: v for a, v in pred.items() if got.get(a) != v}
    extra = {a: v for a, v in got.items() if pred.get(a) != v}
    print("level file %d: %dx%d  markers: items=%d actors=%d anchors=%s  pred bytes=%d callcap bytes=%d  match=%s  (pred-not-got %d, got-not-pred %d)"
          % (n, w, h, len(items), len(actors), sorted(anchors), len(pred), len(got), ok, len(missing), len(extra)))
    if not ok:
        print("  missing", list(missing.items())[:6], "extra", list(extra.items())[:6])
    tot_ok += ok
print("levels matching: %d/%d" % (tot_ok, len(levels)))
