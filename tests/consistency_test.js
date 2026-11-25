// Checks that smartdorm.js (web app) gives the same results as smart_dorm.py.
// Run:  python tests/make_reference.py  &&  node tests/consistency_test.js
const SD = require("../smartdorm.js");
const ref = require("./reference.json");
const close = (a, b) => Math.abs(a - b) < 1e-9;
let checks = 0, fails = 0;
const check = (ok, msg) => { checks++; if (!ok) { fails++; console.log("FAIL", msg); } };

ref.forEach((r, n) => {
  const P = JSON.parse(JSON.stringify(SD.DEFAULTS));
  const c = r.case;
  if ("PRIOR_HOME" in c) P.prior = c.PRIOR_HOME;
  if ("P_NOMOTION_IF_HOME" in c) P.pNoMotionHome = c.P_NOMOTION_IF_HOME;
  if ("P_NOMOTION_IF_EMPTY" in c) P.pNoMotionEmpty = c.P_NOMOTION_IF_EMPTY;
  if ("DISCOMFORT" in c) P.discomfort = c.DISCOMFORT;
  if ("REWARD" in c) P.reward = c.REWARD;

  for (const [s, [best, trace]] of Object.entries(r.hill)) {
    const js = SD.hillClimbing(P, +s);
    check(js.best === best && JSON.stringify(js.trace) === JSON.stringify(trace), `case ${n} hill start ${s}`);
  }
  for (const [m, b] of Object.entries(r.bayes)) {
    const js = SD.bayes(P, m === "True");
    for (const [k, pk] of [["posterior", "posterior"], ["evidence", "evidence"], ["jointHome", "joint_home"], ["jointEmpty", "joint_empty"]])
      check(close(js[k], b[pk]), `case ${n} bayes ${m} ${k}`);
  }
  for (const [p, m] of Object.entries(r.mdp)) {
    const js = SD.mdp(P, +p);
    check(js.action === m.action, `case ${n} mdp p=${p} action ${js.action} vs ${m.action}`);
    check(close(js.q["Keep On"], m.q["Keep On"]) && close(js.q["Turn Off"], m.q["Turn Off"]), `case ${n} mdp p=${p} Q`);
    check(close(js.threshold, m.threshold), `case ${n} mdp threshold`);
  }
  const best = SD.hillClimbing(P).best;
  const day = SD.simulateDay(P, P.hoursOf[best]);
  check(best === r.day.best && close(day.planned, r.day.planned) && close(day.actual, r.day.actual), `case ${n} day totals`);
  check(JSON.stringify(day.rows.map((x) => x.action)) === JSON.stringify(r.day.actions), `case ${n} day actions`);
  const home12 = {}; for (let h = 10; h < 22; h++) home12[h] = true;
  const d12 = SD.simulateDay(P, P.hoursOf[best], home12);
  check(close(d12.actual, r.day.home12_actual), `case ${n} home-12h total`);
  check(JSON.stringify(d12.rows.map((x) => x.action)) === JSON.stringify(r.day.home12_actions), `case ${n} home-12h actions`);
  check(Math.abs(SD.bonusHillClimbing(P).bestCost - r.bonus_best) < 1e-6, `case ${n} bonus optimum`);
});
console.log(`${checks - fails}/${checks} checks passed (${ref.length} parameter sets)`);
process.exit(fails ? 1 : 0);
