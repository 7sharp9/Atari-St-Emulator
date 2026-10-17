"""Leader-blink rule of $13bbe: which panel regions of a snapshot are blank (restored to the pristine crowd by $13c50), observed vs predicted.
usage: blink.py snap..."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
import proof_playfield as PF


def observed_blank(R, track=0):
    PF.r = R; bg = bytes(PF.build(track)); st = bytes(R.b[R.g(-86):R.g(-86) + 32000])
    out = []
    for k in range(3):
        same = all(st[0x460 + k * 0x38 + r * 160: 0x460 + k * 0x38 + r * 160 + 48] == bg[0x460 + k * 0x38 + r * 160: 0x460 + k * 0x38 + r * 160 + 48] for r in range(11))
        out.append(same)
    return out


def predict(R, hyp):
    f = R.gw(-8072); cyc = R.gsw(-4814); lead = R.gsw(-4812)
    cur = (f - hyp) % 6                                   # ph of the most recent $13bbe call
    res = []
    for k in range(3):
        if k != lead: res.append(False); continue
        if cur >= 2 * k: v = cyc                          # panel k already refreshed in this 6-frame cycle (cyc counts from ph == 0)
        else: v = (cyc - 1) % 4                           # still shows the previous cycle's refresh
        res.append(v < 2)
    return res


if __name__ == '__main__':
    for s in sys.argv[1:]:
        R = Ram(s)
        ob = observed_blank(R)
        print('%-28s f=%d cyc=%d lead=%d observed blank %s  pred(H0) %s  pred(H1) %s' % (os.path.basename(s), R.gw(-8072), R.gsw(-4814), R.gsw(-4812), ob, predict(R, 0), predict(R, 1)))
