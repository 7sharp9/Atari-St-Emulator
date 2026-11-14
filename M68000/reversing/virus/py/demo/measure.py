"""measure.py <snap>... : fly each demo-start snapshot and print HUD measures at ticks 200/400/700/1000 (first 100k-step sample at/after the tick),
plus min lives seen and number of life losses. Fields: score $2708e (long), lives $32a54, rockets $32a40, wave $32a50, fuel $32a2e, hi $2709a."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
TICKS = [200, 400, 700, 1000]; STEP = 100000; N = 520
w = lambda b, o=0: int.from_bytes(b[o:o+2], 'big'); l = lambda b: int.from_bytes(b, 'big', signed=True)
for snap in sys.argv[1:]:
    cmds = []
    for i in range(N): cmds += [f's {STEP}', 'm 32a44 2', 'm 2708e 4', 'm 32a54 2', 'm 32a40 2', 'm 32a50 2', 'm 32a2e 2', 'm 270b0 6']
    rows = drv.mem(drv.run(snap, cmds)); assert len(rows) == 7*N, len(rows)
    S = [rows[7*i:7*i+7] for i in range(N)]
    lives = [w(s[2]) for s in S]; losses = sum(1 for a, b in zip(lives, lives[1:]) if b < a)
    out = []
    for T in TICKS:
        s = next((s for s in S if w(s[0]) >= T), None)
        if s: out.append(f'T{T}: tick={w(s[0])} score={l(s[1])} lives={w(s[2])} rockets={w(s[3])} wave={w(s[4])} fuel={w(s[5])} pos=({w(s[6],0)},{w(s[6],2)},{w(s[6],4)})')
    print(os.path.basename(snap), f'lives_min={min(lives)} life_losses={losses}'); [print('   ', o) for o in out]
