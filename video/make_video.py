#!/usr/bin/env python3
"""Render the Closeout demo video.

Captioned, no voice-over: the machine has no TTS worth listening to, and a
synthetic voice reads worse than clean type. Every terminal frame in here
is real output from scripts/demo.sh, not a mock-up.
"""
from __future__ import annotations
import subprocess, textwrap, pathlib, shutil

W, H, FPS = 1920, 1080, 30
OUT = pathlib.Path(__file__).resolve().parent
FRAMES = OUT / "frames"

BG      = (13, 17, 23)
PANEL   = (22, 27, 34)
FG      = (230, 237, 243)
DIM     = (125, 139, 153)
ACCENT  = (88, 166, 255)
RED     = (248, 113, 113)
GREEN   = (126, 231, 135)
AMBER   = (240, 180, 90)

from PIL import Image, ImageDraw, ImageFont
F = "/usr/share/fonts/truetype/dejavu/"
def font(name, size): return ImageFont.truetype(F + name, size)
H1   = font("DejaVuSans-Bold.ttf", 68)
H2   = font("DejaVuSans-Bold.ttf", 46)
BODY = font("DejaVuSans.ttf", 36)
SMALL= font("DejaVuSans.ttf", 28)
MONO = font("DejaVuSansMono.ttf", 26)
MONOB= font("DejaVuSansMono.ttf", 32)

shots: list[tuple[Image.Image, float]] = []

def new():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)

def wrap(d, text, xy, f, fill, width, leading=1.45):
    x, y = xy
    for para in text.split("\n"):
        if not para.strip():
            y += int(f.size * leading * 0.6); continue
        for line in textwrap.wrap(para, width=width):
            d.text((x, y), line, font=f, fill=fill)
            y += int(f.size * leading)
    return y

def hold(img, seconds): shots.append((img, seconds))

def footer(d, text="closeout"):
    d.text((80, H - 70), text, font=SMALL, fill=(70, 80, 92))

# ---------------------------------------------------------------- 1. title
img, d = new()
d.text((120, 330), "Closeout", font=font("DejaVuSans-Bold.ttf", 130), fill=FG)
d.text((124, 500), "A product recall is closed by reconciliation,", font=H2, fill=ACCENT)
d.text((124, 560), "never by assertion.", font=H2, fill=ACCENT)
d.text((124, 680), "An agent that refuses to close a recall while", font=BODY, fill=DIM)
d.text((124, 730), "product is still in the market.", font=BODY, fill=DIM)
d.text((124, 860), "Flip the Switch  ·  Track 01", font=SMALL, fill=(90, 100, 112))
hold(img, 5)

# ------------------------------------------------------- 2. the real record
img, d = new()
d.text((120, 110), "This is a real FDA recall", font=H1, fill=FG)
d.rounded_rectangle([120, 240, W - 120, 700], 14, fill=PANEL)
rows = [
    ("recall_number",   "D-1572-2020", FG),
    ("classification",  "Class I", RED),
    ("product_quantity","9600 bottles", FG),
    ("distribution",    "Nationwide", FG),
    ("reason",          "labeled to contain 0.56% methanol", FG),
    ("status",          "Terminated", AMBER),
]
y = 290
for k, v, c in rows:
    d.text((170, y), f"{k:<18}", font=MONO, fill=DIM)
    d.text((170 + 330, y), v, font=MONOB if c is not FG else MONO, fill=c)
    y += 66
d.text((120, 760), "Class I means a reasonable probability of death.", font=BODY, fill=DIM)
d.text((120, 820), "Terminated means closed.", font=BODY, fill=AMBER)
footer(d); hold(img, 9)

# ------------------------------------------------------------ 3. the question
img, d = new()
d.text((120, 300), "So how many of the", font=H1, fill=DIM)
d.text((120, 390), "9,600 bottles came back?", font=H1, fill=FG)
d.text((120, 560), "The record does not say.", font=H2, fill=RED)
d.text((120, 650), "There is no field in it that could.", font=H2, fill=RED)
footer(d); hold(img, 7)

# ------------------------------------------------------------- 4. the survey
img, d = new()
d.text((120, 110), "Not an outlier. I measured it.", font=H1, fill=FG)
d.rounded_rectangle([120, 250, W - 120, 640], 14, fill=PANEL)
d.text((170, 295), "$ python3 scripts/survey_recalls.py", font=MONO, fill=GREEN)
lines = [
    ("  records sampled                   : 3000", DIM),
    ("  state a numeric quantity shipped  : 2606 (86.9%)", FG),
    ("  distinct fields across the sample : 25", DIM),
    ("  fields that could carry how much came back: NONE", RED),
]
y = 370
for t, c in lines:
    d.text((170, y), t, font=MONO, fill=c); y += 56
d.text((120, 700), "86.9% say how much went out.", font=H2, fill=FG)
d.text((120, 770), "None can say how much came back.", font=H2, fill=RED)
d.text((120, 860), "That is not missing data. It is a missing concept.", font=BODY, fill=DIM)
footer(d); hold(img, 10)

# ------------------------------------------------------- 5. why it needs Switch
img, d = new()
d.text((120, 90), "Why this needs Switch", font=H1, fill=FG)
d.text((120, 190), "A recall is several organisations who must not see each other's books.", font=BODY, fill=DIM)

def room(x, y, w, h, title, sub, colour):
    d.rounded_rectangle([x, y, x + w, y + h], 14, fill=PANEL, outline=colour, width=3)
    d.text((x + 28, y + 26), title, font=font("DejaVuSansMono.ttf", 27), fill=colour)
    wrap(d, sub, (x + 28, y + 76), SMALL, DIM, 30)

room(120, 300, 520, 230, "recall-…-gulf-coast", "Gulf Coast staff\n@liaison-gulf-coast", AMBER)
room(120, 570, 520, 230, "recall-…-riverside", "Riverside staff\n@liaison-riverside", AMBER)
room(760, 420, 620, 300, "recall-skinguard", "@registrar\n@regulatory  (exclusive role)\n@comms", ACCENT)
d.line([640, 415, 760, 520], fill=(90, 100, 112), width=3)
d.line([640, 685, 760, 620], fill=(90, 100, 112), width=3)
d.text((1430, 470), "files only its", font=SMALL, fill=DIM)
d.text((1430, 505), "own account →", font=SMALL, fill=DIM)
d.text((120, 860), "The registrar is a member of NO consignee room.", font=H2, fill=GREEN)
d.text((120, 930), "Not told to avoid them. Not in them.", font=BODY, fill=DIM)
footer(d); hold(img, 12)

# ----------------------------------------------------------- 6. the Switch quote
img, d = new()
d.text((120, 300), "Switch's own documentation:", font=BODY, fill=DIM)
wrap(d, "“Membership is the boundary that matters here.\nSeparate rooms preserve the boundary.”",
     (120, 390), H2, ACCENT, 46)
d.text((120, 620), "So isolation is enforced by Switch,", font=BODY, fill=FG)
d.text((120, 675), "not requested in a prompt.", font=BODY, fill=FG)
d.text((120, 790), "Remove Switch and every consignee reads every", font=BODY, fill=DIM)
d.text((120, 845), "other's figures. In a real recall that is unlawful.", font=BODY, fill=DIM)
footer(d); hold(img, 10)

# --------------------------------------------------- 7-9. the three refusals
def refusal(n, head, setup, out_lines, punch):
    img, d = new()
    d.text((120, 90), f"Refusal {n}", font=H2, fill=RED)
    d.text((120, 160), head, font=H1, fill=FG)
    y = wrap(d, setup, (120, 290), BODY, DIM, 72)
    top = y + 30
    d.rounded_rectangle([120, top, W - 120, top + 60 + 48 * len(out_lines)], 14, fill=PANEL)
    yy = top + 30
    for t, c in out_lines:
        d.text((170, yy), t, font=MONO, fill=c); yy += 48
    d.text((120, 940), punch, font=H2, fill=AMBER)
    footer(d); hold(img, 13)

refusal(
    1, "The numbers do not add up.",
    "Gulf Coast returns 4,800 of 7,200 bottles and states the recall is\nfinished. Nothing in the words is wrong.",
    [("CLOSURE REFUSED", RED),
     ("  - Gulf Coast Wholesale: reports the recall complete while", FG),
     ("    2400 of 7200 units are still unaccounted for", FG)],
    "Then @regulatory orders closure — and is refused too.")

refusal(
    2, "They add up, and rest on nothing.",
    "Gulf Coast finds the rest: 1,500 destroyed, 500 quarantined, 400 sold.\n7,200 of 7,200. Only the returns cite a document.",
    [("CLOSURE REFUSED", RED),
     ("  - Gulf Coast Wholesale: claims 1500 units destroyed citing", FG),
     ("    no document and it is counted as recovered", FG)],
    "A count with no paper behind it is a sentence, not a fact.")

refusal(
    3, "Evidenced — and still wrong.",
    "Every count now cites a document and the total is exact. Then the firm\nchecks its own receiving log: the other side of the transaction.",
    [("CLOSURE REFUSED", RED),
     ("  - Gulf Coast Wholesale: claims 4800 units returned, but the", FG),
     ("    firm's receiving log records 4300 arriving back: 500 units", FG),
     ("    are claimed as returned and were never received", FG)],
    "No amount of self-consistency finds that.")

# ------------------------------------------------------------- 10. resolution
img, d = new()
d.text((120, 110), "The resolution is worse than the dispute", font=H1, fill=FG)
wrap(d, "Those 500 bottles were never sent back. They were sold before the recall\nnotice reached the shop floor, and written up as returns afterwards.",
     (120, 250), BODY, DIM, 76)
d.text((120, 430), "They do not move from “returned” to “found”.", font=H2, fill=FG)
d.text((120, 500), "They move from recovered to in somebody's bathroom.", font=H2, fill=RED)
d.rounded_rectangle([120, 620, W - 120, 900], 14, fill=PANEL)
d.text((170, 660), "Recovery rate", font=BODY, fill=DIM)
d.text((170, 720), "85.4%", font=font("DejaVuSans-Bold.ttf", 86), fill=GREEN)
d.text((700, 660), "Never recovered", font=BODY, fill=DIM)
d.text((700, 720), "1,400 bottles", font=font("DejaVuSans-Bold.ttf", 86), fill=RED)
d.text((170, 830), "not the 90.6% the tidy version claimed", font=SMALL, fill=DIM)
footer(d); hold(img, 12)

# ----------------------------------------------------------- 11. certificate
img, d = new()
d.text((120, 110), "Closure is signed for, as a room document", font=H1, fill=FG)
d.rounded_rectangle([120, 250, W - 120, 820], 14, fill=PANEL)
cert = [
    ("# Closure certificate — recall D-1572-2020", ACCENT),
    ("", FG),
    ("Closed by M. Haddad, regulatory affairs.", FG),
    ("", FG),
    ("- Shipped:         9600", FG),
    ("- Recovered:       8200  (85.4%)", GREEN),
    ("- Never recovered: 1400", RED),
    ("", FG),
    ("1400 units were never recovered. The FDA enforcement", DIM),
    ("record for D-1572-2020 has no field in which to say so.", DIM),
]
y = 300
for t, c in cert:
    d.text((170, y), t, font=MONO, fill=c); y += 50
d.text((120, 870), "A chat message scrolls away. Someone will look for this in two years.", font=BODY, fill=DIM)
footer(d); hold(img, 11)

# ---------------------------------------------------------------- 12. close
img, d = new()
d.text((120, 260), "Closeout", font=font("DejaVuSans-Bold.ttf", 100), fill=FG)
d.text((124, 400), "Authority is not arithmetic.", font=H2, fill=ACCENT)
items = [
    "Three agents on Claude Code, in Mattermost, through Switch",
    "One private room per consignee; the registrar is in none of them",
    "Template generated from the distribution list — tested at twelve",
    "62 tests · ./scripts/demo.sh runs offline, no key, no server",
]
y = 540
for it in items:
    d.text((130, y), "—", font=BODY, fill=ACCENT)
    d.text((180, y), it, font=BODY, fill=DIM); y += 62
d.text((120, 880), "github.com/ANMOLGUPTA-24/closeout", font=MONOB, fill=ACCENT)
hold(img, 8)

# ------------------------------------------------------------------ encode
if FRAMES.exists(): shutil.rmtree(FRAMES)
FRAMES.mkdir(parents=True)
idx = 0
for img, secs in shots:
    for _ in range(int(secs * FPS)):
        img.save(FRAMES / f"{idx:05d}.png"); idx += 1
print(f"{len(shots)} scenes, {idx} frames, {idx/FPS:.0f}s")

mp4 = OUT / "closeout-demo.mp4"
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
    "-i", str(FRAMES / "%05d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
    "-vf", "fade=t=in:st=0:d=0.6", str(mp4),
], check=True)
shutil.rmtree(FRAMES)
print("wrote", mp4, f"{mp4.stat().st_size/1e6:.1f} MB")
