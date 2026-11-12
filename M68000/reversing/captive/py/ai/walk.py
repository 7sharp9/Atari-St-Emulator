"""Drive the party with keypad keys and log plane-2 writers and party position.
walk.py <snap> <out.snap> <keys hex,...>   ($68 fwd, $6a/$6c strafe, $67/$69 turn, $6e back)"""
import os, sys, collections; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
s = srv(sys.argv[1])
wid = s('watch_add', lo='$1e208', hi='$1ea07', kind='w', max_events=200000)['id']
for k in sys.argv[3].split(','):
    k = int(k, 16)
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=300000)
    print(hex(k), 'pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30))
ev = s('watch_events', id=wid); ev = ev[0] if isinstance(ev, list) else ev
c = collections.Counter((e['pc'], e['value']) for e in ev['events'] if e['pc'] not in ('$0086a0', '$0086ae', '$0086bc', '$0086ca'))
print('non-visit writers', c.most_common(20))
s('save', path=os.path.abspath(sys.argv[2]))
s.close()
