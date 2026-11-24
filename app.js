/* Smart Dorm Energy Saver — user interface. All AI logic lives in smartdorm.js. */
(function () {
  "use strict";
  const SD = window.SmartDorm;
  const P = JSON.parse(JSON.stringify(SD.DEFAULTS));
  const $ = (id) => document.getElementById(id);
  const f2 = (x) => x.toFixed(2), f3 = (x) => x.toFixed(3), pct = (x) => (x * 100).toFixed(1) + "%";
  const tg = (x) => (Number.isInteger(Math.round(x * 10) / 10) ? Math.round(x).toLocaleString("en") : (Math.round(x * 10) / 10).toLocaleString("en", { minimumFractionDigits: 1 })).replace(/,/g, " ") + " tg";
  const sg = (v) => (v < 0 ? "(" + v + ")" : String(v));
  const hh = (h) => String(h).padStart(2, "0") + ":00";
  const state = { motion: false, hcShown: null, sensor: { ...P.sensorDay }, timer: null };

  // ------------------------------------------------------------ 1. hill climbing
  P.schedules.forEach((h, i) => $("hcStart").insertAdjacentHTML("beforeend", `<option value="${i}">${h} h/day</option>`));

  function drawHill(trace, upto) {
    const W = 360, H = 190, L = 44, R = 24, T = 14, B = 30;
    const S = P.schedules, costs = S.map((h) => SD.scheduleCost(P, h));
    const lo = Math.floor((Math.min(...costs) - 40) / 50) * 50, hi = Math.ceil((Math.max(...costs) + 20) / 50) * 50;
    const x = (h) => L + ((h - S[0]) / (S[S.length - 1] - S[0])) * (W - L - R);
    const y = (c) => T + (1 - (c - lo) / (hi - lo)) * (H - T - B);
    let s = "";
    for (let c = lo; c <= hi; c += 50) s += `<line x1="${L}" x2="${W - R}" y1="${y(c)}" y2="${y(c)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(c) + 4}" text-anchor="end">${c}</text>`;
    s += `<polyline fill="none" stroke="var(--idle)" stroke-width="2" points="${S.map((h) => x(h) + "," + y(SD.scheduleCost(P, h))).join(" ")}"/>`;
    S.forEach((h) => { s += `<circle cx="${x(h)}" cy="${y(SD.scheduleCost(P, h))}" r="5" fill="var(--card)" stroke="var(--muted)" stroke-width="2"/><text x="${x(h)}" y="${H - 10}" text-anchor="middle">${h} h</text>`; });
    const path = trace.slice(0, upto + 1);
    if (path.length > 1) s += `<polyline fill="none" stroke="var(--heat)" stroke-width="3" points="${path.map((h) => x(h) + "," + y(SD.scheduleCost(P, h))).join(" ")}"/>`;
    const cur = path[path.length - 1];
    s += `<circle cx="${x(cur)}" cy="${y(SD.scheduleCost(P, cur))}" r="9" fill="var(--heat)"/>`;
    s += `<text x="${x(cur)}" y="${y(SD.scheduleCost(P, cur)) - 14}" text-anchor="middle" style="fill:var(--ink);font-weight:600">${Math.round(SD.scheduleCost(P, cur))} tg</text>`;
    $("hcChart").innerHTML = s;
  }

  function showHill(res, upto) {
    drawHill(res.trace, upto);
    $("hcLog").innerHTML = res.log.slice(0, upto + 1).map((e) =>
      `<li>at ${e.at} h (${Math.round(e.cost)}) · neighbours ${e.neighbours.map((n) => `${n.hours} h = ${Math.round(n.cost)}`).join(", ")} → ${e.moveTo ? "move to " + e.moveTo + " h" : "<b>stop</b>"}</li>`).join("");
    const done = upto >= res.log.length - 1;
    const best = res.trace[Math.min(upto, res.trace.length - 1)];
    $("hcOut").innerHTML = done
      ? `Plan: heat <span class="big">${res.best} h/day</span> · cost ${tg(SD.scheduleCost(P, res.best))}<small>Hours: ${P.hoursOf[res.best].map(hh).join(", ")}</small>`
      : `Searching… now at ${best} h<small>&nbsp;</small>`;
  }

  function runHill(animate) {
    clearInterval(state.timer);
    const res = SD.hillClimbing(P, +$("hcStart").value);
    if (!animate) { showHill(res, res.log.length - 1); return; }
    let k = 0;
    showHill(res, k);
    state.timer = setInterval(() => { k++; showHill(res, k); if (k >= res.log.length - 1) clearInterval(state.timer); }, 800);
  }
  $("hcRun").addEventListener("click", () => runHill(true));
  $("hcStart").addEventListener("change", () => runHill(false));

  // ------------------------------------------------------------ 2. Bayes + 3. MDP
  const sliders = [["prior", "prior"], ["lh", "pNoMotionHome"], ["le", "pNoMotionEmpty"]];
  sliders.forEach(([id, key]) => {
    $(id).value = P[key];
    $(id).addEventListener("input", () => { P[key] = +$(id).value; renderAll(); });
  });
  const rewards = [["rHK", "homeKeep"], ["rEK", "emptyKeep"], ["rHO", "homeOff"], ["rEO", "emptyOff"]];
  rewards.forEach(([id, key]) => {
    $(id).value = P.reward[key];
    $(id).addEventListener("input", () => { const v = parseFloat($(id).value); if (Number.isFinite(v)) { P.reward[key] = v; renderAll(); } });
  });
  function setObs(m) { state.motion = m; $("obsYes").setAttribute("aria-pressed", m); $("obsNo").setAttribute("aria-pressed", !m); renderAll(); }
  $("obsYes").addEventListener("click", () => setObs(true));
  $("obsNo").addEventListener("click", () => setObs(false));

  function renderBayesMdp() {
    sliders.forEach(([id, key]) => { $(id + "V").textContent = f2(P[key]); });
    const obs = state.motion ? "motion" : "no motion";
    const b = SD.bayes(P, state.motion);
    $("bayesCalc").innerHTML =
      `Prior:       P(Home) = ${f2(b.prior)}
` +
      `Likelihood:  P(${obs} | Home)  = ${f2(b.likeHome)}
` +
      `             P(${obs} | Empty) = ${f2(b.likeEmpty)}
` +
      `Home:   ${f2(b.likeHome)} × ${f2(b.prior)} = ${f3(b.jointHome)}
` +
      `Empty:  ${f2(b.likeEmpty)} × ${f2(1 - b.prior)} = ${f3(b.jointEmpty)}
` +
      `P(${obs}) = ${f3(b.jointHome)} + ${f3(b.jointEmpty)} = ${f3(b.evidence)}
` +
      `P(Home | ${obs}) = ${f3(b.jointHome)} / ${f3(b.evidence)} = <b>${f3(b.posterior)}</b>`;
    $("bayesOut").innerHTML = `P(student is home) = <span class="big">${pct(b.posterior)}</span><small>was ${pct(b.prior)} before the sensor reading</small>`;

    const m = SD.mdp(P, b.posterior), p = b.posterior, r = P.reward;
    $("mdpCalc").innerHTML =
      `b(Home) = ${f3(p)}  (from step 2)
` +
      `γ = ${P.gamma}, V0 = 0  → future term is 0
` +
      `Q(Keep On)  = ${f3(p)}×${sg(r.homeKeep)} + ${f3(1 - p)}×${sg(r.emptyKeep)}
             = <b>${f2(m.q["Keep On"])}</b>
` +
      `Q(Turn Off) = ${f3(p)}×${sg(r.homeOff)} + ${f3(1 - p)}×${sg(r.emptyOff)}
             = <b>${f2(m.q["Turn Off"])}</b>`;
    const span = Math.max(1, ...SD.ACTIONS.map((a) => Math.abs(m.q[a])));
    $("qbars").innerHTML = SD.ACTIONS.map((a) => {
      const v = m.q[a], w = (Math.abs(v) / span) * 50;
      const color = a === "Keep On" ? "var(--heat)" : "var(--cold)";
      return `<div class="qbar"><span>${a}</span><div class="track"><div class="zero"></div><div class="fill" style="background:${color};${v >= 0 ? "left:50%" : "right:50%"};width:${w}%"></div></div><span class="v">${v >= 0 ? "+" : ""}${f2(v)}</span></div>`;
    }).join("");
    const thrOk = Number.isFinite(m.threshold) && m.threshold > 0 && m.threshold < 1;
    $("mdpOut").className = "out" + (m.action === "Turn Off" ? " off" : "");
    $("mdpOut").innerHTML = `Decision: <span class="big">${m.action.toUpperCase()}</span><small>${thrOk
      ? `Keep On wins only when P(Home) > ${pct(m.threshold)}; now ${pct(p)}`
      : "With these rewards one action always wins, whatever the probability"}</small>`;
  }

  // ------------------------------------------------------------ 4. day simulation
  const PRESETS = {
    pTypical: () => ({ ...P.sensorDay }),
    pAway: () => { const s = {}; for (let h = 0; h < 24; h++) s[h] = h < 9; return s; },
    pHome: () => { const s = {}; for (let h = 0; h < 24; h++) s[h] = true; return s; },
  };
  Object.keys(PRESETS).forEach((id) => $(id).addEventListener("click", () => { state.sensor = PRESETS[id](); renderDay(); }));

  function renderDay() {
    const best = SD.hillClimbing(P).best, plan = P.hoursOf[best];
    const day = SD.simulateDay(P, plan, state.sensor);
    const byHour = Object.fromEntries(day.rows.map((r) => [r.hour, r]));
    let cells = "";
    for (let h = 0; h < 24; h++) {
      const r = byHour[h], motion = h in state.sensor ? state.sensor[h] : true;
      const cls = r ? (r.action === "Keep On" ? "on" : "off") : "";
      const label = `${hh(h)}, ${motion ? "motion" : "no motion"}${r ? ", " + r.action : ", not planned"}. Click to flip the sensor.`;
      cells += `<button class="hour ${cls}" data-h="${h}" aria-label="${label}" title="${label}"><span>${h}</span><span class="st"></span><span class="sn">${motion ? "●" : "○"}</span></button>`;
    }
    $("hours").innerHTML = cells;
    $("hours").querySelectorAll(".hour").forEach((el) => el.addEventListener("click", () => {
      const h = +el.dataset.h; const cur = h in state.sensor ? state.sensor[h] : true;
      state.sensor = { ...state.sensor, [h]: !cur }; renderDay();
    }));
    $("tiles").innerHTML =
      `<div class="tile"><b>${best} h</b><span>plan from hill climbing</span></div>` +
      `<div class="tile"><b>${tg(day.planned)}</b><span>plan alone (${plan.length} h)</span></div>` +
      `<div class="tile"><b>${tg(day.actual)}</b><span>with the agent (${day.onHours} h)</span></div>` +
      `<div class="tile save"><b>${tg(day.saved)}</b><span>saved today${day.planned ? " (" + Math.round((day.saved / day.planned) * 100) + "%)" : ""} · ≈ ${tg(day.saved * 30)} per month</span></div>`;
    $("dayTable").innerHTML = `<thead><tr><th>Hour</th><th>Sensor</th><th class="n">P(Home)</th><th class="n">Q(Keep On)</th><th class="n">Q(Turn Off)</th><th>Action</th></tr></thead><tbody>` +
      day.rows.map((r) => { const m = SD.mdp(P, r.pHome); return `<tr><td>${hh(r.hour)}</td><td>${r.motion ? "motion" : "no motion"}</td><td class="n">${f3(r.pHome)}</td><td class="n">${f2(m.q["Keep On"])}</td><td class="n">${f2(m.q["Turn Off"])}</td><td><b style="color:${r.action === "Keep On" ? "var(--heat)" : "var(--cold)"}">${r.action}</b></td></tr>`; }).join("") + "</tbody>";
  }

  // ------------------------------------------------------------ bonus
  let bonusSeed = 42;
  function renderBonus() {
    const res = SD.bonusHillClimbing(P, 10, bonusSeed);
    $("bonusSeed").textContent = `random seed ${bonusSeed}`;
    const bits = (b) => `<div class="bits">${b.map((v) => `<i class="${v ? "on" : ""}"></i>`).join("")}</div>`;
    $("bonusTable").innerHTML = `<thead><tr><th>Restart</th><th>Random start (00 → 23 h)</th><th>Local optimum</th><th class="n">Moves</th><th class="n">Cost</th></tr></thead><tbody>` +
      res.results.map((r) => `<tr class="${r.cost === res.bestCost ? "best" : ""}"><td>${r.restart}</td><td style="min-width:160px">${bits(r.start)}</td><td style="min-width:160px">${bits(r.bits)}</td><td class="n">${r.steps}</td><td class="n">${r.cost.toFixed(1)}</td></tr>`).join("") + "</tbody>";
    const distinct = [...new Set(res.results.map((r) => r.cost.toFixed(1)))];
    const on = res.bestBits.map((v, h) => (v ? h : -1)).filter((h) => h >= 0);
    $("bonusOut").innerHTML = `Best 24-hour plan: ${on.length} heating hours, cost ${res.bestCost.toFixed(1)} tg` +
      `<small>${distinct.length === 1 ? "All 10 restarts reached the same plan, so it is very likely the global optimum." : `Restarts stopped in ${distinct.length} different local optima, so the restarts were needed.`}</small>`;
  }
  $("bonusRun").addEventListener("click", () => { bonusSeed = Math.floor(Math.random() * 100000); renderBonus(); });

  function renderAll() { renderBayesMdp(); renderDay(); }
  runHill(false);
  renderAll();
  renderBonus();
})();
