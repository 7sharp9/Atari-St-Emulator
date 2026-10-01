"""route_room27_to_room22_natural.py <start.snap> <OUTDIR>: Cadaver 88th pass, E1.  The join D1 -> D2 with no injection.
Start: room 27 just landed from room 21's hole with gems 164 and 290 carried naturally (d1/snaps/gems_room27_landed.snap, health 30, rucksack [290,164,182,53]).
Ends in room 22 with urn 143 and key 167 carried, var 4 = 0.  Natural joystick/keyboard input only (nothing injected).
Differences from d2/route_room27_to_room22.py: (1) `WQ` before the `gL14` leg: room 27's guard creature (event 14 creates object 127 once the hero has stood on the south strip) fires
a fireball south along x 14..16 (-10 where it meets the hero; D2's own run never met it by timing); the leg waits until the creature is gone; (2) the last two throws select 164 and 290 by id
(`SG<id>`: Return grid, RIGHT x slot, FIRE, icon $d) because the oldest items are not the first in the selection list.  Reload (snapshot, close, reopen) after every token."""
import sys, os
HD = os.path.dirname(os.path.abspath(__file__))
ARGS = [os.path.abspath(a) for a in sys.argv[1:3]]   # before `import play`: lib/drv.py does os.chdir(ROOT) on import
os.environ.setdefault('CAD_OUT', os.path.join(ARGS[1], '_scratch'))   # the lib's own output goes under the output dir
sys.path.insert(0, HD)
import play
ROUTE27 = ['D', 'gL55', 'D', 'L', 'P', 'I2', 'gU65', 'WQ', 'gL14', 'D', 'I2', 'D', 'w50000', 'I3', 'w100000', 'gR23', 'D', 'I2',
           'R', 'w50000', 'I3', 'w100000', 'gU66', 'R', 'I2', 'R', 'I2', 'R', 'U', 'R', 'w150000']
GEMS = ['w100000', 'R', 'R', 'w100000', 'R', 'P', 'I2', 'D', 'P', 'I2', 'gR42', 'U', 'P', 'I2', 'L', 'P', 'I2']
BACK = ['gU26', 'L', 'w100000', 'L', 'L', 'w100000', 'gD30', 'gL70']
THROW = ['SP', 'Id', 'F', 'w100000']
THROW_ID = lambda i: ['SG%d' % i, 'F', 'w100000']
TOKENS = ['w600000'] + ROUTE27 + GEMS + BACK + THROW * 4 + THROW_ID(290) + THROW_ID(164) + ['w300000', 'D', 'w100000', 'w300000']
if __name__ == '__main__':
    play.run(ARGS[0], 'route', TOKENS, outdir=ARGS[1])
