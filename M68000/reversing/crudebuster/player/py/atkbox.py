"""atkbox.py: the player attack-box table $67000[+24 pose][+25 variant][+21 frame][+7 facing] -> flag word, R, L, B, T (signed words, relative to x,y).
   usage: atkbox.py pose var frames   e.g. atkbox.py 0 1 7"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
def rec(pose, var, fr, face):
    a = l(0x67000 + 4 * pose); a = l(a + 4 * var); a = l(a + 4 * fr); a = l(a + 4 * face)
    return (w(a),) + tuple(sw(a + 2 + 2 * k) for k in range(4))
if __name__ == "__main__":
    pose, var, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    for fr in range(n):
        print("pose %d var %d frame %d: right-facing %s  left-facing %s" % (pose, var, fr, rec(pose, var, fr, 0), rec(pose, var, fr, 1)))
