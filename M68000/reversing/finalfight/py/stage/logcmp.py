"""logcmp.py <new log> <old log> : compare two lua/stagebot.lua logs frame by frame on the fields every log version writes (stage/area, camera, script pointer,
player x, y, state, health, lives), ignoring later additions (tgt=, extra pools, S lines). Prints the frames compared and the first that differs."""
import sys, re
def rows(fn):
    r = {}
    for l in open(fn):
        m = re.match(r'(\d+) sa=(\S+) cam=(\S+) scr=(\S+) x=(\S+) y=(\S+) st=(\S+) hp=(\S+) lives=(\S+)', l)
        if m: r[int(m[1])] = m.groups()[1:]
    return r
a, b = rows(sys.argv[1]), rows(sys.argv[2])
common = sorted(set(a) & set(b)); bad = [f for f in common if a[f] != b[f]]
print('frames compared %d (%d to %d), differ %d' % (len(common), common[0] if common else -1, common[-1] if common else -1, len(bad)))
if bad: print('first difference at frame %d:' % bad[0], ' '.join(a[bad[0]]), '|', ' '.join(b[bad[0]]))
