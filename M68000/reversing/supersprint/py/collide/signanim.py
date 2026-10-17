"""signanim.py - port of $b24e (the flashing 3-sign group animator, active when -1792(A4) != 0, i.e. (R+1) % 3 == 0) and its blit $1432e.
$b24e(track) runs in the race loop before $aa60 (call at $c796).  State: -1800 which of the 3 signs, -1798 animation frame (bit 7 = 'draw again next call'),
-1796 frame step (+1/-1), -1794 down-counter; sign position words at -1686 + 6*track + 2*sign, frame base bytes at -1638 + 3*track + sign.
$1432e(frame, off): 8x16 sprite of 6 words per row at [-1722] + 0x1740 + 96*frame: words 0-3 = four bitplane words (composited over both background pages [-78],[-86]
with mask ~(w0|w1|w2|w3)), word 4 -> collision plane 2 (stored whole), word 5 -> collision plane 1 ((plane1 & mask) | word 5), at (-94) + off/4."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import ssport as P
from ssport import s16

def blit_sign(m, frame, off):
    A4 = P.A4
    src = (m.rl(A4 - 1722) + 0x1740 + ((frame * 96) & 0xffff)) & 0xffffffff
    off &= 0xffff
    b1 = m.rl(A4 - 78) + s16(off); b2 = m.rl(A4 - 86) + s16(off)
    a3 = m.rl(A4 - 94) + 0x1f40 + (off >> 2); a6 = a3 + 8000
    for row in range(8):
        w = [m.rw(src + 12 * row + 2 * k) for k in range(6)]
        mask = (~(w[0] | w[1] | w[2] | w[3])) & 0xffff
        m.ww(a6, w[4])
        m.ww(a3, ((m.rw(a3) & mask) | w[5]))
        for bb in (b1, b2):
            for k in range(4):
                m.ww(bb + 2 * k, (m.rw(bb + 2 * k) & mask) | w[k])
        b1 += 160; b2 += 160; a3 += 40; a6 += 40

def signs(m, track):
    if m.g(-1798) > 0x7f:
        m.sg(-1798, m.g(-1798) & 0x7f)
        blit_sign(m, m.rb(P.A4 - 1638 + 3 * track + m.g(-1800)) + m.g(-1798), m.g(-1686 + 6 * track + 2 * m.g(-1800)))
    m.sg(-1794, m.g(-1794) - 1)
    if m.g(-1794) != 0:
        return
    m.sg(-1794, 8)
    m.sg(-1798, m.g(-1798) + m.g(-1796))
    if m.g(-1798) == 0:
        m.sg(-1796, 1); m.sg(-1794, 0x4b)
    elif m.g(-1798) == 4:
        m.sg(-1796, -1); m.sg(-1794, 0x1e)
        m.sg(-1800, (m.g(-1800) + 1) % 3); m.sg(-1798, 3)
    blit_sign(m, m.rb(P.A4 - 1638 + 3 * track + m.g(-1800)) + m.g(-1798), m.g(-1686 + 6 * track + 2 * m.g(-1800)))
    m.sg(-1798, m.g(-1798) + 0x80)
