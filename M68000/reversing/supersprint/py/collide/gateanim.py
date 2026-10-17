"""gateanim.py - port of $aa60 (per-frame gate animator, one gate per frame) and its blit $142b2, which ssport.py lacks.
$aa60 is called with the track number (8(A6)); it runs in the race loop at $c7a0 after the page flip's frame counter -8072 += 1 and before
the control phase ($eaea/$d4fa).  Gate k = ((R mod 6) >> 1); only k < -1808(A4) (gate count) is animated.
  per-gate words: dir -1814, phase -1820, timer -1826, route -1832; screen offset word -1278[track + k].
$142b2(frame = phase, off = -1278 word) copies a 48x16 gate picture: sprite sheet [-1722] + frame*0x240 + 0x180, 16 rows of 36 bytes:
  bytes 0-23 -> both background screens [-78]/[-86] + off (row stride 160); bytes 24-29 -> plane 2, 30-35 -> plane 1 (stride 40, at (-94)+off/4),
  and plane 0 gets ~word at bytes 2-3, 10-11, 18-19."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import ssport as P
from ssport import s16, u16

def blit(m, frame, off):
    A4 = P.A4
    src = m.rl(A4 - 1722) + ((frame * 0x240) & 0xffff) + 0x180
    src = (m.rl(A4 - 1722) + s16((frame * 0x240 + 0x180) & 0xffff)) & 0xffffffff
    off &= 0xffff
    d0 = s16(off)
    b1 = m.rl(A4 - 78) + d0
    b2 = m.rl(A4 - 86) + d0
    a3 = m.rl(A4 - 94) + (off >> 2)
    a5 = a3 + 8000
    a6 = a3 + 16000
    for row in range(16):
        s = src + row * 36
        blk = bytes(m.b[s:s + 24])
        m.b[b1:b1 + 24] = blk
        m.b[b2:b2 + 24] = blk
        m.b[a6:a6 + 6] = m.b[s + 24:s + 30]
        m.b[a5:a5 + 6] = m.b[s + 30:s + 36]
        for k, o in enumerate((2, 10, 18)):
            w = (~((m.b[s + o] << 8) | m.b[s + o + 1])) & 0xffff
            m.b[a3 + 2 * k] = w >> 8
            m.b[a3 + 2 * k + 1] = w & 0xff
        b1 += 160; b2 += 160; a3 += 40; a5 += 40; a6 += 40

def gate_anim(m, track):
    R = m.gu(-8072)
    k = ((R % 6) >> 1)
    if k >= m.g(-1808):
        return
    D, PH, T, RT = -1814, -1820, -1826, -1832
    if m.a(D, k) != 0:
        if R & 1:
            if (m.a(PH, k) & 3) == 0:
                m.sa(T, k, s16((0xe * (2 * (k + 1)) + 2 * k) & 0xffff))
                m.sa(D, k, 0)
        else:
            m.sa(PH, k, m.a(PH, k) + m.a(D, k))
        blit(m, m.a(PH, k), m.g(-1278 + 2 * (track + k)))
        return
    if m.a(T, k) == 5 and m.a(PH, k) == 4:
        m.sa(RT, k, 2)
    m.sa(T, k, m.a(T, k) - 1)
    if m.a(T, k) == 0:
        if m.a(PH, k) == 0:
            m.sa(RT, k, 3)
        m.sa(D, k, 1 - (m.a(PH, k) >> 1))

def next_boundary(m, track, controls=True, signs=False):
    """controls=False models the race-end freeze: the race loop ($c7c6) runs the control phase only while its finish countdown (local -6(A6), 170 at the
    finish detection) is > 165, i.e. for 4 more iterations; after that no car is controlled or moved until the countdown ends the loop."""
    P.frame(m)
    m.sg(-8072, m.gu(-8072) + 1)
    if signs and m.g(-1792) != 0:
        import signanim; signanim.signs(m, track)       # $b24e, called before $aa60 ($c796)
    gate_anim(m, track)
    if controls:
        P.control_phase(m)
