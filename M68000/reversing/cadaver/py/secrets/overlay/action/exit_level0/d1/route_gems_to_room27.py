"""route_gems_to_room27.py <start.snap> <out dir>: natural joystick/panel input only (nothing poked or injected).
Start: `s87/b7/snaps/C1/ck_71_L_stall_2a.snap` (room 13 at the door $2a stall, health 47, rucksack oil 182 + crown 53).
Road (reload after every token, play.py): D L U (room 12) U L U (room 7, -2 creature 901) U R U L R U (room 6, -2) L L L (room 3) L U R U (room 9) R U (stall under gem 164,
facing it fires its event 7: +26 XP, a maggot 912 appears) I2 TAKE 164 (free), D L D R D (the maggot costs -1; a wait for it to clear is built into the tokens) -> room 3, then the reverse road
D R R R D U D R D D L D R D R R R R R R: rooms 2, 6, 7 (-2), 12, 13, 14, 19, 20 at (10,20,4,14); gR25 gD50, JR (RIGHT+FIRE jump from the floor: apex bottom z 35, lands on platform 286
past the gem), L (stall at (42,51,36,45), probe 290, icons 2 10 11 6), I2 TAKE 290 (free); U w150000 U (north wall, under object 207), I4 on 207 (event 5: HIDEs 206/208/209 and removes the
203/204 cover of the hole), gD22 gR70 U (door $41) -> room 21 at (68,55,62,49), gL45 = the hole's edge (44,55,38,49); then U falls into room 27 at (64,32,58,26) and lands 10 health lower with
all four items still carried.  Health 47 -> 40 at the edge, 30 after the fall; rucksack [290,164,182,53].
Checkpoints: <out dir>/gems/NN_<token>.snap."""
import sys, os
HD = os.path.dirname(os.path.abspath(__file__)); A = [os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])]
os.environ.setdefault('CAD_OUT', os.path.join(A[1], '_scratch'))   # the lib's own output (r16/r12/trek/h dirs) goes under the output dir
sys.path.insert(0, HD)
import play
TOKENS = ('D L U U L U U R U L R U L L L L U R U R U I2 D L D R D D R R R D U D R D D L D R D R R R R R R gR25 gD50 JR L I2 '
          'U w150000 U P I4 w300000 gD22 gR70 U w100000 gL45 U w100000 w700000').split()
if __name__ == '__main__':
    play.run(A[0], 'gems', TOKENS, outdir=A[1])
