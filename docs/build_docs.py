"""Builds the Word documents in docs/: technical report, AI usage declaration, team contribution statement."""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ACCENT = RGBColor(0xD9, 0x62, 0x2B)
STUDENT = "Bolat Rauan"
GROUP = "Stream 2, Practice 2"
COURSE = "AIF1303 AI Fundamentals"
SITE = "https://rauanking.github.io/smart-dorm/"
REPO = "https://github.com/rauanking/smart-dorm"


def new_doc():
    d = Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2)
    st = d.styles["Normal"]
    st.font.name = "Calibri"; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    st.paragraph_format.space_after = Pt(6)
    for name, size in (("Heading 1", 16), ("Heading 2", 13)):
        h = d.styles[name]; h.font.name = "Cambria"; h.font.size = Pt(size); h.font.color.rgb = RGBColor(0x18, 0x21, 0x2D)
        h.element.rPr.rFonts.set(qn("w:eastAsia"), "Cambria")
    return d


def page_numbers(d):
    p = d.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tag); run._r.append(el)
        else:
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = text; run._r.append(el)


def para(d, text, bold_prefix=None, style=None):
    p = d.add_paragraph(style=style)
    if bold_prefix:
        p.add_run(bold_prefix).bold = True
    p.add_run(text)
    return p


def bullets(d, items):
    for it in items:
        if isinstance(it, tuple):
            para(d, it[1], bold_prefix=it[0], style="List Bullet")
        else:
            d.add_paragraph(it, style="List Bullet")


def code(d, text):
    for line in text.strip("\n").splitlines():
        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.6)
        r = p.add_run(line); r.font.name = "Consolas"; r.font.size = Pt(9.5)
    d.add_paragraph().paragraph_format.space_after = Pt(2)


def table(d, header, rows, widths=None):
    t = d.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
        t.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(10)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(d, path, caption, width=16):
    d.add_picture(path, width=Cm(width))
    d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = d.add_paragraph(caption); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.runs[0].italic = True; c.runs[0].font.size = Pt(9.5)


def title_block(d, title, subtitle):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title); r.bold = True; r.font.size = Pt(24); r.font.name = "Cambria"
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(subtitle); r.font.size = Pt(13); r.font.color.rgb = ACCENT
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{COURSE} · Final Project\n{STUDENT} · {GROUP} · individual project\nNovember 2026").font.size = Pt(11)


# =================================================================== technical report
d = new_doc(); page_numbers(d)
title_block(d, "Smart Dorm Energy Saver", "Technical Report")
p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run(f"Live demo: {SITE}\nRepository: {REPO}").font.size = Pt(10)

d.add_heading("Abstract", 1)
d.add_paragraph(
    "Smart Dorm Energy Saver is an AI agent that controls an electric heater in a student dormitory room. "
    "It combines three topics from the course into one pipeline. Hill climbing chooses the cheapest daily heating schedule. "
    "Bayesian inference turns a noisy motion-sensor reading into the probability that the student is home. "
    "A Markov decision process (one Bellman update) uses that probability to keep the heater on or turn it off. "
    "On a simulated winter day the agent heats for 5 hours instead of the planned 8, which lowers the cost from 300 tg to 187.5 tg (38% saved). "
    "The project includes a Python reference implementation, an interactive web application, 11 unit tests and 186 automatic checks that the web application matches the Python code.")

d.add_heading("1. Problem statement", 1)
d.add_paragraph(
    "In winter, many students in Astana dormitories heat their rooms with an electric heater of about 1.5 kW. "
    "At 25 tg per kWh this costs 37.5 tg per hour, or 900 tg per day if the heater runs all the time. Students are often away "
    "at lectures or asleep, so much of this energy heats an empty or unused room. Switching the heater off completely leaves the student cold. "
    "The problem has three parts:")
bullets(d, [
    "planning: how many hours a day to heat, given that more heating costs more but less heating is uncomfortable;",
    "sensing: a motion sensor is noisy, because a sleeping student does not move, so the room cannot be known to be empty for certain;",
    "deciding: the agent must act under that uncertainty, and the two possible mistakes have different costs.",
])

d.add_heading("2. Objectives", 1)
bullets(d, [
    ("O1. ", "Choose a daily heating schedule that balances electricity cost and comfort (local search)."),
    ("O2. ", "Estimate the probability that the student is home from one sensor reading (probabilistic reasoning)."),
    ("O3. ", "Decide whether to keep the heater on or turn it off, taking the different costs of mistakes into account (sequential decision making)."),
    ("O4. ", "Combine O1–O3 in one working application and measure the money saved."),
    ("O5. ", "Test every algorithm and make the results reproducible."),
])

d.add_heading("3. System overview", 1)
d.add_paragraph(
    "The three algorithms form one pipeline. The output of each step is the input of the next one:")
table(d, ["Step", "Algorithm (course topic)", "Input", "Output"], [
    ["1", "Hill climbing (search / local search)", "5 schedules, cost function", "Plan: heat 8 h/day (06–07, 17–22)"],
    ["2", "Bayes' rule (probabilistic reasoning)", "Prior, sensor model, sensor reading", "P(Home | no motion) = 0.321"],
    ["3", "MDP, one Bellman update (sequential decisions)", "Belief from step 2, rewards", "Turn Off (Q = +0.14 vs −0.79)"],
    ["4", "Day simulation", "Plan from step 1, hourly sensor readings", "5 h of heating, 112.5 tg saved"],
], widths=[1.2, 5, 4.6, 5.2])
figure(d, os.path.join(ROOT, "smart_dorm_overview.png"), "Figure 1. The three algorithms with default settings: hill-climbing path, Bayes posteriors and MDP Q-values.")

d.add_heading("4. AI topic 1: Hill climbing (local search)", 1)
d.add_heading("Why this algorithm", 2)
d.add_paragraph(
    "Choosing a schedule is an optimisation problem: only the best final schedule matters, not the path to it. "
    "Local search fits this kind of problem. Hill climbing keeps only the current solution and moves to a better neighbour. "
    "This matters for larger versions of the problem: a full 24-hour on/off schedule has 2²⁴ ≈ 16.8 million options, too many to check one by one (Section 8).")
d.add_heading("How it works", 2)
d.add_paragraph("Each candidate schedule s (hours of heating per day) has a cost, which the algorithm minimises:")
code(d, "cost(s) = s × 37.5 tg + discomfort(s)")
d.add_paragraph("The schedules are ordered 4, 6, 8, 10, 12 h, and the neighbours of a schedule are the one before and the one after. "
                "Steepest-descent hill climbing repeats two steps: look at all neighbours; move to the cheapest one if it is cheaper than the current schedule; otherwise stop.")
table(d, ["Hours", "Electricity, tg", "Discomfort, tg", "Total, tg"],
      [[4, 150, 400, 550], [6, 225, 200, 425], [8, 300, 90, "390 (best)"], [10, 375, 40, 415], [12, 450, 20, 470]], widths=[3, 4, 4, 4])
d.add_paragraph("Starting from 4 h: 550 → 425 (6 h) → 390 (8 h). The neighbours of 8 h cost 425 and 415, so the search stops. "
                "Starting from 12 h gives 470 → 415 → 390 and the same result. The output is the plan: heat 8 hours a day, at 06–07 and 17–22.")

d.add_heading("5. AI topic 2: Bayesian inference", 1)
d.add_heading("Why this algorithm", 2)
d.add_paragraph("The agent cannot see whether the student is home; it only receives a sensor reading, and the sensor makes mistakes. "
                "Bayes' rule is the standard way to update a belief when new evidence arrives, and it returns a probability instead of a hard yes or no.")
d.add_heading("How it works", 2)
code(d, "P(Home | obs) = P(obs | Home) · P(Home) / P(obs)\nP(obs) = P(obs | Home) · P(Home) + P(obs | Empty) · P(Empty)")
table(d, ["Quantity", "Value", "Meaning"], [
    ["Prior P(Home)", "0.60", "in heating hours the student is usually home"],
    ["P(no motion | Home)", "0.30", "the student sleeps or sits still at the laptop"],
    ["P(no motion | Empty)", "0.95", "an empty room rarely triggers the sensor (5% false triggers)"],
], widths=[4.5, 2, 9.5])
d.add_paragraph("For the reading “no motion for 30 minutes”: joint Home = 0.30 × 0.60 = 0.180, joint Empty = 0.95 × 0.40 = 0.380, "
                "evidence = 0.560, posterior P(Home | no motion) = 0.180 / 0.560 = 0.321. For “motion seen” the posterior is 0.42 / 0.44 = 0.955. "
                "One sensor reading therefore moves the belief from 60% to either 32% or 95.5%.")

d.add_heading("6. AI topic 3: Markov decision process", 1)
d.add_heading("Why this algorithm", 2)
d.add_paragraph("A probability alone does not say what to do. The two possible mistakes have different costs: a cold student is worse than a wasted hour of electricity. "
                "An MDP combines states, actions, rewards and probabilities, and it chooses the action with the highest expected value. The decision repeats every hour, which makes it sequential.")
d.add_heading("How it works", 2)
d.add_paragraph("States: Home, Empty. Actions: Keep On, Turn Off. Reward per hour:")
table(d, ["", "Home", "Empty"], [["Keep On", "+6 (warm student)", "−4 (wasted energy)"], ["Turn Off", "−8 (cold student)", "+4 (money saved)"]], widths=[3, 6, 6])
d.add_paragraph("Transitions for the next hour: Home→Home 0.8, Empty→Empty 0.7, γ = 0.9. One Bellman update starts from V₀ = 0, so the future term is zero, "
                "and the Q-value of an action equals its expected one-step reward under the Bayesian belief b:")
code(d, "Q(s, a) = R(s, a) + γ · Σ P(s'|s) · V0(s')        (V0 = 0)\nQ(a)    = Σ b(s) · Q(s, a)")
d.add_paragraph("With b(Home) = 0.321: Q(Keep On) = 0.321·6 + 0.679·(−4) = −0.79, and Q(Turn Off) = 0.321·(−8) + 0.679·4 = +0.14, so the agent turns the heater off. "
                "Setting both Q-values equal gives the decision threshold p* = 8/22 = 0.364: the heater stays on only when P(Home) is above 36.4%, not 50%, "
                "because freezing the student is penalised more than wasting energy.")

d.add_heading("7. Integration: one simulated day", 1)
d.add_paragraph("For every hour of the 8-hour plan, the sensor reading goes through Bayes and then the MDP. The table shows the default day.")
table(d, ["Hour", "Sensor", "P(Home)", "Action"], [
    ["06:00", "motion", "0.955", "Keep On"], ["07:00", "motion", "0.955", "Keep On"], ["17:00", "motion", "0.955", "Keep On"],
    ["18:00", "no motion", "0.321", "Turn Off"], ["19:00", "no motion", "0.321", "Turn Off"], ["20:00", "motion", "0.955", "Keep On"],
    ["21:00", "motion", "0.955", "Keep On"], ["22:00", "no motion", "0.321", "Turn Off"],
], widths=[3, 4, 3, 4])
d.add_paragraph("Result: 5 heating hours instead of 8. The cost falls from 300 tg to 187.5 tg (112.5 tg saved, 38%), about 3 375 tg per month.")

d.add_heading("8. Extension: 24-hour hill climbing with random restarts", 1)
d.add_paragraph("To show that hill climbing scales, the project also plans every hour of the day. A schedule is 24 on/off bits (2²⁴ ≈ 16.8 million options), "
                "and a neighbour flips one hour. The cost is energy + 70 × P(home at h) × coldness(h) for each hour the heater is off + 15 tg for each on/off switch. "
                "Steepest-descent hill climbing runs from 10 random starts, a standard defence against local optima. Each run needs only 9–17 moves. "
                "All restarts reached the same plan (heat 00–08 and 18–24, cost 692.2), so it is very likely the global optimum.")

d.add_heading("9. Implementation and user interface", 1)
table(d, ["Component", "File", "Role"], [
    ["Reference implementation", "smart_dorm.py", "All algorithms in Python; console demo"],
    ["Core logic for the web", "smartdorm.js", "The same algorithms as pure JavaScript functions"],
    ["User interface", "index.html, app.js", "Interactive web application (GitHub Pages)"],
    ["Notebook", "SmartDorm_Colab.ipynb", "Step-by-step version for Google Colab"],
    ["Tests", "tests/", "Unit tests and Python-vs-JavaScript consistency test"],
], widths=[4.5, 4.5, 7])
d.add_paragraph("The web application runs entirely in the browser, both online and offline, and has five panels:")
bullets(d, [
    ("Plan the day: ", "choose a starting schedule and watch hill climbing move along the cost curve step by step."),
    ("Is the student home?: ", "switch the sensor reading and move sliders for the prior and the sensor accuracy; every step of Bayes' rule is printed."),
    ("Keep on or turn off?: ", "edit the reward table and see the Q-values, the decision and the threshold update immediately."),
    ("One winter day: ", "presets (typical day, away all evening, home all day), or click any hour to flip its sensor reading; shows the cost and savings."),
    ("Bonus: ", "run 10 random restarts of 24-hour hill climbing."),
])
figure(d, os.path.join(HERE, "app_screenshot.png"), "Figure 2. Web application: the three algorithm panels.")

d.add_heading("10. Testing", 1)
table(d, ["Test", "What it checks", "Result"], [
    ["Hill climbing from 4 h and from 12 h", "Both starts reach 8 h, paths 4→6→8 and 12→10→8", "Pass"],
    ["Hill climbing = true minimum", "Result equals the minimum over all 5 schedules", "Pass"],
    ["Bayes posteriors", "0.321 for no motion, 0.955 for motion; P(Home) + P(Empty) = 1", "Pass"],
    ["MDP decisions", "Turn Off for no motion, Keep On for motion", "Pass"],
    ["MDP threshold", "Threshold = 8/22; decision flips just above and below it", "Pass"],
    ["Day simulation", "Planned 300 tg, actual 187.5 tg, 8 rows", "Pass"],
    ["24-hour bonus", "Valid 24-hour schedule, best cost among restarts", "Pass"],
    ["Consistency (186 checks)", "Web app equals Python for 6 parameter sets", "Pass"],
    ["User-interface check", "Every button, slider, preset and hour toggle; phone width without horizontal scroll; no console errors", "Pass"],
], widths=[4.5, 8.5, 2])
d.add_paragraph("The consistency test found one real bug. In the Python function bayes_home, the default prior was fixed when the function was defined, "
                "so changing the prior setting had no effect. The function now reads the setting at call time, and all 11 unit tests and 186 consistency checks pass.")

d.add_heading("11. Results", 1)
table(d, ["Scenario", "Plan alone", "With the agent", "Saved"], [
    ["Typical day (default sensor log)", "300 tg (8 h)", "187.5 tg (5 h)", "112.5 tg (38%)"],
    ["Student away all evening", "300 tg (8 h)", "75 tg (2 h)", "225 tg (75%)"],
    ["Student home all day", "300 tg (8 h)", "300 tg (8 h)", "0 tg (0%)"],
], widths=[6, 3.3, 3.5, 3.2])
d.add_paragraph("The agent saves money when the room is empty and does not switch the heater off when the student is clearly home, which is the intended behaviour. "
                "Sensitivity: if the penalty for a cold student rises from −8 to −20, the threshold drops from 36.4% to 23.5%, and the agent becomes more cautious.")

d.add_heading("12. Limitations and future work", 1)
bullets(d, [
    "All numbers are hypothetical toy-model assumptions, as the project guidelines allow. Real values would come from a smart meter and a sensor log.",
    "One motion sensor and one prior. A prior per hour of the day and more sensors (door, Wi-Fi presence) combined with Naive Bayes would make the belief more accurate.",
    "One Bellman update without room temperature. Full value iteration with heating dynamics would let the agent pre-heat the room before the student returns.",
    "The next step is a real ESP32 motion sensor and smart plug in a dorm room. This would suit a later IoT or embedded-systems course.",
])

d.add_heading("13. Conclusion", 1)
d.add_paragraph("The project shows how three course topics solve one practical problem together. Hill climbing makes the plan, Bayes estimates the hidden state from noisy evidence, "
                "and the MDP chooses an action that accounts for the different costs of mistakes. The application works online and offline, every algorithm is tested, "
                "and on a typical simulated day the agent cuts heating cost by 38%.")

d.add_heading("References", 1)
bullets(d, [
    "S. Russell, P. Norvig. Artificial Intelligence: A Modern Approach, 4th ed. Pearson, 2020 (local search, Bayes' rule, MDPs).",
    "AIF1303 AI Fundamentals lectures and practice sessions, weeks 1–10.",
])

d.add_heading("Appendix: AI usage and contribution", 1)
d.add_paragraph("See the separate documents AI_Usage_Declaration_Bolat_Rauan.docx and Team_Contribution_Statement_Bolat_Rauan.docx in the docs folder.")
d.save(os.path.join(HERE, "Smart_Dorm_Technical_Report_Bolat_Rauan.docx"))

# =================================================================== AI usage declaration
d = new_doc()
title_block(d, "AI Usage Declaration", "Smart Dorm Energy Saver")
d.add_paragraph(f"Course: {COURSE}, Final Project. Student: {STUDENT}. AI use was substantive and is declared here as the syllabus requires.")
table(d, ["Who / tool", "Role and contribution"], [
    [f"{STUDENT} (student)",
     "Chose the project topic (Mini Smart Home Energy Saver, adapted to a dorm heater) from the course topic list, after asking the assistant for several options and a detailed explanation of this one. "
     "Provided the assignment, the topic list and the deliverables. Decided on an individual project, an interactive web demo, a PowerPoint deck, and an AI-narrated demo video. "
     "Created the GitHub repository and authorised the upload. Reviewed the results and is responsible for explaining every algorithm at the defense."],
    ["Claude (Anthropic), via Claude Code, November 2026",
     "Proposed the project options and the integration of the three algorithms. Wrote the Python implementation, the tests, the Colab notebook, the JavaScript port and the web interface. "
     "Drafted this report, the slides and the video script, chose the toy-model numbers, ran all tests, and prepared Russian-language explanations for defense preparation."],
    ["Microsoft Edge neural text-to-speech, November 2026", "Read the English narration of the demo video."],
], widths=[4.5, 11.5])
d.add_heading("Key prompts", 2)
bullets(d, [
    "“Here is the final project task and the topic list; first propose an idea, a plan and questions.” (original prompts were written in Russian)",
    "“Give me many project options.” → the student chose option 7 (Smart Dorm).",
    "“Explain option 7 in more detail and check that it covers the required categories.”",
    "“Here are the required deliverables and grading; look and tell me what we do.”",
])
d.add_heading("How the work was verified", 2)
bullets(d, [
    "Every number in the report was recomputed by the code; 11 unit tests pass.",
    "186 automatic checks confirm that the web application gives the same results as the Python code for 6 parameter sets. This test found and fixed one bug.",
    "The user interface was tested by script (every button, slider and preset, phone width) with no console errors.",
    "Definitions follow Russell & Norvig, Artificial Intelligence: A Modern Approach, and the course lectures.",
])
p = d.add_paragraph(); p.add_run("Student statement. ").bold = True
p.add_run(f"I confirm that I am responsible for the final work and have accurately disclosed the use of AI. — {STUDENT}")
d.save(os.path.join(HERE, "AI_Usage_Declaration_Bolat_Rauan.docx"))

# =================================================================== team contribution statement
d = new_doc()
title_block(d, "Team Contribution Statement", "Smart Dorm Energy Saver")
d.add_paragraph(f"This is an individual project. The team has one member: {STUDENT} ({GROUP}).")
table(d, ["Member", "Contribution", "Share"], [
    [STUDENT,
     "Project choice and scope; requirements and deliverables; direction of the AI assistant; review of the code, results and documents; "
     "GitHub repository and publishing; presentation and live demo; oral defense.", "100%"],
], widths=[3.5, 10.5, 2])
d.add_paragraph("Use of an AI assistant (Claude) for code and documents is disclosed in the AI Usage Declaration.")
p = d.add_paragraph(); p.add_run("Signature: ").bold = True; p.add_run(f"{STUDENT}")
d.save(os.path.join(HERE, "Team_Contribution_Statement_Bolat_Rauan.docx"))
print("docs written")
