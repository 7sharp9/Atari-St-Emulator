"""mfilter.py: A1.  Hand-built action filter for the captain-item legs: walks always, plus only the named operate/take/throw/cast actions."""
def mfilter(ops=(), takes=(), throws=(), cast=False, applies=(), touch=()):
    def f(S, act):
        k = act[0]
        if k == 'walk': return True
        if k == 'operate': return act[1] in ops
        if k == 'take': return act[1] in takes
        if k == 'throw': return act[1] in throws and act[2] == 1 and S['room'] == 87
        if k == 'cast8': return cast
        if k == 'apply': return (act[1], act[2]) in applies
        if k == 'throw_at': return True
        if k == 'wait': return True
        if k == 'region': return S['room'] == 88 and act[1] == 1
        return False
    return f
