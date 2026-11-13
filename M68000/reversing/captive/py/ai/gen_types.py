"""Group-list types from gen.py output: gen_types.py <gen.json>. Walks fedtab ($1bd3e..) from the group list $1c782
(fed 4532(A6)) and prints each case's member-type census and the groups holding types given in argv[2:] (hex)."""
import json, sys, collections
FED0, LIST = 0x1bd3e, 0x1c782
for c in json.load(open(sys.argv[1])):
    b = bytes.fromhex(c['fedtab']); a = LIST - FED0; cnt = collections.Counter(); hits = []
    while True:
        sz = int.from_bytes(b[a + 2:a + 4], 'big', signed=True)
        if sz < 0: break
        types = [b[a + 8 + 8 * i] for i in range((sz - 8) // 8)]
        cnt.update(types)
        if any(f'{t:x}' in sys.argv[2:] for t in types):
            hits.append((b[a], b[a + 1], f'{b[a + 4]:02x}{b[a + 5]:02x}', b[a + 7], [b[a + 8 + 8 * i:a + 16 + 8 * i].hex() for i in range(len(types))]))
        a += sz
    print(c['args'], 'types', {f'{k:x}': v for k, v in sorted(cnt.items())}, 'selected', hits)
