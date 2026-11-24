"""
Demo video for Smart Dorm Energy Saver:
  1) AI narration with Microsoft Edge neural TTS (edge-tts),
  2) screen recording of the real web app (Playwright + Edge), actions timed to the narration,
  3) ffmpeg: narration placed at the recorded offsets + burned-in subtitles.
Run: python docs/video/make_video.py
"""
import asyncio
import json
import os
import re
import subprocess
import time

import edge_tts
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(HERE, "work")
os.makedirs(WORK, exist_ok=True)
FF = r"C:\Users\admin\SilkRoad_P1\tools\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe"
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
VOICE = "en-US-AndrewNeural"
OUT = os.path.join(os.path.dirname(HERE), "Smart_Dorm_Demo_Video_Bolat_Rauan.mp4")

SEGMENTS = [
    ("intro", "This is Smart Dorm Energy Saver, my final project for AI Fundamentals. In winter, students in Astana dorms use electric heaters. "
              "Running one all day costs about nine hundred tenge, and often the room is empty. "
              "My agent combines three AI topics to heat the room only when the student is there."),
    ("hill", "Step one is hill climbing. Each daily schedule has a cost: electricity plus a discomfort penalty. "
             "The search starts at four hours and moves to the cheaper neighbour: five hundred fifty, four hundred twenty-five, then three hundred ninety tenge. "
             "Both neighbours of eight hours are more expensive, so it stops. The plan is to heat eight hours a day."),
    ("bayes", "Step two is Bayes' rule. During a planned hour, the motion sensor sees nothing for thirty minutes. "
              "But a sleeping student does not move either, so the agent cannot be sure. "
              "Bayes combines the prior of sixty percent with the sensor model, and the probability that the student is home drops to thirty-two percent. "
              "If the sensor sees motion, it rises to ninety-five percent."),
    ("mdp", "Step three is a Markov decision process. A cold student costs minus eight points, while heating an empty room costs minus four. "
            "Weighted by the belief from Bayes, turning off scores plus zero point one four, and keeping on scores minus zero point seven nine, so the agent turns the heater off. "
            "If I make a cold student cost minus twenty, the threshold drops, and the agent becomes more careful."),
    ("day", "Now the whole day. For each planned hour, the sensor reading goes through Bayes and then the MDP. "
            "On a typical day, the heater runs five hours instead of eight, saving thirty-eight percent, about three thousand four hundred tenge a month. "
            "If the student is away all evening, it saves seventy-five percent. If the student is home all day, it saves nothing, which is exactly right."),
    ("bonus", "As a bonus, hill climbing plans all twenty-four hours, which is about sixteen million possible schedules. "
              "Ten random restarts protect against local optima."),
    ("outro", "The project has eleven unit tests, and one hundred eighty-six checks that the web app matches the Python code. "
              "The code and the live demo are on GitHub. Thank you."),
]

# subtitle text (digits instead of spoken numbers), same sentences as the narration
SUBS = {
    "intro": ["This is Smart Dorm Energy Saver, my final project for AI Fundamentals.",
              "In winter, students in Astana dorms use electric heaters.",
              "Running one all day costs about 900 tg, and often the room is empty.",
              "My agent combines three AI topics to heat the room only when the student is there."],
    "hill": ["Step 1 is hill climbing.", "Each daily schedule has a cost: electricity plus a discomfort penalty.",
             "The search starts at 4 h and moves to the cheaper neighbour: 550 → 425 → 390 tg.",
             "Both neighbours of 8 h are more expensive, so it stops.", "The plan is to heat 8 hours a day."],
    "bayes": ["Step 2 is Bayes' rule.", "During a planned hour, the motion sensor sees nothing for 30 minutes.",
              "But a sleeping student does not move either, so the agent cannot be sure.",
              "Bayes combines the 60% prior with the sensor model: P(student is home) drops to 32%.",
              "If the sensor sees motion, it rises to 95%."],
    "mdp": ["Step 3 is a Markov decision process.", "A cold student costs −8 points, heating an empty room costs −4.",
            "Weighted by the belief from Bayes: Turn Off +0.14, Keep On −0.79, so the agent turns the heater off.",
            "If a cold student costs −20, the threshold drops, and the agent becomes more careful."],
    "day": ["Now the whole day.", "For each planned hour, the sensor reading goes through Bayes and then the MDP.",
            "Typical day: 5 heating hours instead of 8, 38% saved, about 3 400 tg a month.",
            "Away all evening: 75% saved.", "Home all day: nothing saved, which is exactly right."],
    "bonus": ["Bonus: hill climbing plans all 24 hours, about 16 million possible schedules.",
              "Ten random restarts protect against local optima."],
    "outro": ["11 unit tests, and 186 checks that the web app matches the Python code.",
              "The code and the live demo are on GitHub. Thank you."],
}


def dur(path):
    return float(subprocess.check_output([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())


# ---------------------------------------------------------------- 1. narration
async def tts():
    for name, text in SEGMENTS:
        await edge_tts.Communicate(text, VOICE, rate="+0%").save(os.path.join(WORK, f"{name}.mp3"))

asyncio.run(tts())
D = {name: dur(os.path.join(WORK, f"{name}.mp3")) for name, _ in SEGMENTS}
print("narration seconds:", {k: round(v, 1) for k, v in D.items()}, "total", round(sum(D.values()), 1))

# ---------------------------------------------------------------- 2. screen recording
GAP = 0.6
url = "file:///" + os.path.join(ROOT, "index.html").replace("\\", "/")
starts = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=WORK, record_video_size={"width": 1280, "height": 720})
    t0 = time.time()
    pg = ctx.new_page()
    pg.goto(url)
    pg.add_style_tag(content=".card.focus{box-shadow:0 0 0 3px #d9622b; transition: box-shadow .3s} html{scroll-behavior:smooth}")
    pg.wait_for_timeout(1200)

    def focus(selector):
        pg.evaluate("""s => { document.querySelectorAll('.card').forEach(c => c.classList.remove('focus'));
                              if (s) document.querySelector(s).closest('.card').classList.add('focus'); }""", selector)

    def scroll(y):
        pg.evaluate(f"window.scrollTo(0, {y})")

    def seg(name, actions):
        """actions: list of (fraction of the segment, callable)."""
        starts[name] = time.time() - t0
        end = starts[name] + D[name]
        for frac, fn in actions:
            target = starts[name] + frac * D[name]
            wait = target - (time.time() - t0)
            if wait > 0:
                pg.wait_for_timeout(wait * 1000)
            fn()
        rest = end + GAP - (time.time() - t0)
        if rest > 0:
            pg.wait_for_timeout(rest * 1000)

    y_day = pg.evaluate("document.getElementById('h4t').getBoundingClientRect().top + window.scrollY - 20")
    y_bonus = pg.evaluate("document.getElementById('h5t').getBoundingClientRect().top + window.scrollY - 20")

    seg("intro", [(0.0, lambda: scroll(0))])
    seg("hill", [(0.0, lambda: (scroll(150), focus("#h1t"))), (0.35, lambda: pg.click("#hcRun"))])
    seg("bayes", [(0.0, lambda: focus("#h2t")), (0.82, lambda: pg.click("#obsYes")), (0.98, lambda: pg.click("#obsNo"))])

    def set_cold(v):
        pg.fill("#rHO", str(v)); pg.dispatch_event("#rHO", "input")
    seg("mdp", [(0.0, lambda: focus("#h3t")), (0.78, lambda: set_cold(-20)), (0.99, lambda: set_cold(-8))])
    seg("day", [(0.0, lambda: (focus("#h4t"), scroll(y_day))), (0.71, lambda: pg.click("#pAway")),
                (0.86, lambda: pg.click("#pHome")), (0.995, lambda: pg.click("#pTypical"))])
    seg("bonus", [(0.0, lambda: (focus("#h5t"), scroll(y_bonus))), (0.55, lambda: pg.click("#bonusRun"))])
    seg("outro", [(0.0, lambda: (focus(None), scroll(0)))])
    pg.wait_for_timeout(1000)
    total = time.time() - t0
    video = pg.video.path()
    ctx.close(); b.close()
print("recorded", round(total, 1), "s; segment starts", {k: round(v, 1) for k, v in starts.items()})

# ---------------------------------------------------------------- 3. subtitles + mix
def ts(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"

ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1280", "PlayResY: 720", "WrapStyle: 0", "", "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
       "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Sub,Segoe UI Semibold,30,&H00FFFFFF,&H00FFFFFF,&H60000000,&H60000000,0,0,0,0,100,100,0,0,3,10,0,2,120,120,36,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for name, _ in SEGMENTS:
    lines = SUBS[name]
    weights = [len(re.sub(r"\W", "", l)) + 8 for l in lines]
    t = starts[name]
    for line, w in zip(lines, weights):
        d = D[name] * w / sum(weights)
        ass.append(f"Dialogue: 0,{ts(t)},{ts(t + d - 0.05)},Sub,,0,0,0,,{line}")
        t += d
open(os.path.join(WORK, "subs.ass"), "w", encoding="utf-8-sig").write("\n".join(ass) + "\n")

inputs, filters = ["-i", video], []
for i, (name, _) in enumerate(SEGMENTS, start=1):
    inputs += ["-i", os.path.join(WORK, f"{name}.mp3")]
    ms = int(starts[name] * 1000)
    filters.append(f"[{i}:a]adelay={ms}|{ms},apad[a{i}]")
mix = "".join(f"[a{i}]" for i in range(1, len(SEGMENTS) + 1))
filters.append(f"{mix}amix=inputs={len(SEGMENTS)}:normalize=0,loudnorm=I=-16:TP=-1.5[aout]")
filters.append("[0:v]subtitles=subs.ass,fade=t=in:st=0:d=0.5[vout]")
subprocess.run([FF, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
                "-t", f"{total:.2f}", "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT], check=True, cwd=WORK)
json.dump({"starts": starts, "durations": D, "total": total}, open(os.path.join(WORK, "timing.json"), "w"), indent=1)
print("video:", OUT, round(dur(OUT), 1), "s")
