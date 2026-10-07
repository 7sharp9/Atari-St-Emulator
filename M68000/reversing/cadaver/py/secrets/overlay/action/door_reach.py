"""door_reach.py [--open HEX ...] [--keys ID ...]: rooms of level 0 reachable from CAVERN (room 0) under a set of opened doors and carried keys.

Edges are the doors of scratchpad/cadaver/secrets_out/door_walk_level0.txt (`py/door_walk.py gameplay_empire.snap`), each joining the two rooms printed on its line.
A door whose id word is 0 is open; `$ffff` (id -1) is closed until its number is in --open (mechanics.md section 11 lists each door's opener); a positive id word is
an item id, open when that id is in --keys (the rucksack carries it).  Teleport scripts (verb 37) are not edges.

    door_reach.py                                  CAVERN, TUNNEL
    door_reach.py --open 33 --keys 73              the lever 144 and the iron key: 11 rooms, with room 8
    door_reach.py --open 33 22 --keys 73           + door $22 (lever 472): 40 more rooms

The census of which room holds which item: `reversing/cadaver/py/room_object_census.py scratchpad/cadaver/gameplay_empire.snap`."""
import re, collections, os, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
doors = {}
for l in open(ROOT + '/scratchpad/cadaver/secrets_out/door_walk_level0.txt'):
    m = re.match(r'door 0x([0-9a-f]+) candidate=\((\d+),(\d+)\) \[id=(-?\d+)[^\]]*\] desc@0x[0-9a-f]+: (.*)', l)
    if not m: continue
    rooms = set(int(x) for x in re.findall(r'(\d+)->', m.group(5))) | set(int(x) for x in re.findall(r'->(\d+)', m.group(5)))
    doors[int(m.group(1), 16)] = (int(m.group(4)), tuple(sorted(rooms)))


def reach(open_ids, keys):
    adj = collections.defaultdict(set)
    for d, (idw, pair) in doors.items():
        if len(pair) != 2: continue
        if idw == 0 or (idw == -1 and d in open_ids) or (idw > 0 and idw in keys):
            a, b = pair; adj[a].add(b); adj[b].add(a)
    seen = {0}; q = [0]
    while q:
        x = q.pop()
        for y in adj[x]:
            if y not in seen: seen.add(y); q.append(y)
    return seen


if __name__ == '__main__':
    args = sys.argv[1:]; op, keys, cur = set(), set(), None
    for a in args:
        if a == '--open': cur = 'o'
        elif a == '--keys': cur = 'k'
        elif cur == 'o': op.add(int(a, 16))
        elif cur == 'k': keys.add(int(a))
    r = reach(op, keys)
    allrooms = set(x for _, p in doors.values() for x in p)
    print('reachable (%d):' % len(r), sorted(r))
    print('not reachable (%d):' % len(allrooms - r), sorted(allrooms - r))
    print('closed doors with their rooms:', {hex(d): (w, p) for d, (w, p) in sorted(doors.items()) if w != 0 and not (d in op or w in keys)})
