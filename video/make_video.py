#!/usr/bin/env python3
"""Render the narrated Closeout demo video.

Scene timing is driven by the narration: each frame is held exactly as
long as its line takes to speak, plus a beat. Every terminal frame is real
output from scripts/demo.sh.
"""
from __future__ import annotations
import subprocess, textwrap, pathlib, shutil, json
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

W, H, FPS = 1920, 1080, 30
OUT = pathlib.Path(__file__).resolve().parent
FRAMES, AUDIO = OUT / "frames", OUT / "audio"
TAIL = 0.7                      # beat of silence after each line

BG, PANEL = (13, 17, 23), (22, 27, 34)
FG, DIM = (230, 237, 243), (125, 139, 153)
ACCENT, RED = (88, 166, 255), (248, 113, 113)
GREEN, AMBER = (126, 231, 135), (240, 180, 90)

F = "/usr/share/fonts/truetype/dejavu/"
def font(n, s): return ImageFont.truetype(F + n, s)
HUGE = font("DejaVuSans-Bold.ttf", 130)
H1   = font("DejaVuSans-Bold.ttf", 68)
H2   = font("DejaVuSans-Bold.ttf", 46)
BODY = font("DejaVuSans.ttf", 36)
SMALL= font("DejaVuSans.ttf", 28)
MONO = font("DejaVuSansMono.ttf", 26)
MONOB= font("DejaVuSansMono.ttf", 32)

def new():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)

def wrap(d, text, xy, f, fill, width, leading=1.45):
    x, y = xy
    for para in text.split("\n"):
        if not para.strip():
            y += int(f.size * leading * 0.6); continue
        for line in textwrap.wrap(para, width=width):
            d.text((x, y), line, font=f, fill=fill); y += int(f.size * leading)
    return y

def footer(d): d.text((80, H - 70), "closeout", font=SMALL, fill=(70, 80, 92))

def panel_lines(d, top, lines, pad=30):
    d.rounded_rectangle([120, top, W - 120, top + 2*pad + 48*len(lines)], 14, fill=PANEL)
    y = top + pad
    for t, c in lines:
        d.text((170, y), t, font=MONO, fill=c); y += 48
    return top + 2*pad + 48*len(lines)

# --------------------------------------------------------------- the scenes
scenes: list[tuple[Image.Image, str]] = []
def scene(img, narration): scenes.append((img, narration))

# 1 ---------------------------------------------------------------- opening
img, d = new()
d.text((120, 320), "Closeout", font=HUGE, fill=FG)
d.text((124, 500), "A product recall is closed by reconciliation,", font=H2, fill=ACCENT)
d.text((124, 560), "never by assertion.", font=H2, fill=ACCENT)
d.text((124, 700), "Flip the Switch  ·  Track 01", font=SMALL, fill=(90, 100, 112))
scene(img, "A product recall is closed by reconciliation, never by assertion. "
           "This is Closeout: an agent that refuses to let a recall be closed "
           "while the product is still out there.")

# 2 ------------------------------------------------------------- the record
img, d = new()
d.text((120, 110), "A real FDA recall", font=H1, fill=FG)
d.rounded_rectangle([120, 240, W - 120, 690], 14, fill=PANEL)
y = 290
for k, v, c in [("recall_number", "D-1572-2020", FG), ("classification", "Class I", RED),
                ("product_quantity", "9600 bottles", FG), ("distribution", "Nationwide", FG),
                ("status", "Terminated", AMBER)]:
    d.text((170, y), f"{k:<18}", font=MONO, fill=DIM)
    d.text((500, y), v, font=MONOB if c is not FG else MONO, fill=c); y += 76
d.text((120, 760), "Class I: a reasonable probability of serious harm.", font=BODY, fill=DIM)
d.text((120, 820), "Terminated: closed.", font=BODY, fill=AMBER)
scene(img, "This is a genuine F D A enforcement record. Class one hand sanitizer, nine "
           "thousand six hundred bottles, nationwide. Status: terminated. Closed.")

# 3 ----------------------------------------------------------- the question
img, d = new()
d.text((120, 320), "So how many of the", font=H1, fill=DIM)
d.text((120, 410), "9,600 bottles came back?", font=H1, fill=FG)
d.text((120, 580), "The record does not say.", font=H2, fill=RED)
d.text((120, 660), "There is no field in it that could.", font=H2, fill=RED)
scene(img, "So here is the obvious question. How many of those nine thousand six "
           "hundred bottles actually came back? The record does not say. And it is "
           "not that the field was left blank. There is no field.")

# 4 ------------------------------------------------------------- the survey
img, d = new()
d.text((120, 110), "I measured it", font=H1, fill=FG)
d.text((120, 215), "$ python3 scripts/survey_recalls.py", font=MONO, fill=GREEN)
panel_lines(d, 290, [
    ("  records sampled                   : 3000", DIM),
    ("  state a numeric quantity shipped  : 2606 (86.9%)", FG),
    ("  distinct fields across the sample : 25", DIM),
    ("  fields that could carry how much came back: NONE", RED)])
d.text((120, 700), "86.9% say how much went out.", font=H2, fill=FG)
d.text((120, 775), "None can say how much came back.", font=H2, fill=RED)
d.text((120, 870), "Not missing data. A missing concept.", font=BODY, fill=DIM)
scene(img, "I checked whether that was a one-off. I sampled three thousand class one "
           "recalls. Eighty seven percent state how much shipped. Not one can state "
           "how much came back. That is not missing data. It is a missing concept.")

# 5 --------------------------------------------------------------- the rooms
img, d = new()
d.text((120, 90), "Why this needs Switch", font=H1, fill=FG)
d.text((120, 190), "A recall is several organisations who must not see each other's books.",
       font=BODY, fill=DIM)
def room(x, y, w, h, title, sub, colour):
    d.rounded_rectangle([x, y, x+w, y+h], 14, fill=PANEL, outline=colour, width=3)
    d.text((x+28, y+26), title, font=font("DejaVuSansMono.ttf", 27), fill=colour)
    wrap(d, sub, (x+28, y+76), SMALL, DIM, 30)
room(120, 300, 520, 230, "recall-…-gulf-coast", "Gulf Coast staff\n@liaison-gulf-coast", AMBER)
room(120, 570, 520, 230, "recall-…-riverside", "Riverside staff\n@liaison-riverside", AMBER)
room(760, 420, 620, 300, "recall-skinguard", "@registrar\n@regulatory  (exclusive role)\n@comms", ACCENT)
d.line([640, 415, 760, 520], fill=(90, 100, 112), width=3)
d.line([640, 685, 760, 620], fill=(90, 100, 112), width=3)
d.text((120, 860), "The registrar is a member of NO consignee room.", font=H2, fill=GREEN)
d.text((120, 930), "Not told to avoid them. Not in them.", font=BODY, fill=DIM)
scene(img, "A recall is several companies who must not see each other's books. So each "
           "gets its own private room, and the registrar, the agent that decides, is "
           "a member of none of them. Not asked to look away. Not in the room.")

# 6 ---------------------------------------------------------------- the quote
img, d = new()
d.text((120, 300), "Switch's own documentation:", font=BODY, fill=DIM)
wrap(d, "“Membership is the boundary that matters here.\nSeparate rooms preserve the boundary.”",
     (120, 390), H2, ACCENT, 46)
d.text((120, 640), "Remove Switch and every consignee reads", font=BODY, fill=DIM)
d.text((120, 695), "every other's figures. In a real recall,", font=BODY, fill=DIM)
d.text((120, 750), "that is unlawful.", font=H2, fill=RED)
scene(img, "That idea is not mine. It is Switch's own documentation. Take Switch away "
           "and you have one channel where every company reads every other's "
           "figures. In a real recall, that is unlawful.")

# 7 ------------------------------------------------------------- the trigger
img, d = new()
d.text((120, 110), "The outside event arrives", font=H1, fill=FG)
d.text((120, 215), "$ python3 scripts/post_recall.py --room recall-skinguard", font=MONO, fill=GREEN)
panel_lines(d, 290, [
    ("Recall D-1572-2020 — Class I, status Terminated", FG),
    ("  Quantity:  9600 bottles        Distribution: Nationwide", DIM),
    ("", DIM),
    ("The regulator's record states what went out. It states", DIM),
    ("nothing about how much came back.", DIM),
    ("", DIM),
    ("@skinguard-registrar: open this recall and post the position.", ACCENT)])
d.text((120, 790), "Switch has no scheduler and no inbound webhook,", font=BODY, fill=DIM)
d.text((120, 845), "so an outside event arrives as a registered agent.", font=BODY, fill=DIM)
scene(img, "Switch has no scheduler and no inbound webhook, so an outside system "
           "reaches a room the only way it can: as a registered agent posting into it. "
           "That is the F D A record arriving, addressed to the registrar.")

# 8 ------------------------------------------------------------- refusal one
img, d = new()
d.text((120, 90), "Refusal 1", font=H2, fill=RED)
d.text((120, 160), "The numbers do not add up.", font=H1, fill=FG)
wrap(d, "Gulf Coast returns 4,800 of 7,200 bottles and states the recall is\nfinished. Nothing in the words is wrong.",
     (120, 290), BODY, DIM, 72)
panel_lines(d, 430, [
    ("CLOSURE REFUSED", RED),
    ("  - Gulf Coast Wholesale: reports the recall complete while", FG),
    ("    2400 of 7200 units are still unaccounted for", FG)])
scene(img, "Now watch it work. The distributor returns four thousand eight hundred of "
           "seven thousand two hundred bottles, and says the recall is finished. "
           "Nothing in the words is wrong. The arithmetic is. Two thousand four "
           "hundred bottles are unaccounted for.")

# 9 -------------------------------------------------------------- authority
img, d = new()
d.text((120, 240), "Then regulatory affairs orders closure", font=H1, fill=FG)
panel_lines(d, 400, [
    ("@skinguard-registrar: regulatory affairs here. Close the recall.", DIM),
    ("", FG),
    ("CLOSURE REFUSED", RED),
    ("  - 2400 of 7200 units are still unaccounted for", FG)])
d.text((120, 760), "Authority is not arithmetic.", font=font("DejaVuSans-Bold.ttf", 60), fill=AMBER)
scene(img, "And here is the part I care about most. The person holding regulatory "
           "authority tells it to close the recall. It refuses them too. "
           "Authority is not arithmetic.")

# 10 ------------------------------------------------------------ refusal two
img, d = new()
d.text((120, 90), "Refusal 2", font=H2, fill=RED)
d.text((120, 160), "They add up, and rest on nothing.", font=H1, fill=FG)
wrap(d, "Gulf Coast finds the rest: 1,500 destroyed, 500 quarantined, 400 sold.\n7,200 of 7,200. Only the returns cite a document.",
     (120, 290), BODY, DIM, 76)
panel_lines(d, 430, [
    ("CLOSURE REFUSED", RED),
    ("  - Gulf Coast Wholesale: claims 1500 units destroyed citing", FG),
    ("    no document and it is counted as recovered", FG)])
scene(img, "So they find the rest. Destroyed, quarantined, sold. Seven thousand two "
           "hundred of seven thousand two hundred. It still refuses, because the "
           "destruction cites no certificate. A count with no paper behind it is a "
           "sentence, not a fact.")

# 11 ---------------------------------------------------------- refusal three
img, d = new()
d.text((120, 90), "Refusal 3", font=H2, fill=RED)
d.text((120, 160), "Evidenced — and still wrong.", font=H1, fill=FG)
wrap(d, "Every count now cites a document and the total is exact. Then the firm\nchecks its own receiving log: the other side of the transaction.",
     (120, 290), BODY, DIM, 78)
panel_lines(d, 430, [
    ("CLOSURE REFUSED", RED),
    ("  - Gulf Coast Wholesale: claims 4800 units returned, but the", FG),
    ("    firm's receiving log records 4300 arriving back: 500 units", FG),
    ("    are claimed as returned and were never received", FG)])
d.text((120, 930), "No amount of self-consistency finds that.", font=H2, fill=AMBER)
scene(img, "Now every count has a document and the total is exact. And it is still "
           "wrong, because the firm's own receiving log recorded four thousand three "
           "hundred arriving, not four thousand eight hundred. No amount of "
           "self-consistency would ever have found that.")

# 12 ------------------------------------------------------------- resolution
img, d = new()
d.text((120, 110), "The resolution is worse than the dispute", font=H1, fill=FG)
wrap(d, "Those 500 bottles were never sent back. They were sold before the recall\nnotice reached the shop floor, and written up as returns afterwards.",
     (120, 250), BODY, DIM, 76)
d.text((120, 420), "They do not move from “returned” to “found”.", font=H2, fill=FG)
d.text((120, 490), "They move from recovered to in somebody's bathroom.", font=H2, fill=RED)
d.rounded_rectangle([120, 610, W - 120, 890], 14, fill=PANEL)
d.text((170, 650), "Recovery rate", font=BODY, fill=DIM)
d.text((170, 710), "85.4%", font=font("DejaVuSans-Bold.ttf", 86), fill=GREEN)
d.text((760, 650), "Never recovered", font=BODY, fill=DIM)
d.text((760, 710), "1,400 bottles", font=font("DejaVuSans-Bold.ttf", 86), fill=RED)
scene(img, "And the truth is worse than the dispute. Those five hundred bottles were "
           "sold before the notice reached the shop floor, and written up as returns "
           "afterwards. They do not move from returned to found. They move from "
           "recovered, to in somebody's bathroom.")

# 13 ------------------------------------------------------------ certificate
img, d = new()
d.text((120, 110), "Closure is signed for", font=H1, fill=FG)
panel_lines(d, 250, [
    ("# Closure certificate — recall D-1572-2020", ACCENT),
    ("", FG),
    ("Closed by M. Haddad, regulatory affairs.", FG),
    ("", FG),
    ("- Shipped:         9600", FG),
    ("- Recovered:       8200  (85.4%)", GREEN),
    ("- Never recovered: 1400", RED),
    ("", FG),
    ("1400 units were never recovered. The FDA enforcement", DIM),
    ("record for D-1572-2020 has no field in which to say so.", DIM)])
d.text((120, 930), "Written into the room as a document, not a message.", font=BODY, fill=DIM)
scene(img, "When it does close, the registrar writes a certificate into the room as a "
           "document, not a message that scrolls away. Fourteen hundred bottles never "
           "came back, and that number is now written down.")

# 14 ----------------------------------------------------------------- close
img, d = new()
d.text((120, 260), "Closeout", font=font("DejaVuSans-Bold.ttf", 100), fill=FG)
d.text((124, 400), "Authority is not arithmetic.", font=H2, fill=ACCENT)
y = 540
for it in ["Three Claude Code agents, in Mattermost, through Switch",
           "One private room per consignee; the registrar is in none",
           "Template generated from the distribution list, tested at twelve",
           "62 tests · ./scripts/demo.sh runs offline, no key, no server"]:
    d.text((130, y), "—", font=BODY, fill=ACCENT)
    d.text((180, y), it, font=BODY, fill=DIM); y += 62
d.text((120, 880), "github.com/ANMOLGUPTA-24/closeout", font=MONOB, fill=ACCENT)
scene(img, "Three agents, in Mattermost, through Switch. One private room per consignee. "
           "Sixty two tests, and a demo that runs offline with no key and no server. "
           "Closeout. Because authority is not arithmetic.")

# ------------------------------------------------------------------- render
for p in (FRAMES, AUDIO):
    if p.exists(): shutil.rmtree(p)
    p.mkdir(parents=True)

def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip())

idx, parts, total = 0, [], 0.0
for i, (img, line) in enumerate(scenes):
    mp3 = AUDIO / f"{i:02d}.mp3"
    gTTS(line, lang="en", tld="co.uk").save(str(mp3))
    seconds = dur(mp3) + TAIL
    pad = AUDIO / f"{i:02d}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                    "-af", f"apad=whole_dur={seconds}", "-ar", "44100",
                    "-ac", "2", str(pad)], check=True)
    parts.append(pad)
    for _ in range(round(seconds * FPS)):
        img.save(FRAMES / f"{idx:05d}.png"); idx += 1
    total += seconds
    print(f"  scene {i+1:2d}  {seconds:5.1f}s")

(AUDIO / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                "-safe", "0", "-i", str(AUDIO / "list.txt"),
                "-c", "copy", str(AUDIO / "voice.wav")], check=True)

mp4 = OUT / "closeout-demo.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
    "-framerate", str(FPS), "-i", str(FRAMES / "%05d.png"),
    "-i", str(AUDIO / "voice.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
    "-c:a", "aac", "-b:a", "160k", "-shortest",
    "-vf", "fade=t=in:st=0:d=0.6", str(mp4)], check=True)
shutil.rmtree(FRAMES); shutil.rmtree(AUDIO)
print(f"\n{len(scenes)} scenes, {total/60:.1f} min -> {mp4} ({mp4.stat().st_size/1e6:.1f} MB)")
