"""observe.py <snap|ram> [--compact]: one decision's observation of a PowerMonger RAM image as JSON (commander README step 3).

Every field is read at an offset taken from a proven doc section (cited per field, paths relative to
reversing/powermonger/) or an existing script; a field whose meaning is not proven is emitted raw under a name
starting `raw_` with what is known in the comment. Doc keys used below:
  S-cmd   strategy.md "`$58016` - command buffer" (+ the `$6ac6` disassembly: bytes 2/3 are read as separate x, y bytes
          at $6c36/$6c3a, NOT a packed cell as that table says)
  S-grp   strategy.md "`$51538` - group-order table" and "Data structures (C)" pm_side_groups
  S-ord   strategy.md "What each order does" (group-offset table: -12 lead, -24 men, -36 first man, -48 owner, 36 food, 84+12i)
  S-exec  strategy.md "`$6a3a` / `$6ac6` / `$6b38`": $58042[2*side] = the group the executor acts for; 48(group) the sender
  S-tot   strategy.md "`$d322` + `$3e06` -> `$57fba` -> `$d23a` -> `$57fce`"
  S-text  strategy.md "The game's own text" (state, posture, aggression, lord-kind names)
  E1      economy.md section 1 (pm_leader) ; E3 economy.md section 3 (pm_settlement) + "Buildings and town layouts"
  AI-obj  ai.md object record table (x/y words 8/10, owner byte 5, mode 31, health 45)
"""
import json, struct, sys
from pathlib import Path

GROUPS, GSTRIDE = 0x51538, 0x13c      # S-grp
LORDS, LSTRIDE, NLORDS = 0x4e514, 32, 160   # E1 / S-grp pm_leader: 160 slots, side byte 0 (0 = empty slot)
SETTL, SSTRIDE, NSETTL = 0x4f916, 18, 400   # E3: stride 18, table size $1c20 = 400 records
OBJ, OSTRIDE = 0x51b66, 50            # AI-obj
SLOTS = 0x58016                       # S-cmd
ACTING = 0x58042                      # S-exec
CLOCK = 0x2df72                       # sides.py "tick"; the clock $3720 stamps into camp_since (S-grp 256())

STATE = {0: '', 1: 'Waiting', 2: 'Get Food', 3: 'Get Men', 4: 'Meeting', 5: 'Going To', 6: 'In Camp', 7: 'Go Home',
         8: 'Attack', 9: 'Invent', 10: 'Equip', 11: 'Pickup', 12: 'Supply', 13: 'Fighting', 14: 'Alliance',
         15: 'Trading', 16: 'Spying'}                                                    # S-text, group state
POSTURE = {2: 'Aggressive', 3: 'Neutral', 4: 'Passive'}                                  # S-text / S-grp 136()
AGGR = ['PowerMonger', 'Bellicose', 'Domineering', 'Aggressive', 'Firm', 'Quite Firm', 'Weak', 'Wimp']  # S-text 148()
LORD_KIND = {1: 'Village', 2: 'Hamlet', 3: 'Town', 4: 'City', 5: 'Capital', 6: 'Base'}   # S-text, byte 1 of $4e514
BUILDING = ['TownHall', 'Tavern', 'FishHut', 'FarmHouse', 'Ranch', 'Barn', 'Church', 'WorkShop', 'Turret', 'Square',
            'Ruin', 'Tower', 'Mine']                                                     # E3 housenam $a15a
GOODS = ['pike', 'sword', 'bow', 'plough', 'boat', 'pot', 'catapult', 'cannon']           # E1 +24..31 / S-ord 84+12i
OPP_CLASS = {0: 'unset', 2: 'lord', 4: 'group', 6: 'lone man', 8: 'animal', 10: 'animal', 12: 'category-4 record'}  # S-grp 280()
LOYALTY_WORDS = ['sycophantic', 'faithful', 'loyal', 'trusting', 'discontent', 'untrusting', 'tratorious', 'rebellious']  # S-text house panel


def load(path):
    data = Path(path).read_bytes()
    if data[:4] != b'A68S':
        return data
    ver = data[4]; off = 5 + (19 if ver >= 5 else 18) * 4 + 2       # tools/gfxview.py load_ram
    n = struct.unpack_from('<i', data, off)[0]
    return data[off + 4: off + 4 + n]


def cell(c):  # packed {x: bits 0-5, y: bits 6-12} (E1 +4, E3 +12)
    return [c & 63, (c >> 6) & 127]


def observe(R):
    B = lambda a: R[a]
    H = lambda a: struct.unpack_from('>H', R, a)[0]
    h = lambda a: struct.unpack_from('>h', R, a)[0]
    L = lambda a: struct.unpack_from('>I', R, a)[0]
    out = dict(clock=L(CLOCK),
               local_side=H(0x57ffe),            # sides.py; S-tot "the local side $57ffe"
               ratio=H(0x57fce),                 # S-tot: 4 at land end = win
               selected_group=H(0x57fd2),        # S-grp: the local selected group offset (_the_cap)
               sides={})
    # ---- lords (E1 pm_leader) ----
    lords = {s: [] for s in range(1, 5)}
    other_lords = []
    for i in range(NLORDS):
        a = LORDS + LSTRIDE * i
        if B(a) == 0:                            # E1: side 0 = empty slot
            continue
        ps = h(a + 14)
        rec = dict(idx=i, side=B(a),
                   kind=B(a + 1), kind_name=LORD_KIND.get(B(a + 1)),   # S-text lord kind (byte 1)
                   cell=cell(H(a + 4)),          # E1 +4
                   food=H(a + 6),                # E1 +6 food store (house panel "Food:")
                   men_home=H(a + 8),            # E1 +8 troops_field (house panel "Men: N")
                   loyalty=ps,                   # E1 +14 loyalty_pressure, >=600 revolt
                   loyalty_word=LOYALTY_WORDS[0 if ps < 0 else min(ps // 75, 7)],  # S-text house panel mapping
                   work_order=H(a + 12),         # E1 +12 gather_kind ($5cde)
                   build_site=H(a + 18),         # E1 +18 ($4f916 offset, 0 none)
                   goods=dict(zip(GOODS, R[a + 24:a + 32])),   # E1 +24..31 (house panel "Stock")
                   chain_head=H(a + 2))          # E1 +2 first settlement
        (lords[B(a)] if B(a) in lords else other_lords).append(rec)
    # ---- settlements / buildings (E3) ----
    setts = {s: [] for s in range(1, 5)}
    other_setts = []
    for i in range(NSETTL):
        a = SETTL + SSTRIDE * i
        if B(a + 5) == 0:                        # E3: owner 0 = free slot
            continue
        n, o = 0, H(a + 10)                      # E3 +10 unit_head, chain via word 24 of each man (E3 / economy 5a)
        while o and n < 512:
            n += 1; o = H(OBJ + o + 24)
        lo = H(a + 14)
        rec = dict(idx=i, addr=a, owner=B(a + 5),                 # E3 +5
                   kind=B(a + 7), kind_name=BUILDING[B(a + 7)] if B(a + 7) < 13 else None,  # E3 +7
                   category=B(a + 6),                             # E3 +6 render byte6 ($1e site being built)
                   cell=cell(H(a + 12)),                          # E3 +12
                   lord=lo // 32 if lo % 32 == 0 else None, raw_leader_off=lo,   # E3 +14
                   residents=n,                                   # length of the +10 unit chain
                   build_progress=H(a + 16))                      # E3 +16 (a Ruin's counter)
        (setts[B(a + 5)] if B(a + 5) in setts else other_setts).append(rec)
    # ---- groups, command slot, acting group, totals ----
    for s in range(1, 5):
        base = GROUPS + GSTRIDE * s
        groups = []
        for k in range(6):
            f = lambda n: h(base + n + 2 * k)
            g = dict(k=k, offset=s * GSTRIDE + 0x4c + 2 * k,       # S-grp: group offset D2
                     owner=f(28), alive=f(28) > 0,                  # S-grp 28(): <= 0 no group
                     men=f(52),                                     # S-grp 52() captain panel "Troops"
                     state=f(76), state_name=STATE.get(f(76)),      # S-grp 76(), S-text
                     food=f(112),                                   # S-grp 112() captain panel "Food"
                     posture=f(136), posture_name=POSTURE.get(f(136)),   # S-grp 136()
                     aggression=f(148),                             # S-grp 148() (display only, README)
                     opp_class=f(280), opp_class_name=OPP_CLASS.get(f(280)),  # S-grp 280() (may hold an offset: $5778 bug)
                     opp_off=f(292),                                # S-grp 292()
                     target=f(100),                                 # S-grp 100() target link
                     prev_state=f(268), camp_since=f(256),          # S-grp 268(), 256()
                     eat_timer=f(88),                               # S-grp 88()
                     sender=f(124),                                 # S-exec: 48(group) the sender word (base+$4c+48)
                     raw_w4=f(4),                                   # S-grp 4(): "slot-index / link written back by $6822"; side_dump.py calls it "pending"
                     first_man=f(40),                               # S-grp 40() roster head
                     carrying=dict(zip(GOODS, [h(base + 160 + 12 * j + 2 * k) for j in range(8)])),  # S-ord 84+12i
                     lead=H(base + 64 + 2 * k))                     # S-grp 64() lead object offset
            if g['lead']:
                o = OBJ + g['lead']                                  # AI-obj
                x, y = h(o + 8), h(o + 10)
                g['lead_obj'] = dict(owner=struct.unpack_from('b', R, o + 5)[0], x=x, y=y, cell=[x >> 8, y >> 8],
                                     mode=B(o + 31), health=B(o + 45))
            groups.append(g)
        sl = SLOTS + 6 * s                                          # S-cmd
        slot = dict(side=B(sl), type=B(sl + 1), x=B(sl + 2), y=B(sl + 3), state=B(sl + 4), pad=B(sl + 5),
                    raw=R[sl:sl + 6].hex())
        act = H(ACTING + 2 * s)                                     # S-exec
        q, r = divmod(act - 0x4c, GSTRIDE) if act else (None, None)
        acting = dict(word=act, side=q, k=r // 2 if act and r % 2 == 0 and 0 <= r < 12 else None)
        live = [g for g in groups if g['alive']]
        tot = dict(lords=len(lords[s]), settlements=len(setts[s]),
                   men_home=sum(l['men_home'] for l in lords[s]), lord_food=sum(l['food'] for l in lords[s]),
                   # $d322 adds 6(leader) only for a lord with 8(leader) != 0 ($d366 move.w 8(A0),D0 / beq $d48a)
                   lord_food_manned=sum(l['food'] for l in lords[s] if l['men_home']),
                   group_men=sum(g['men'] for g in live), group_food=sum(g['food'] for g in live),
                   groups_alive=len(live),
                   raw_57fba=[H(0x57fba + 4 * s), H(0x57fba + 4 * s + 2)])   # S-tot: word0 men, word2 lords' food
        out['sides'][s] = dict(lords=lords[s], settlements=setts[s], groups=groups, slot=slot, acting=acting, totals=tot)
    out['other_lords'] = other_lords
    out['other_settlements'] = other_setts
    return out


if __name__ == '__main__':
    o = observe(load(sys.argv[1]))
    print(json.dumps(o, separators=(',', ':')) if '--compact' in sys.argv else json.dumps(o, indent=1))
