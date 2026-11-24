"""Writes tests/reference.json: Python results for several parameter sets (used by consistency_test.js)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import smart_dorm as sd

CASES = [
    {},                                                         # defaults from the report
    {"PRIOR_HOME": 0.9},
    {"PRIOR_HOME": 0.2, "P_NOMOTION_IF_HOME": 0.5},
    {"P_NOMOTION_IF_EMPTY": 0.7, "REWARD": {"homeKeep": 6, "emptyKeep": -10, "homeOff": -8, "emptyOff": 4}},
    {"DISCOMFORT": {4: 100, 6: 50, 8: 40, 10: 30, 12: 25}},
    {"REWARD": {"homeKeep": 6, "emptyKeep": -4, "homeOff": -20, "emptyOff": 4}},
]
base = {k: getattr(sd, k) for k in ("PRIOR_HOME", "P_NOMOTION_IF_HOME", "P_NOMOTION_IF_EMPTY", "DISCOMFORT", "REWARD")}
out = []
for case in CASES:
    for k, v in base.items():
        setattr(sd, k, v)
    for k, v in case.items():
        if k == "REWARD":
            v = {("Home", "Keep On"): v["homeKeep"], ("Empty", "Keep On"): v["emptyKeep"],
                 ("Home", "Turn Off"): v["homeOff"], ("Empty", "Turn Off"): v["emptyOff"]}
        setattr(sd, k, v)
    hc = {str(s): list(sd.hill_climbing(s, verbose=False)) for s in range(5)}
    bay = {str(m): sd.bayes_home(m) for m in (True, False)}
    mdp = {}
    for p in (0.05, 0.3, 0.364, 0.5, 0.95):
        a, q, _, thr = sd.mdp_decide(p)
        mdp[str(p)] = {"action": a, "q": q, "threshold": thr}
    best = sd.hill_climbing(verbose=False)[0]
    planned, actual, rows = sd.simulate_day(sd.HOURS_OF[best], verbose=False)
    out.append({"case": {k: (v if k != "DISCOMFORT" else {str(a): b for a, b in v.items()}) for k, v in case.items()},
                "hill": hc, "bayes": bay, "mdp": mdp,
                "day": {"best": best, "planned": planned, "actual": actual, "actions": [r[3] for r in rows]},
                "bonus_best": round(sd.bonus_hill_climbing()[1], 6)})
json.dump(out, open(os.path.join(os.path.dirname(__file__), "reference.json"), "w"), indent=1)
print(len(out), "cases")
