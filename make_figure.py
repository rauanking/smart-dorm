"""Builds smart_dorm_overview.png: one picture of the three algorithms for the README / defense."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import smart_dorm as sd

INK, MUTED, BLUE, GOLD, RED, GREEN = "#1d2733", "#6b7a8c", "#1f77b4", "#e3a008", "#d64545", "#2e9e5b"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 12, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(16, 5.2))

# 1. hill climbing
costs = [sd.schedule_cost(h) for h in sd.SCHEDULES]
ax[0].plot(sd.SCHEDULES, costs, "o-", color=MUTED, lw=2, ms=8)
_, trace = sd.hill_climbing(verbose=False)
for a, b in zip(trace, trace[1:]):
    ax[0].annotate("", xy=(b, sd.schedule_cost(b)), xytext=(a, sd.schedule_cost(a)),
                   arrowprops=dict(arrowstyle="->", color=BLUE, lw=2.5))
ax[0].scatter([8], [sd.schedule_cost(8)], s=260, color=GOLD, zorder=5)
ax[0].text(8, sd.schedule_cost(8) - 28, "best: 8 h\n390 tg", ha="center", va="top", weight="bold")
ax[0].set(title="1 · Hill climbing: daily schedule", xlabel="heating hours per day", ylabel="cost, tg", ylim=(300, 590))

# 2. Bayes
labels = ["prior", "no motion", "motion"]
vals = [sd.PRIOR_HOME, sd.bayes_home(False)["posterior"], sd.bayes_home(True)["posterior"]]
bars = ax[1].bar(labels, vals, color=[MUTED, BLUE, BLUE], width=0.55)
for b, v in zip(bars, vals):
    ax[1].text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.0%}", ha="center", weight="bold")
thr = sd.mdp_decide(0.5)[3]
ax[1].axhline(thr, color=GOLD, ls="--", lw=2)
ax[1].text(-0.3, thr + 0.025, f"MDP threshold {thr:.1%}", ha="left", color=GOLD, weight="bold")
ax[1].set(title="2 · Bayes: P(student is home)", ylim=(0, 1.08), yticks=[0, .25, .5, .75, 1])

# 3. MDP
x = range(2)
for i, (motion, name) in enumerate([(False, "no motion"), (True, "motion")]):
    _, q, _, _ = sd.mdp_decide(sd.bayes_home(motion)["posterior"])
    for j, a in enumerate(sd.ACTIONS):
        v = q[a]
        ax[2].bar(i + (j - 0.5) * 0.36, v, width=0.34, color=["#e8833a", "#4a90c2"][j],
                  label=a if i == 0 else None)
        ax[2].text(i + (j - 0.5) * 0.36, v + (0.3 if v >= 0 else -0.3), f"{v:+.2f}", ha="center",
                   va="bottom" if v >= 0 else "top", fontsize=11)
ax[2].axhline(0, color=INK, lw=1)
ax[2].set_xticks(list(x), ["no motion\n→ TURN OFF", "motion\n→ KEEP ON"])
ax[2].set(title="3 · MDP: expected reward Q(a)", ylim=(-9.5, 7.5))
ax[2].legend(frameon=False, loc="lower left")

fig.suptitle("Smart Dorm Energy Saver — plan (hill climbing) → belief (Bayes) → action (MDP)", fontsize=15, weight="bold")
fig.tight_layout()
fig.savefig("smart_dorm_overview.png", dpi=150)
print("saved smart_dorm_overview.png")
