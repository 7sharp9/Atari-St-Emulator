"""Drive the enemy carrier state machine from a snapshot with optional pokes; log events by breakpoint.
usage: drive.py <snap> <max_steps> [poke addr:width:value ...] [--save out.snap] [--until-state N]
(stops at the first strategy-tick entry $1ac8c where $11be == N)
Run from M68000/. Prints each event (step offset, PC label, $11ba..$11d0 words, enemy/player positions)."""
import sys, struct
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent)); from ccpaths import ROOT
sys.path.insert(0, str(ROOT / 'tools')); from stclient import StServer
EV = {0x1ac8c: None, 0x1af20: 'ENGAGE(enter 10)', 0x1b04c: 'MISSILE launch', 0x1b108: 'AIRCRAFT launch',
      0x1b15e: 'RETREAT(enter 11)', 0x1b1ba: 'RETREAT done->1', 0x1ad3c: 'travel(enter 5)'}
args = sys.argv[1:]; snap = args[0]; budget = int(args[1]); save = None; pokes = []; until = None
i = 2
while i < len(args):
    if args[i] == '--save': save = args[i+1]; i += 2
    elif args[i] == '--until-state': until = int(args[i+1]); i += 2
    else: pokes.append(args[i]); i += 1
s = StServer(str(ROOT))
s('load', snapshot=snap)
for p in pokes:
    a, w, v = p.split(':'); s('poke', addr=int(a, 16), width=int(w), value=int(v, 16))
s('bp_set', addrs=[f'${a:x}' for a in EV])
def st():
    b = s.read(0x11ba, 0x18); return struct.unpack('>12h', b)
def pos(a):
    return struct.unpack('>i', s.read(a+10, 4))[0], struct.unpack('>i', s.read(a+18, 4))[0]
base = int(s('regs')['step']); used = 0; last = None; cnt = {}
print('names: ba=target bc=cur be=state c0=count c2=hull c4=air c6=aircd c8=airout ca cc=msl ce=mslcd d0=spd')
while used < budget:
    r = s('run', max_steps=budget - used)
    pc = int(r.get('pc', s('regs')['pc']).lstrip('$'), 16) if isinstance(r.get('pc'), str) else s.reg('pc')
    used = int(s('regs')['step']) - base
    if r['reason'] != 'breakpoint': break
    pc &= 0xffffff
    w = st()
    if pc == 0x1ac8c:
        cnt['frames'] = cnt.get('frames', 0) + 1
        if w != last:
            ex, ez = pos(0x5f49a); px, pz = pos(0x5e95a)
            act = s.read(0x5f49b, 1)[0] & 1
            d = max(abs(ex-px), abs(ez-pz))
            print(f'{used:>10} state ' + ' '.join(f'{x:6d}' for x in w) + f'  eAct={act} cheb(e,pc)={d}')
            last = w
        if until is not None and w[2] == until: break
    else:
        cnt[EV[pc]] = cnt.get(EV[pc], 0) + 1
        print(f'{used:>10} {EV[pc]}  ' + ' '.join(f'{x:6d}' for x in w))
print('steps', used, 'counts', cnt)
ex, ez = pos(0x5f49a); px, pz = pos(0x5e95a)
print('final enemy', ex, ez, 'heading', struct.unpack('>H', s.read(0x5f4a0, 2))[0], 'player', px, pz, 'cheb', max(abs(ex-px), abs(ez-pz)), 'state', st())
if save: s('save', path=save)
s.close()
