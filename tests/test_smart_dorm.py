"""Test cases for Smart Dorm Energy Saver. Run: python test_smart_dorm.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import smart_dorm as sd


def close(a, b, tol=1e-3):
    return abs(a - b) < tol


# ---- Hill climbing
def test_hill_climbing_from_low_start():
    best, trace = sd.hill_climbing(start_index=0, verbose=False)        # start 4 h
    assert best == 8 and trace == [4, 6, 8]


def test_hill_climbing_from_high_start():
    best, trace = sd.hill_climbing(start_index=4, verbose=False)        # start 12 h
    assert best == 8 and trace == [12, 10, 8]


def test_hill_climbing_finds_true_minimum():
    assert sd.hill_climbing(verbose=False)[0] == min(sd.SCHEDULES, key=sd.schedule_cost)


# ---- Bayes
def test_bayes_no_motion():
    b = sd.bayes_home(motion=False)
    assert close(b["evidence"], 0.56) and close(b["posterior"], 0.18 / 0.56)    # 0.321


def test_bayes_motion():
    assert close(sd.bayes_home(motion=True)["posterior"], 0.42 / 0.44)          # 0.955


def test_bayes_probabilities_sum_to_one():
    b = sd.bayes_home(motion=False)
    assert close(b["joint_home"] / b["evidence"] + b["joint_empty"] / b["evidence"], 1.0)


# ---- MDP
def test_mdp_turn_off_when_probably_empty():
    action, q, _, _ = sd.mdp_decide(sd.bayes_home(motion=False)["posterior"])
    assert action == "Turn Off" and q["Turn Off"] > q["Keep On"]


def test_mdp_keep_on_when_probably_home():
    assert sd.mdp_decide(sd.bayes_home(motion=True)["posterior"])[0] == "Keep On"


def test_mdp_threshold():
    _, _, _, thr = sd.mdp_decide(0.5)
    assert close(thr, 8 / 22)
    assert sd.mdp_decide(thr + 0.01)[0] == "Keep On"
    assert sd.mdp_decide(thr - 0.01)[0] == "Turn Off"


# ---- Whole pipeline
def test_day_saves_money():
    planned, actual, rows = sd.simulate_day(sd.HOURS_OF[8], verbose=False)
    assert planned == 300 and actual == 187.5 and len(rows) == 24


def test_heats_outside_plan_when_student_is_home():
    home_12h = {h: True for h in range(10, 22)}                      # home 10:00-22:00
    planned, actual, rows = sd.simulate_day(sd.HOURS_OF[8], verbose=False, sensor=home_12h)
    on = [h for h, pl, m, p, a in rows if a == "Keep On"]
    assert on == list(range(10, 22))                                   # heats exactly the 12 hours at home
    assert actual == 12 * sd.COST_PER_HOUR and planned == 300


def test_stays_off_outside_plan_without_motion():
    _, _, rows = sd.simulate_day(sd.HOURS_OF[8], verbose=False, sensor={})
    assert all(a == "Turn Off" for h, pl, m, p, a in rows)


def test_bonus_finds_valid_schedule():
    bits, cost, res = sd.bonus_hill_climbing(restarts=3)
    assert len(bits) == 24 and cost == min(c for _, _, c in res)


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"PASS  {name}")
    print(f"\nAll {len(tests)} tests passed.")
