"""Python model of Little Computer People's behaviour scheduler (ST, Mockingbird #3 build; README "The behaviour
scheduler"). Transcribed from the routines' 68000 bodies, not from a decompile:

  `$1876a` rnd(lo, hi): lo + (XBIOS 17 Random() & $7fff) mod (hi - lo + 1)
  `$1747e` secondary desire: hours awake -> period (begin/middle/end) -> list A/B/C by personality, weekday
           override, then draw from the 16-entry list until the draw differs from the last action `$4c5a4`.

TOS 1.00's Random (the emulator runs the real ROM): seed = seed * 3141592621 + 1 (mod 2^32), returns
(seed >> 8) & $ffffff; seed is the long at `$29b8`.
"""
SEED = 0x29b8
LIST_A, LIST_B, LIST_C, PERIOD_TABLE = 0x2b43e, 0x2b45e, 0x2b47e, 0x2b49e

# name -> (address, width) of the inputs `$1747e` reads
FIELDS = {
    'hour': (0x4ca20, 2),         # current hour, 0..23
    'mday': (0x4ca22, 2),         # day of the month (read by the weekday routine $2459c)
    'wake': (0x5142c, 2),         # HYBER +$06, wake-up hour
    'personality': (0x51434, 2),  # HYBER +$0e, 0..7
    'ill': (0x5145a, 2),          # HYBER +$34, illness level
    'in_bed': (0x51460, 2),       # HYBER +$3a
    'last': (0x4c5a4, 2),         # the action most recently started (written by $172a6)
}

BROKEN = ['no_weekday', 'no_norepeat', 'period_hours', 'ill_ge1', 'rnd_0_14', 'transposed']


def tos_random(seed):
    seed = (seed * 3141592621 + 1) & 0xffffffff
    return seed, (seed >> 8) & 0xffffff


def rnd(seed, lo, hi):
    seed, r = tos_random(seed)
    return seed, lo + (r & 0x7fff) % (hi - lo + 1)


def read_tables(read):
    def words(a, n):
        b = read(a, 2 * n)
        return [int.from_bytes(b[2 * i:2 * i + 2], 'big', signed=True) for i in range(n)]
    return {'A': words(LIST_A, 16), 'B': words(LIST_B, 16), 'C': words(LIST_C, 16),
            'period': words(PERIOD_TABLE, 24)}


def secondary(st, t, variant='true'):
    """Return (action, list name) as `$1747e` would. `variant` names one deliberately wrong rule (a control)."""
    awake = st['hour'] - st['wake']
    if awake < 0:
        awake += 24
    ill_limit = 1 if variant == 'ill_ge1' else 2
    if awake >= 18 or st['ill'] >= ill_limit:
        return (4 if st['in_bed'] == 0 else -1), 'bed'
    period = awake % 3 if variant == 'period_hours' else (awake // 2) % 3
    if variant == 'transposed':
        idx = st['personality'] % 3 * 8 + period          # wrong axis order
    else:
        idx = period * 8 + st['personality']
    which = 'ABC'[t['period'][idx]]
    if variant != 'no_weekday' and which == 'A':
        if st['weekday'] == 0:
            which = 'C'
        elif st['weekday'] == 6:
            which = 'B'
    seed = st['seed']
    hi = 14 if variant == 'rnd_0_14' else 15
    for _ in range(1000):
        seed, k = rnd(seed, 0, hi)
        a = t[which][k]
        if variant == 'no_norepeat' or a != st['last']:
            return a, which
    return None, which


# ---- `$16f50`, the top-level chooser, run whenever the LCP is idle ------------------------------------------
TOP = {  # name -> address of the word `$16f50` reads (all words)
    'event_head': 0x2c948,   # -1 when the house-event queue is empty, else `$27270` dequeues and `$1721c` runs it
    'alarm': 0x3df6c,        # alarm clock ringing
    'pee': 0x51470,          # HYBER +$4a, needs to pee
    'ill': 0x5145a, 'thirst': 0x51464, 'water': 0x5141a, 'hunger': 0x5146a,
    'bits': 0x5147e,         # HYBER +$58; bits 9..11 = cans of food
    'last': 0x4c5a4, 'hour': 0x4ca20,
    'lunch_done': 0x2ae18, 'dinner_done': 0x2ae1a, 'wake_done': 0x2ae1c, 'sleep_done': 0x2ae1e,
    'lunch': 0x5142e, 'dinner': 0x51430, 'wake': 0x5142c, 'sleep': 0x5142a,
    'qcount': 0x3dce2,
}
QPRIO, QACT = 0x3e272, 0x40966   # ten words each: the player-query queue (priority, action)


def toplevel(st, variant='true'):
    """Return (label, action, qcount, qprio, qact) for one `$16f50` pass. label: 'event', 'start' (an action handed
    to `$172a6`), 'agree' (`$2310a`, before a play/piano query runs) or 'secondary' (`$1747e` reached)."""
    q = st['qcount']; qp = list(st['qprio']); qa = list(st['qact'])
    if st['event_head'] != -1:
        return 'event', None, q, qp, qa
    if st['alarm']:
        return 'start', 0x29, q, qp, qa
    if st['pee']:
        return 'start', 0x15, q, qp, qa
    seed = st['seed']
    a = 0 if st['ill'] > 0 else 0x42
    if st['thirst'] > 0:
        seed, r = rnd(seed, 1, 100)
        if r > a and (st['ill'] == 0 or st['water'] != 0 or variant == 'ill_ignores_water'):
            return 'start', 0x0d, q, qp, qa
    cans = (st['bits'] >> 9) & 7
    if st['hunger'] > 0:
        seed, r = rnd(seed, 1, 100)
        if r > a:
            if (st['ill'] != 0 and cans != 0) or ((st['last'] != 0x12 or variant == 'eat_repeats') and st['ill'] == 0):
                return 'start', 0x12, q, qp, qa
    for done, hour, act in (('lunch_done', 'lunch', 0x19), ('dinner_done', 'dinner', 0x19),
                            ('wake_done', 'wake', 0x2b), ('sleep_done', 'sleep', 0x2c)):
        if st[done] == 0 and st[hour] == st['hour']:
            return 'start', act, q, qp, qa
    if q > 0:
        if qp[0] < 4:
            qa[:9] = qa[1:10]; qp[:9] = qp[1:10]
            if variant == 'drop_decrements':
                q -= 1
        elif qp[0] < (7 if variant == 'execute_at_7' else 8):
            qp[0] += 1
        else:
            act = qa[0]
            if act in (0x10, 0x1a):   # `$2310a` runs before the shift, so a stop there sees the queue unchanged
                return 'agree', act, q, qp, qa
            qa[:9] = qa[1:10]; qp[:9] = qp[1:10]
            q -= 1
            return ('agree' if act in (0x10, 0x1a) else 'start'), act, q, qp, qa
    return 'secondary', None, q, qp, qa


# ---- `$17c46`, a new LCP (run when there is no HYBER file) ---------------------------------------------------
# (field, HYBER offset or absolute address, lo, hi), in the order the routine draws them
NEW_DRAWS = [('head', 0x51480, 2, 6), ('name_index', None, 0, 265),
             ('clothes', 0x51426, 0, 15), ('pyjamas', 0x51428, 0, 7), ('sleep', 0x5142a, 22, 24),
             ('lunch', 0x5142e, 11, 13), ('dinner', 0x51430, 17, 19), ('unused', 0x51432, 0, 3),
             ('personality', 0x51434, 0, 7), ('happy_t0', 0x51450, 6, 24), ('happy_t1', 0x51452, 6, 24),
             ('happy_t2', 0x51454, 6, 12), ('tidiness', 0x51462, 20, 80), ('thirst_t', 0x51466, 45, 75),
             ('hunger_t', 0x5146c, 75, 120), ('pee_t', 0x51472, 20, 40)]


def new_person(seed, names, variant='true'):
    """names: the NAMES file bytes (266 entries of 10). Returns {field: value} plus 'wake' and 'name'."""
    draws = NEW_DRAWS
    if variant == 'swap_unused_personality':
        draws = draws[:7] + [draws[8], draws[7]] + draws[9:]
    out = {}
    for name, _, lo, hi in draws:
        if variant == 'sleep_22_23' and name == 'sleep':
            hi = 23
        seed, out[name] = rnd(seed, lo, hi)
    if out['sleep'] > 23:
        out['sleep'] -= 24
    out['wake'] = out['sleep'] + 6 if out['sleep'] + 6 <= 23 else out['sleep'] - 18
    raw = names[out['name_index'] * 10: out['name_index'] * 10 + 10]
    out['name'] = bytes(c if c >= 0x41 else 0 for c in raw)
    return out
