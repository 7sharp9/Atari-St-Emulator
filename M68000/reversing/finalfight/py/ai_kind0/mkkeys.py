# deterministic pseudo-random Cody input plan -> FF_KEYS string. usage: mkkeys.py <start> <end> <seed>
import random, sys
a, b, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(seed)
out = []
t = a
while t < b:
    d = rng.choice(['left', 'right', 'left', 'right', 'up', 'down'])
    n = rng.randint(10, 40)
    out.append('%s:%d-%d' % (d, t, t + n))
    t += n
    for _ in range(rng.randint(1, 4)):
        if rng.random() < 0.2:
            out.append('b2:%d-%d' % (t, t + 3)); t += 6
            out.append('b1:%d-%d' % (t, t + 3)); t += 12
        else:
            out.append('b1:%d-%d' % (t, t + 3)); t += rng.randint(7, 16)
print(','.join(out))
