"""negatives.py: controls for action_survey.py.  Each prints the entry-point hits and the state so 'nothing happened' is backed by a signal that fires
only when the input was read (the fire branch $006f28 / the key handler $006cce / the panel entry $009c82).
  1  fire with no object in front (start): $006f28 hit, panel entry $009c82 not hit
  2  Return and Space with an EMPTY rucksack: $006cce and $009682 hit, $009724 (rucksack loop) not hit
  3  Down key near an object: $006cb0 and $006f28 hit, $009c82 not hit (Down is the 'crouch' flag 2474 bit 0, not a panel key)
  4  Space inside the object panel cancels (returns icon 6, no dispatch except $a134)
  5  selected item + fire with nothing in front: $006f48 -> $00a19e -> $00a1ea -> $00f44a (throw / drop from the hero), item leaves the type-8 list
"""
from drv import *
SITES = [0x6f28, 0x6cce, 0x6cb0, 0x9682, 0x9724, 0x9c82, 0xa08c, 0xa134, 0xa19e, 0xa1ea, 0xf44a, 0x6f48, 0x6f62, 0xa748, 0xc3d4, 0xa70e, 0x6e70, 0x9440, 0x737a]

def run(label, snap, act):
    r = Repl(snap); t = Tally(r); before = state(r)
    act(r, t)
    print(f'{label}\n   before {before}\n   after  {state(r)}  2463={r.a5(2463,1).hex()}  type8 count {r.a5(2438,1)[0]}\n   hits {t.show()}', flush=True)
    r.close()

def fire_hold(r, t, n=60000):
    t.joy(FIRE); t.run(n, SITES); t.joy(0); t.run(120000, SITES)
# tally.run default sites are KEYSITES; wrap so the negatives use SITES
_run = Tally.run
Tally.run = lambda self, n, sites=SITES: _run(self, n, sites)

run('1  fire, no object in front (start)', START, lambda r, t: fire_hold(r, t))
run('2a Return, empty rucksack', START, lambda r, t: tap(r, t, 0x1c))
run('2b Space, empty rucksack', START, lambda r, t: tap(r, t, 0x39))
run('3  Down key next to the coin', ensure('coin'), lambda r, t: tap(r, t, 0x50))
def cancel(r, t):
    t.joy(FIRE); t.run(40000); t.joy(0); t.run(20000); tap(r, t, 0x39)
run('4  Space cancels the object panel (coin)', ensure('coin'), cancel)
def sel_fire(r, t):
    ruck_panel(r, t, 'space'); pick_icon_id(r, t, 13)
    print('   selected:', r.a5(1262, 2).hex(), '2463', r.a5(2463, 1).hex())
    t.tot = {}
    fire_hold(r, t)
run('5  selected pickaxe, fire (nothing in front)', ensure('held'), sel_fire)
