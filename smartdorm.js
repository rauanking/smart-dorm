/*
 * Smart Dorm Energy Saver — core AI logic (browser + Node).
 * The same three algorithms as smart_dorm.py, written as pure functions:
 *   1. Hill climbing (local search)      — best daily heating schedule
 *   2. Bayesian inference                — P(student is home | motion sensor)
 *   3. MDP, one Bellman update           — Keep On or Turn Off
 *   4. Day simulation                    — plan corrected every hour by 2 + 3
 * tests/consistency_test.js checks that these functions give the same numbers as the Python code.
 */
(function (root) {
  "use strict";

  const DEFAULTS = {
    heaterKw: 1.5,
    price: 25,                                    // tenge per kWh
    schedules: [4, 6, 8, 10, 12],                 // heating hours per day
    discomfort: { 4: 400, 6: 200, 8: 90, 10: 40, 12: 20 },
    hoursOf: {
      4: [6, 7, 21, 22],
      6: [6, 7, 19, 20, 21, 22],
      8: [6, 7, 17, 18, 19, 20, 21, 22],
      10: [6, 7, 8, 16, 17, 18, 19, 20, 21, 22],
      12: [5, 6, 7, 8, 15, 16, 17, 18, 19, 20, 21, 22],
    },
    prior: 0.6,                                   // P(Home) during planned heating hours
    priorOffPlan: 0.3,                            // P(Home) outside the plan (student usually away)
    pNoMotionHome: 0.3,                           // P(no motion | Home)
    pNoMotionEmpty: 0.95,                         // P(no motion | Empty)
    reward: { homeKeep: 6, emptyKeep: -4, homeOff: -8, emptyOff: 4 },
    transition: { Home: { Home: 0.8, Empty: 0.2 }, Empty: { Home: 0.3, Empty: 0.7 } },
    gamma: 0.9,
    sensorDay: { 6: true, 7: true, 8: false, 15: false, 16: false, 17: true, 18: false,
                 19: false, 20: true, 21: true, 22: false },
    // bonus: 24-hour schedule
    outsideCold: [].concat(Array(6).fill(1.0), Array(6).fill(0.8), Array(6).fill(0.6), Array(6).fill(0.9)),
    pHomeByHour: [].concat(Array(8).fill(0.95), Array(8).fill(0.2), Array(8).fill(0.7)),
    switchCost: 15,
  };

  const costPerHour = (P) => P.heaterKw * P.price;

  // ------------------------------------------------------------ 1. hill climbing
  function scheduleCost(P, hours) {
    return hours * costPerHour(P) + P.discomfort[hours];
  }

  /** Steepest descent on the line of schedules. Neighbours of i are i−1 and i+1. */
  function hillClimbing(P, startIndex = 0) {
    const S = P.schedules;
    let current = startIndex;
    const trace = [S[current]];
    const log = [];
    for (;;) {
      const neigh = [current - 1, current + 1].filter((i) => i >= 0 && i < S.length);
      let best = neigh[0];
      for (const i of neigh) if (scheduleCost(P, S[i]) < scheduleCost(P, S[best])) best = i;
      const entry = {
        at: S[current], cost: scheduleCost(P, S[current]),
        neighbours: neigh.map((i) => ({ hours: S[i], cost: scheduleCost(P, S[i]) })), moveTo: null,
      };
      if (scheduleCost(P, S[best]) < scheduleCost(P, S[current])) {
        current = best;
        trace.push(S[current]);
        entry.moveTo = S[current];
        log.push(entry);
      } else {
        log.push(entry);
        return { best: S[current], trace, log };
      }
    }
  }

  // ------------------------------------------------------------ 2. Bayes
  function bayes(P, motion, prior = P.prior) {
    const likeHome = motion ? 1 - P.pNoMotionHome : P.pNoMotionHome;
    const likeEmpty = motion ? 1 - P.pNoMotionEmpty : P.pNoMotionEmpty;
    const jointHome = likeHome * prior;
    const jointEmpty = likeEmpty * (1 - prior);
    const evidence = jointHome + jointEmpty;
    return { prior, likeHome, likeEmpty, jointHome, jointEmpty, evidence, posterior: jointHome / evidence };
  }

  // ------------------------------------------------------------ 3. MDP
  const STATES = ["Home", "Empty"];
  const ACTIONS = ["Keep On", "Turn Off"];

  function rewardOf(P, s, a) {
    const r = P.reward;
    if (a === "Keep On") return s === "Home" ? r.homeKeep : r.emptyKeep;
    return s === "Home" ? r.homeOff : r.emptyOff;
  }

  /** One Bellman update from V0 = 0, evaluated under the belief b(Home) = pHome. */
  function mdp(P, pHome) {
    const V0 = { Home: 0, Empty: 0 };
    const belief = { Home: pHome, Empty: 1 - pHome };
    const qsa = {};
    for (const s of STATES) for (const a of ACTIONS) {
      const future = STATES.reduce((sum, s2) => sum + P.transition[s][s2] * V0[s2], 0);
      qsa[s + "|" + a] = rewardOf(P, s, a) + P.gamma * future;
    }
    const q = {};
    for (const a of ACTIONS) q[a] = STATES.reduce((sum, s) => sum + belief[s] * qsa[s + "|" + a], 0);
    const action = q["Turn Off"] > q["Keep On"] ? "Turn Off" : "Keep On";   // tie → Keep On, as in Python max()
    const a = rewardOf(P, "Home", "Keep On") - rewardOf(P, "Empty", "Keep On"), b = rewardOf(P, "Empty", "Keep On");
    const c = rewardOf(P, "Home", "Turn Off") - rewardOf(P, "Empty", "Turn Off"), d = rewardOf(P, "Empty", "Turn Off");
    const threshold = (d - b) / (a - c);
    return { action, q, qsa, threshold };
  }

  // ------------------------------------------------------------ 4. day simulation
  /** Every hour of the day: sensor → Bayes → MDP. Outside the plan the prior is lower, and the
   *  agent can switch the heater ON when it sees the student. Unlisted hours = no motion. */
  function simulateDay(P, hours, sensor = P.sensorDay) {
    const rows = [];
    for (let h = 0; h < 24; h++) {
      const planned = hours.includes(h);
      const motion = h in sensor ? sensor[h] : false;
      const p = bayes(P, motion, planned ? P.prior : P.priorOffPlan).posterior;
      rows.push({ hour: h, planned, motion, pHome: p, action: mdp(P, p).action });
    }
    const onHours = rows.filter((r) => r.action === "Keep On").length;
    const planned = hours.length * costPerHour(P);
    const actual = onHours * costPerHour(P);
    return { rows, onHours, planned, actual, saved: planned - actual };
  }

  // ------------------------------------------------------------ bonus: 24-hour hill climbing
  function bonusCost(P, bits) {
    const energy = bits.reduce((s, b) => s + b, 0) * costPerHour(P);
    let discomfort = 0, switches = 0;
    for (let h = 0; h < 24; h++) {
      if (!bits[h]) discomfort += 70 * P.pHomeByHour[h] * P.outsideCold[h];
      if (bits[h] !== bits[(h + 23) % 24]) switches++;
    }
    return energy + discomfort + switches * P.switchCost;
  }

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function bonusHillClimbing(P, restarts = 10, seed = 42) {
    const rnd = mulberry32(seed);
    let bestBits = null, bestCost = Infinity;
    const results = [];
    for (let r = 0; r < restarts; r++) {
      let bits = Array.from({ length: 24 }, () => (rnd() < 0.5 ? 1 : 0));
      const start = bits.slice();
      let cost = bonusCost(P, bits), steps = 0;
      for (;;) {
        let bestNb = null, bestNbCost = Infinity;
        for (let h = 0; h < 24; h++) {
          const nb = bits.slice(); nb[h] ^= 1;
          const c = bonusCost(P, nb);
          if (c < bestNbCost) { bestNbCost = c; bestNb = nb; }
        }
        if (bestNbCost >= cost) break;
        bits = bestNb; cost = bestNbCost; steps++;
      }
      results.push({ restart: r + 1, steps, cost, start, bits });
      if (cost < bestCost) { bestCost = cost; bestBits = bits; }
    }
    return { bestBits, bestCost, results };
  }

  const api = { DEFAULTS, STATES, ACTIONS, costPerHour, scheduleCost, hillClimbing, bayes, mdp, simulateDay,
                bonusCost, bonusHillClimbing };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SmartDorm = api;
})(typeof window !== "undefined" ? window : globalThis);
