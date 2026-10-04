"""Gate: shop purchase $00fa9c(item) vs a Python model, over random inventories (callcap, stack arg poked at $1ee50,
$1eeda forced high so the wait loop $fc1c exits).  Compares the inventory fields $1f002..$1f00a, $17820 only.
Model (from the body):  price=P[i] (words at $17a8e); if price > money: refuse (text $17a76).  else
  i 0..3: weapon level := i+1 if i+1 > level else free;  i 4: keys+=1;  i 5..8: armour := (i-4)*2 if larger else free;
  i 9: if poisoned clear poison else potions+=1;  money -= price unless free."""
import os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
P = [b.rw(ram, 0x17a8e + 2 * i) for i in range(10)]
low = ram[0x1ee52:0x1ee54].hex()
def model(i, st):
    st = dict(st); price = P[i]
    if price > st["money"]: return st            # refused
    cost = price
    if i < 4:
        if i + 1 > st["weapon"]: st["weapon"] = i + 1
        else: cost = 0
    elif i == 4: st["keys"] += 1
    elif i < 9:
        if (i - 4) * 2 > st["armour"]: st["armour"] = (i - 4) * 2
        else: cost = 0
    else:
        if st["poison"]: st["poison"] = 0
        else: st["potions"] += 1
    st["money"] -= cost
    return st
random.seed(5)
cases = []; lines = ["w 1eeda 7fff7fff"]
for k in range(200):
    i = random.randrange(10)
    st = dict(money=random.choice((0, 14, 15, 79, 80, 100, 150, 299, 300, 1000, 5000, 9600, 20000)), keys=random.randrange(4), armour=random.choice((0, 2, 4, 6, 8)),
              potions=random.randrange(3), weapon=random.randrange(5), poison=random.randrange(2))
    cases.append((i, st))
    lines += ["w 1f002 %04x%04x" % (st["money"], st["keys"]), "w 1f006 %04x%04x" % (st["armour"], st["potions"]),
              "w 1f00a %04x%s" % (st["weapon"], ram[0x1f00c:0x1f00e].hex()), "w 17820 %04x%s" % (st["poison"], ram[0x17822:0x17824].hex()),
              "w 1ee50 %04x%s" % (i, low), "callcap fa9c 4000000"]
out = b.repl(snap, lines)
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
assert len(blocks) == len(cases), (len(blocks), len(cases))
ok = 0; ret = 0
for (i, st), blk in zip(cases, blocks):
    ret += "returned" in blk.splitlines()[0]
    mem = bytearray(ram)
    mem[0x1f002:0x1f004] = st["money"].to_bytes(2, "big"); mem[0x1f004:0x1f006] = st["keys"].to_bytes(2, "big")
    mem[0x1f006:0x1f008] = st["armour"].to_bytes(2, "big"); mem[0x1f008:0x1f00a] = st["potions"].to_bytes(2, "big")
    mem[0x1f00a:0x1f00c] = st["weapon"].to_bytes(2, "big"); mem[0x17820:0x17822] = st["poison"].to_bytes(2, "big")
    for a, v in re.findall(r"^mem \$([0-9a-f]+) \$[0-9a-f]+->\$([0-9a-f]+)", blk, re.M):
        mem[int(a, 16)] = int(v, 16)
    got = dict(money=b.rw(mem, 0x1f002), keys=b.rw(mem, 0x1f004), armour=b.rw(mem, 0x1f006), potions=b.rw(mem, 0x1f008), weapon=b.rw(mem, 0x1f00a), poison=b.rw(mem, 0x17820))
    exp = model(i, st)
    if got == exp: ok += 1
    else: print("MISMATCH item", i, st, "model", exp, "got", got)
print("shop model vs callcap: %d/%d match (callcap returned %d/%d); prices %s" % (ok, len(cases), ret, len(cases), P))
