"""
Smart Dorm Energy Saver — AI Fundamentals Final Project
Student: Bolat Rauan · Stream 2, Practice 2

Problem: an electric heater in a dorm room in Astana (winter). Heating all day is expensive,
not heating is cold. The agent plans the heating and switches it off when the room is empty.

Three course algorithms, one goal (warm room for less money):
  1. HILL CLIMBING (local search)  – choose the best of 5 daily heating schedules.
  2. BAYESIAN INFERENCE            – from a motion-sensor reading, infer P(student is home).
  3. MDP (one Bellman update)      – with that probability, choose Keep On or Turn Off.
  4. DAY SIMULATION                – plan (1) is corrected hour by hour by (2)+(3); money saved is reported.

All numbers are hypothetical assumptions for a toy model (allowed by the project guidelines).
Run:  python smart_dorm.py            main demonstration
      python smart_dorm.py --bonus    + 24-hour schedule hill climbing with random restarts
"""
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")      # Windows console; not needed (and not available) in Colab
except AttributeError:
    pass

# ================================================================= assumptions
HEATER_KW = 1.5                       # heater power, kW
PRICE_TG_PER_KWH = 25                 # electricity price, tenge per kWh
COST_PER_HOUR = HEATER_KW * PRICE_TG_PER_KWH      # 37.5 tg for one hour of heating

# ================================================================= 1. HILL CLIMBING
# five candidate schedules (hours of heating per day), ordered so neighbours differ by 2 hours
SCHEDULES = [4, 6, 8, 10, 12]
# discomfort penalty in tenge-equivalent: fewer heating hours → colder room → bigger penalty
DISCOMFORT = {4: 400, 6: 200, 8: 90, 10: 40, 12: 20}
# which hours of the day each schedule heats (used later by the day simulation)
HOURS_OF = {
    4: [6, 7, 21, 22],
    6: [6, 7, 19, 20, 21, 22],
    8: [6, 7, 17, 18, 19, 20, 21, 22],
    10: [6, 7, 8, 16, 17, 18, 19, 20, 21, 22],
    12: [5, 6, 7, 8, 15, 16, 17, 18, 19, 20, 21, 22],
}


def schedule_cost(hours):
    """Objective to MINIMISE: electricity cost + discomfort penalty (tenge)."""
    return hours * COST_PER_HOUR + DISCOMFORT[hours]


def hill_climbing(start_index=0, verbose=True):
    """Steepest-descent hill climbing on the line of 5 schedules.
    Neighbours of schedule i are i−1 and i+1. Move to the best neighbour while it is better; stop otherwise."""
    current = start_index
    trace = [SCHEDULES[current]]
    step = 0
    if verbose:
        print(f"Start: {SCHEDULES[current]} h, cost {schedule_cost(SCHEDULES[current]):.0f} tg")
    while True:
        step += 1
        neigh = [i for i in (current - 1, current + 1) if 0 <= i < len(SCHEDULES)]
        best = min(neigh, key=lambda i: schedule_cost(SCHEDULES[i]))
        if verbose:
            shown = ", ".join(f"{SCHEDULES[i]} h = {schedule_cost(SCHEDULES[i]):.0f}" for i in neigh)
            print(f"Step {step}: at {SCHEDULES[current]} h ({schedule_cost(SCHEDULES[current]):.0f}); neighbours: {shown}")
        if schedule_cost(SCHEDULES[best]) < schedule_cost(SCHEDULES[current]):
            current = best
            trace.append(SCHEDULES[current])
            if verbose:
                print(f"        → move to {SCHEDULES[current]} h (better)")
        else:
            if verbose:
                print("        → no neighbour is better: STOP (local optimum)")
            return SCHEDULES[current], trace


# ================================================================= 2. BAYESIAN INFERENCE
PRIOR_HOME = 0.60                     # P(Home) during heating hours (evening, from habit)
P_NOMOTION_IF_HOME = 0.30             # student sleeps / sits still at the laptop
P_NOMOTION_IF_EMPTY = 0.95            # sensor rarely sees motion in an empty room (5% false triggers)


def bayes_home(motion, prior=None):
    """P(Home | sensor reading) with every intermediate number.
    motion=True  → the sensor saw movement in the last 30 min,
    motion=False → no movement for 30 min.
    prior defaults to PRIOR_HOME, read at call time so a changed setting is used."""
    if prior is None:
        prior = PRIOR_HOME
    like_home = (1 - P_NOMOTION_IF_HOME) if motion else P_NOMOTION_IF_HOME
    like_empty = (1 - P_NOMOTION_IF_EMPTY) if motion else P_NOMOTION_IF_EMPTY
    joint_home = like_home * prior
    joint_empty = like_empty * (1 - prior)
    evidence = joint_home + joint_empty
    return {
        "prior": prior, "like_home": like_home, "like_empty": like_empty,
        "joint_home": joint_home, "joint_empty": joint_empty,
        "evidence": evidence, "posterior": joint_home / evidence,
    }


# ================================================================= 3. MDP
STATES = ("Home", "Empty")
ACTIONS = ("Keep On", "Turn Off")
# reward for one hour (points): comfort is good, wasted energy is bad, a cold student is worst
REWARD = {
    ("Home", "Keep On"): 6,      # warm student
    ("Empty", "Keep On"): -4,    # heating an empty room = wasted money
    ("Home", "Turn Off"): -8,    # student is cold
    ("Empty", "Turn Off"): 4,    # money saved
}
# transition model: probability the room is in s' next hour (the heater does not change occupancy)
TRANSITION = {"Home": {"Home": 0.8, "Empty": 0.2}, "Empty": {"Home": 0.3, "Empty": 0.7}}
GAMMA = 0.9
V0 = {"Home": 0.0, "Empty": 0.0}      # values before the first Bellman update


def mdp_decide(p_home):
    """One Bellman update from V0 = 0, evaluated under the Bayesian belief:
         Q(s, a) = R(s, a) + γ · Σ_s' P(s'|s) · V0(s')
         Q(a)    = Σ_s b(s) · Q(s, a)        with b(Home) = p_home
    Because V0 = 0 the future term is 0 and Q(a) is the expected one-step reward."""
    belief = {"Home": p_home, "Empty": 1 - p_home}
    q_sa = {(s, a): REWARD[(s, a)] + GAMMA * sum(TRANSITION[s][s2] * V0[s2] for s2 in STATES)
            for s in STATES for a in ACTIONS}
    q = {a: sum(belief[s] * q_sa[(s, a)] for s in STATES) for a in ACTIONS}
    # threshold where both actions are equal: 6p − 4(1−p) = −8p + 4(1−p)  →  p* = 8/22
    a, b = REWARD[("Home", "Keep On")] - REWARD[("Empty", "Keep On")], REWARD[("Empty", "Keep On")]
    c, d = REWARD[("Home", "Turn Off")] - REWARD[("Empty", "Turn Off")], REWARD[("Empty", "Turn Off")]
    threshold = (d - b) / (a - c)
    return max(q, key=q.get), q, q_sa, threshold


# ================================================================= 4. DAY SIMULATION
# hypothetical motion-sensor readings for one winter day (True = motion seen)
# hours not listed = no motion
SENSOR_DAY = {6: True, 7: True, 8: False, 15: False, 16: False, 17: True, 18: False,
              19: False, 20: True, 21: True, 22: False}
# outside the plan the student is usually away, so the prior is lower
PRIOR_OFF_PLAN = 0.30


def simulate_day(hours, verbose=True, sensor=None):
    """Every hour of the day: sensor → Bayes → MDP → heater On (Keep On) or Off (Turn Off).
    Inside the plan the prior is PRIOR_HOME; outside it is PRIOR_OFF_PLAN, so the agent can also
    switch the heater ON outside the plan when it sees the student. Returns plan cost, agent cost, rows."""
    sensor = SENSOR_DAY if sensor is None else sensor
    rows, on_hours = [], 0
    for h in range(24):
        planned = h in hours
        motion = sensor.get(h, False)
        p = bayes_home(motion, PRIOR_HOME if planned else PRIOR_OFF_PLAN)["posterior"]
        action, q, _, _ = mdp_decide(p)
        on_hours += action == "Keep On"
        rows.append((h, planned, motion, p, action))
    planned_cost = len(hours) * COST_PER_HOUR
    actual = on_hours * COST_PER_HOUR
    if verbose:
        print(f"{'Hour':>6s}  {'In plan':8s}{'Sensor':10s} {'P(Home)':>8s}  Heater")
        for h, pl, m, p, a in rows:
            if pl or a == "Keep On":
                print(f"{h:4d}:00  {'yes' if pl else 'NO':8s}{'motion' if m else 'no motion':10s} {p:8.3f}  {'ON' if a == 'Keep On' else 'off'}")
        print("(hours outside the plan with no motion stay off)")
        print(f"\nPlan alone: {len(hours)} h × {COST_PER_HOUR:.1f} tg = {planned_cost:.1f} tg")
        print(f"With agent: {on_hours} h × {COST_PER_HOUR:.1f} tg = {actual:.1f} tg")
        diff = planned_cost - actual
        if diff >= 0:
            print(f"Saved today: {diff:.1f} tg ({diff / planned_cost:.0%});  ≈ {diff * 30:.0f} tg per month")
        else:
            print(f"Extra heating for comfort: {-diff:.1f} tg (the student was home outside the plan)")
    return planned_cost, actual, rows


# ================================================================= BONUS: 24-hour schedule
OUTSIDE_COLD = [1.0] * 6 + [0.8] * 6 + [0.6] * 6 + [0.9] * 6          # how cold each hour is (night coldest)
P_HOME_BY_HOUR = [0.95] * 8 + [0.2] * 8 + [0.7] * 8                    # usually home at night / evening
SWITCH_COST = 15                                                        # tg-equivalent per on/off switch


def bonus_cost(bits):
    """24 bits, 1 = heat this hour. Cost = energy + discomfort when off at home + switching wear."""
    energy = sum(bits) * COST_PER_HOUR
    discomfort = sum(70 * P_HOME_BY_HOUR[h] * OUTSIDE_COLD[h] for h in range(24) if not bits[h])
    switches = sum(bits[h] != bits[h - 1] for h in range(24))
    return energy + discomfort + switches * SWITCH_COST


def bonus_hill_climbing(restarts=10, seed=42):
    """Neighbour = flip one hour. Steepest descent from a random start; repeat with random restarts."""
    rng = random.Random(seed)
    best_bits, best_cost, results = None, float("inf"), []
    for r in range(restarts):
        bits = [rng.randint(0, 1) for _ in range(24)]
        cost, steps = bonus_cost(bits), 0
        while True:
            options = []
            for h in range(24):
                nb = bits[:]; nb[h] ^= 1
                options.append((bonus_cost(nb), nb))
            c, nb = min(options, key=lambda x: x[0])
            if c >= cost:
                break
            bits, cost, steps = nb, c, steps + 1
        results.append((r + 1, steps, cost))
        if cost < best_cost:
            best_bits, best_cost = bits, cost
    return best_bits, best_cost, results


# ================================================================= printing
def title(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def step1():
    title("STEP 1 · HILL CLIMBING — choose the daily heating schedule")
    print("Input: 5 schedules; cost = hours × 37.5 tg + discomfort penalty")
    print(f"{'Hours':>6s} {'Electricity':>12s} {'Discomfort':>11s} {'Total':>7s}")
    for h in SCHEDULES:
        print(f"{h:6d} {h * COST_PER_HOUR:12.1f} {DISCOMFORT[h]:11d} {schedule_cost(h):7.1f}")
    print()
    best, trace = hill_climbing(start_index=0)
    print(f"\nOutput: best schedule = {best} h/day, cost {schedule_cost(best):.1f} tg; path {' → '.join(map(str, trace))}")
    print(f"Heating hours: {', '.join(f'{h:02d}:00' for h in HOURS_OF[best])}")
    print("Why: hill climbing moves to a better neighbouring schedule until no neighbour improves the cost.")
    return best


def step2():
    title("STEP 2 · BAYES — is the student home?  (18:00 is planned ON, sensor: no motion for 30 min)")
    for motion in (False, True):
        b = bayes_home(motion)
        obs = "motion" if motion else "no motion"
        print(f"Observation: {obs}")
        print(f"  Prior       P(Home) = {b['prior']:.2f}   P(Empty) = {1 - b['prior']:.2f}")
        print(f"  Likelihood  P({obs} | Home) = {b['like_home']:.2f}   P({obs} | Empty) = {b['like_empty']:.2f}")
        print(f"  Joint       {b['like_home']:.2f}×{b['prior']:.2f} = {b['joint_home']:.3f}    "
              f"{b['like_empty']:.2f}×{1 - b['prior']:.2f} = {b['joint_empty']:.3f}")
        print(f"  Evidence    P({obs}) = {b['joint_home']:.3f} + {b['joint_empty']:.3f} = {b['evidence']:.3f}")
        print(f"  Posterior   P(Home | {obs}) = {b['joint_home']:.3f} / {b['evidence']:.3f} = {b['posterior']:.3f}")
    print("Why: Bayes' rule combines the usual habit (prior) with the new sensor evidence.")


def step3():
    title("STEP 3 · MDP — Keep On or Turn Off?")
    print("States: Home, Empty   Actions: Keep On, Turn Off   γ = 0.9, V0 = 0 (one Bellman update)")
    print(f"Reward table:  {'':9s}{'Home':>6s}{'Empty':>7s}")
    for a in ACTIONS:
        print(f"               {a:9s}{REWARD[('Home', a)]:6d}{REWARD[('Empty', a)]:7d}")
    for motion in (False, True):
        p = bayes_home(motion)["posterior"]
        action, q, _, thr = mdp_decide(p)
        print(f"\nBelief from Bayes ({'motion' if motion else 'no motion'}): P(Home) = {p:.3f}")
        for a in ACTIONS:
            print(f"  Q({a}) = {p:.3f}×({REWARD[('Home', a)]} + γ·0) + {1 - p:.3f}×({REWARD[('Empty', a)]} + γ·0) = {q[a]:+.2f}")
        print(f"  Decision → {action.upper()}   (Keep On is better only when P(Home) > {thr:.3f})")
    print("\nWhy: the MDP picks the action with the highest expected reward under uncertainty.")


def step4(best=None):
    best = best or hill_climbing(verbose=False)[0]
    title(f"STEP 4 · ONE DAY — the {best}-hour plan corrected every hour by Bayes + MDP")
    simulate_day(HOURS_OF[best])


def bonus_demo():
    title("BONUS · HILL CLIMBING ON A REAL 24-HOUR SCHEDULE (2^24 ≈ 16.8 million options)")
    bits, cost, res = bonus_hill_climbing()
    for r, steps, c in res:
        print(f"  restart {r:2d}: {steps:2d} moves → local optimum {c:7.1f}")
    print("  Best schedule: " + "".join("█" if b else "·" for b in bits) + "   (00:00 … 23:00)")
    distinct = sorted({round(c, 1) for _, _, c in res})
    print(f"  Best cost {cost:.1f}; local optima found: {distinct}")
    if len(distinct) == 1:
        print("  All restarts reached the same schedule → very likely the global optimum.")
    else:
        print("  Restarts stopped in different local optima → random restarts were needed.")


def main(bonus=False):
    print("SMART DORM ENERGY SAVER · heater in a dorm room in Astana (toy model)")
    print(f"Assumptions: heater {HEATER_KW} kW, electricity {PRICE_TG_PER_KWH} tg/kWh → {COST_PER_HOUR} tg per heating hour")
    best = step1()
    step2()
    step3()
    step4(best)
    if bonus:
        bonus_demo()


if __name__ == "__main__":
    main(bonus="--bonus" in sys.argv)
