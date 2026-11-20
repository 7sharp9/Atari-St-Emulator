"""compare.py <fresh.json> <saved.json> : do two census files agree on every life loss (tick, wave, cause, fuel, entry)?  Prints N/N.
Exit 0 always; the gate greps the line.  Used as the gate's check that a fresh run reproduces the saved census, and as its broken control
(a fresh game compared with a different game's saved file must give 0 agreeing)."""
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
k = lambda d: (d['state']['tick'], d['state']['wave'], d['cause'], d['state']['fuel'], d['entry'])
da, db = a['deaths'], b['deaths']
same = sum(1 for x, y in zip(da, db) if k(x) == k(y))
print(f"census game {a['game']} fresh vs saved game {b['game']}: {same}/{max(len(da), len(db))} life losses identical (tick, wave, cause, fuel at death, entry); over {a['over']['tick']} vs {b['over']['tick']}")
