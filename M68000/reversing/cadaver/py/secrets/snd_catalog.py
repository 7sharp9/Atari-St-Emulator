"""Static catalogue of the sound data: request table, set table, action (script) pointer table, reachability.
Start snapshot gameplay_empire.snap.  Prints a summary and writes snd_scripts.txt (every script disassembled)."""
import struct, sys, os, collections
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
OUT = os.path.join(os.path.abspath(os.path.join(here, '..', '..', '..', '..')), 'scratchpad/cadaver/secrets_out'); os.makedirs(OUT, exist_ok=True)
from ram import ram
from cad_sound import Sound, disasm_script, PTR_TAB, REQ_TAB, SET_TAB, PRESET_TAB
s = Sound(ram())
ptrs = [s.rl(PTR_TAB + 4 * i) for i in range(256)]
uniq = sorted(set(p for p in ptrs if p))
print('action pointer table: 256 slots at $%06x, null=%d, distinct non-null scripts=%d, range $%06x-$%06x' % (PTR_TAB, sum(1 for p in ptrs if not p), len(uniq), uniq[0], uniq[-1]))
# which actions have a real script (start of the next distinct pointer bounds its length)
dup = collections.defaultdict(list)
for i, p in enumerate(ptrs): dup[p].append(i)
print('slots sharing a pointer:', {hex(p): v for p, v in dup.items() if len(v) > 1 and p})
# referenced actions
ref_req = set(); ref_set = collections.defaultdict(set)
for k in range(62):
    e = REQ_TAB + 5 * k; n = s.rb(e + 1)
    for j in range(n): ref_req.add(s.rb(e + 2 + j))
for k in range(62):
    for j in range(3):
        a = s.rb(SET_TAB + 3 * k + j)
        if a: ref_set[a].add(k)
# $8c stage references inside scripts
ref_8c = set()
for p in uniq:
    for a, t in disasm_script(s, p):
        if t.startswith('STAGE'): ref_8c.add(int(t.split()[1], 16))
used = ref_req | set(ref_set) | ref_8c
print('actions referenced by request table: %d; by set table only: %s; via $8c STAGE: %s' % (len(ref_req), sorted(set(ref_set) - ref_req), sorted(ref_8c)))
defined = [i for i in range(256) if ptrs[i] and ptrs[i] != 0x16fe4]
print('defined actions (non-null, not the $016fe4 filler): %d ; defined but never referenced: %s' % (len(defined), [hex(i) for i in defined if i not in used]))
filler = [i for i in range(256) if ptrs[i] == 0x16fe4]
print('slots pointing at $016fe4 (end-of-data filler): %d, first %s' % (len(filler), filler[:3]))
with open(os.path.join(OUT, 'snd_scripts.txt'), 'w') as f:
    for i in range(256):
        if ptrs[i] and ptrs[i] != 0x16fe4:
            f.write('action $%02x @ $%06x (requested by sounds %s)\n' % (i, ptrs[i], [k for k in range(62) if i in [s.rb(REQ_TAB + 5 * k + 2 + j) for j in range(s.rb(REQ_TAB + 5 * k + 1))]]))
            for a, t in disasm_script(s, ptrs[i]): f.write('  $%06x %s\n' % (a, t))
# sound request classes
cls = collections.Counter()
for k in range(62):
    e = REQ_TAB + 5 * k; pr = s.rb(e); kind = s.rb(e + 1)
    c = ('queued(bit7)' if pr & 0x80 else ('sfx-voice-alloc' if kind in (1, 2) else 'priority-3voice'))
    cls[c] += 1
print('request classes:', dict(cls))
print('prio0 (always play) entries:', [k for k in range(62) if s.rb(REQ_TAB + 5 * k) == 0], '; prio 1 (never plays via $15a3e):', [k for k in range(62) if s.rb(REQ_TAB + 5 * k) & 0x7f == 1 and not s.rb(REQ_TAB + 5 * k) & 0x80])
# envelope presets
n_env = (0x1729d - PRESET_TAB) // 12 if False else None
