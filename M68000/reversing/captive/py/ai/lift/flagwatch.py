"""Who writes a byte during some inputs: flagwatch.py <snap> <hexaddr> <len> <input ...> (drive.py input syntax).
Prints every CPU write to the range with its PC, value and step."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_input as P
from probe_input import srv, w16  # noqa
s = srv(sys.argv[1]); lo = int(sys.argv[2], 16); hi = lo + int(sys.argv[3]) - 1
wid = s('watch_add', lo=f'${lo:x}', hi=f'${hi:x}', kind='w', max_events=10000)['id']
for inp in sys.argv[4:]:
    tot = dict.fromkeys(P.ADDRS, 0)
    P.run(s, int(inp[1:]), tot) if inp[0] == 'w' else P.drive(s, inp, tot)
    ev = s('watch_events', id=wid); ev = ev[0] if isinstance(ev, list) else ev
    print(inp, 'party', w16(s, 26), w16(s, 28), [(e['pc'], e['addr'], e['value'], e.get('step')) for e in ev['events']])
s.close()
