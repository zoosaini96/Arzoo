"""Explainer compositor: cable-free A-roll + B-roll cards + motion graphics + captions.
Layout: src/c1..c8.mov (audio), clean/c1..c8.avi (tone-mapped, cable removed), dl/broll, dl/music, dl/sfx."""
import subprocess, sys, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, CLEAN, DL, OUT = f"{S}/src", f"{S}/clean", f"{S}/dl", f"{S}/out"
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FONT + f"Inter-{w}.otf", s)

# ---------------- timeline (frame-accurate trims, source seconds) ----------------
TRIM = {1: (14, 234), 2: (4, 171), 3: (0, 65), 4: (7, 275), 5: (15, 307), 6: (1, 231), 7: (3, 104), 8: (5, 119)}
ORDER = [1, 2, 3, 4, 5, 6, 7, 8]
INS = {4: (124, 8)}  # insert spoken "or" in clip 4 at source frame 124 ("car | furniture"), 8 frames long
OR_SRC = (7, 2.49, 2.66)  # the "-ore" of "before" in clip 7
START = {}; acc = 0
for c in ORDER:
    a, b = TRIM[c]; START[c] = acc; acc += b - a + INS.get(c, (0, 0))[1]
SPEECH_N = acc; SPEECH_END = SPEECH_N / FPS
END_CARD = 3.2
TOTAL = SPEECH_END + END_CARD
N = int(round(TOTAL * FPS))
def g(c, t):  # clip-local source second -> output second
    sh = INS[c][1] / FPS if c in INS and t >= INS[c][0] / FPS - 1e-6 else 0
    return START[c] / FPS + t - TRIM[c][0] / FPS + sh
def clip_at(t):
    for c in ORDER:
        if g(c, TRIM[c][0] / FPS) <= t < g(c, TRIM[c][1] / FPS): return c
    return ORDER[-1]

NAVY = (32, 30, 30); AMBER = (255, 183, 3); ACCENT = (255, 106, 44); GREEN = (46, 196, 140); WHITE = (255, 255, 255)
CORAL = (240, 84, 84); GREY = (160, 170, 185); RED = (216, 43, 43)

# captions: (start, end, text) ; *word* = highlight
CAPS = [
    (g(1, .55), g(1, 1.70), "Hi everyone!"),
    (g(1, 1.75), g(1, 3.98), "In this video, I will share *4 important things*"),
    (g(1, 3.98), g(1, 5.74), "that every *home buyer* should know"),
    (g(1, 5.74), g(1, 7.80), "before purchasing their home in *Canada*."),
    (g(2, .15), g(2, 1.95), "*First* and the most important,"),
    (g(2, 1.95), g(2, 4.0), "always get a *mortgage pre-approval*"),
    (g(2, 4.0), g(2, 5.7), "before starting a *house hunt*,"),
    (g(3, 0.0), g(3, 2.17), "so you know *how much you can afford*."),
    (g(4, .25), g(4, .95), "*Second*,"),
    (g(4, .95), g(4, 2.6), "avoid making *big purchases*"),
    (g(4, 2.6), g(4, 4.7), "like *financing a car* or *furniture*"),
    (g(4, 4.7), g(4, 5.85), "before *closing*,"),
    (g(4, 5.85), g(4, 9.17), "because it may affect your *mortgage qualification*."),
    (g(5, .55), g(5, 1.2), "*Third*,"),
    (g(5, 1.25), g(5, 3.9), "do not focus only on *interest rate*."),
    (g(5, 4.15), g(5, 6.15), "Always review your *terms*,"),
    (g(5, 6.15), g(5, 7.05), "*conditions*,"),
    (g(5, 7.05), g(5, 8.3), "*prepayment privileges*,"),
    (g(5, 8.3), g(5, 10.24), "*penalties* and other *features*."),
    (g(6, .05), g(6, .65), "And *last*,"),
    (g(6, .7), g(6, 3.3), "before *switching your job* during mortgage process,"),
    (g(6, 3.55), g(6, 5.02), "speak with your *mortgage professional*"),
    (g(6, 5.02), g(6, 7.7), "because it may affect your *mortgage approval*."),
    (g(7, .1), g(7, 1.62), "Remember, making *informed decisions*"),
    (g(7, 1.62), g(7, 3.47), "before *buying a home*"),
    (g(8, .17), g(8, 3.2), "can save you from unnecessary *financial stress* later."),
    (g(8, 3.3), SPEECH_END, "*Thank you!*"),
]

# B-roll: (file, src_start, t0, t1, crop_center_x (0-1 of 1280), label, icon)
BROLL = [
    ("24945.mp4", 3.0, g(1, 5.74), g(1, 7.80), 0.45, "Buying a home in Canada", "house"),
    ("6021.mp4", 3.0, g(2, 4.0), g(2, 5.7), 0.50, "Before the house hunt", "house"),
    ("4533.mp4", 9.0, g(2, 5.7), g(3, 2.0), 0.60, "Know your budget", "check"),
    ("35540.mp4", 4.0, g(4, 2.6), g(4, 4.1), 0.42, "Financing a car", "warn"),
    ("3110.mp4", 6.0, g(4, 4.1), g(4, 5.25), 0.62, "New furniture", "warn"),
    ("21373.mp4", 3.0, g(6, 3.55), g(6, 5.05), 0.60, "Talk to your mortgage professional", "bulb"),
    ("36136.mp4", 2.0, g(7, 1.6), g(8, 0.9), 0.60, "Make informed decisions", "check"),
]
CARD_W, CARD_H, CARD_CY = 940, 1175, 860
WARM = {"24945.mp4", "35540.mp4", "3110.mp4"}

TIPS = [  # (n, title, pill, t0, t1)
    (1, "Get pre-approved first", "PRE-APPROVAL", g(2, .15), g(2, 1.95)),
    (2, "Avoid big purchases", "BIG PURCHASES", g(4, .25), g(4, 2.6)),
    (3, "Look beyond the rate", "RATE ISN'T EVERYTHING", g(5, .55), g(5, 1.95)),
    (4, "Talk before switching jobs", "CHANGING JOBS", g(6, .05), g(6, 1.35)),
]
CHAPTERS = [(0, TIPS[0][3], "4 TIPS FOR HOME BUYERS")]
for i, tp in enumerate(TIPS):
    end = TIPS[i + 1][3] if i < 3 else g(7, TRIM[7][0] / FPS)
    CHAPTERS.append((tp[3] + 0.9, end, f"TIP {tp[0]}/4 · {tp[2]}"))
CHAPTERS.append((g(7, TRIM[7][0] / FPS), SPEECH_END, "REMEMBER"))

BASEZ = {1: 1.0, 2: 1.16, 3: 1.16, 4: 1.0, 5: 1.16, 6: 1.0, 7: 1.16, 8: 1.0}
ANCHOR = (540, 430)
PUNCH = [(g(2, 1.95), g(2, 4.0), 1.26), (g(4, 5.85), g(4, 9.2), 1.08), (g(5, 4.15), g(5, 10.3), 1.24),
         (g(6, 5.05), g(6, 7.8), 1.12), (g(8, 2.6), SPEECH_END + 10, 1.12)]

def ease_out_back(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_io(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)

def zoom_at(t):
    for a, b, z in PUNCH:
        if a <= t < b: return z
    c = clip_at(t); a = g(c, TRIM[c][0] / FPS); b = g(c, TRIM[c][1] / FPS)
    return BASEZ[c] + 0.04 * (t - a) / max(0.1, b - a)

# ---------------- drawing helpers ----------------
def rrect(size, r, fill, outline=None, width=0):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, size[0]-1, size[1]-1], r, fill=fill, outline=outline, width=width)
    return im

def shadowed(im, blur=18, off=(0, 10), alpha=110):
    pad = blur * 3
    sh = Image.new("RGBA", (im.width + 2*pad, im.height + 2*pad), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh.paste(blk, (pad + off[0], pad + off[1]), blk)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh.alpha_composite(im, (pad, pad))
    return sh

def paste(layer, im, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if scale <= 0.01 or alpha <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width*scale)), max(1, int(im.height*scale))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1.0:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    layer.alpha_composite(im, (int(cx - im.width/2), int(cy - im.height/2)))

def check_icon(d, cx, cy, r, bg=GREEN):
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=bg)
    w = max(4, r // 4)
    d.line([(cx - r*0.45, cy + r*0.02), (cx - r*0.1, cy + r*0.38), (cx + r*0.5, cy - r*0.35)], fill=WHITE, width=w, joint="curve")

def x_icon(d, cx, cy, r, bg=RED):
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=bg)
    w = max(4, r // 4); k = r * 0.38
    d.line([(cx-k, cy-k), (cx+k, cy+k)], fill=WHITE, width=w); d.line([(cx-k, cy+k), (cx+k, cy-k)], fill=WHITE, width=w)

def warn_icon(d, cx, cy, s, col=AMBER, fg=NAVY):
    d.polygon([(cx, cy - s), (cx - s*1.1, cy + s*0.8), (cx + s*1.1, cy + s*0.8)], fill=col)
    d.rectangle([cx - s*0.09, cy - s*0.45, cx + s*0.09, cy + s*0.25], fill=fg)
    d.ellipse([cx - s*0.11, cy + s*0.4, cx + s*0.11, cy + s*0.62], fill=fg)

def house_icon(d, cx, cy, s, col, door=NAVY):
    d.polygon([(cx, cy - s), (cx - s, cy - s*0.05), (cx + s, cy - s*0.05)], fill=col)
    d.rectangle([cx - s*0.7, cy - s*0.1, cx + s*0.7, cy + s*0.8], fill=col)
    d.rectangle([cx - s*0.18, cy + s*0.3, cx + s*0.18, cy + s*0.8], fill=door)

def briefcase_icon(d, cx, cy, s, col):
    d.rounded_rectangle([cx - s*0.35, cy - s*0.75, cx + s*0.35, cy - s*0.35], s*0.12, outline=col, width=max(4, int(s*0.12)))
    d.rounded_rectangle([cx - s, cy - s*0.45, cx + s, cy + s*0.75], s*0.18, fill=col)
    d.rectangle([cx - s, cy - s*0.02, cx + s, cy + s*0.06], fill=NAVY)

def text_w(font, s): return font.getlength(s)

def caption_img(text):
    font = F("ExtraBold", 64)
    parts = []; hl = False
    for tok in text.replace("*", " * ").split():
        if tok == "*": hl = not hl; continue
        if parts and all(ch in ".,?!" for ch in tok):
            parts[-1] = (parts[-1][0] + tok, parts[-1][1]); continue
        parts.append((tok, hl))
    lines, cur, maxw = [], [], 960
    for w_, h_ in parts:
        trial = " ".join(x for x, _ in cur + [(w_, h_)])
        if cur and text_w(font, trial) > maxw: lines.append(cur); cur = [(w_, h_)]
        else: cur.append((w_, h_))
    lines.append(cur)
    lh = 82; sw = 7
    im = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        total = text_w(font, " ".join(x for x, _ in ln)); x = (W - total) / 2; y = 20 + i * lh
        for w_, h_ in ln:
            d.text((x, y), w_, font=font, fill=AMBER if h_ else WHITE, stroke_width=sw, stroke_fill=(0, 0, 0))
            x += text_w(font, w_ + " ")
    return shadowed(im, blur=10, off=(0, 4), alpha=120)

def chip_img(text, bg=NAVY, fg=WHITE, size=44, icon=None):
    font = F("ExtraBold", size)
    tw = int(text_w(font, text)); padx, h = 34, int(size * 1.9)
    iw = int(h * 0.75) if icon else 0
    im = rrect((tw + 2*padx + iw, h), h // 2, bg + (242,))
    d = ImageDraw.Draw(im); cx = padx + iw*0.35
    if icon == "check": check_icon(d, cx, h/2, int(h*0.3))
    if icon == "house": house_icon(d, cx, h/2, h*0.27, ACCENT)
    if icon == "warn": warn_icon(d, cx, h/2 + 2, h*0.27)
    if icon == "bulb":
        r = h*0.22
        d.ellipse([cx-r, h/2-r*1.25, cx+r, h/2+r*0.75], fill=ACCENT)
        d.rectangle([cx-r*0.5, h/2+r*0.6, cx+r*0.5, h/2+r*1.2], fill=GREY)
    d.text((padx + iw, h/2), text, font=font, fill=fg, anchor="lm")
    return shadowed(im, blur=12, off=(0, 6), alpha=120)

def panel_base(title, pw, ph, head=ACCENT):
    im = rrect((pw, ph), 40, (255, 255, 255, 240)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw-1, 112], 40, fill=head + (255,)); d.rectangle([0, 70, pw-1, 112], fill=head + (255,))
    d.text((pw/2, 58), title, font=F("ExtraBold", 50), fill=WHITE, anchor="mm")
    return im, d

def list_img(title, items, tms, t, mark="check", footer=None, footer_t=None):
    """Panel with title + items that pop in at times tms. mark: check|x."""
    pw, row = 900, 100
    ph = 130 + row * len(items) + 24 + (110 if footer else 0)
    im, d = panel_base(title, pw, ph)
    for i, it in enumerate(items):
        y = 130 + i * row + row/2
        if t >= tms[i]:
            s = ease_out_back((t - tms[i]) / 0.3)
            ic = Image.new("RGBA", (90, 90), (0, 0, 0, 0)); di = ImageDraw.Draw(ic)
            (check_icon if mark == "check" else x_icon)(di, 45, 45, 36)
            ic = ic.resize((max(1, int(90*s)), max(1, int(90*s))), Image.BICUBIC)
            im.alpha_composite(ic, (int(90 - ic.width/2), int(y - ic.height/2)))
            d.text((160, y), it, font=F("Bold", 52), fill=NAVY, anchor="lm")
        else:
            d.ellipse([90-30, y-30, 90+30, y+30], outline=(200, 205, 215), width=5)
            d.text((160, y), it, font=F("Bold", 52), fill=(205, 210, 220), anchor="lm")
    if footer and t >= footer_t:
        p = ease_out((t - footer_t) / 0.3); y0 = ph - 120
        d.rounded_rectangle([30, y0, pw - 30, y0 + 92], 26, fill=(255, 240, 205, int(255 * p)))
        warn_icon(d, 92, y0 + 44, 30)
        d.text((150, y0 + 46), footer, font=F("ExtraBold", 42), fill=(150, 60, 0, int(255 * p)), anchor="lm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def title_img():
    im = Image.new("RGBA", (980, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 979, 399], 48, fill=(255, 255, 255, 245))
    d.rounded_rectangle([0, 0, 22, 399], 11, fill=ACCENT)
    d.ellipse([40, 70, 300, 330], fill=ACCENT)
    d.text((170, 205), "4", font=F("Black", 210), fill=WHITE, anchor="mm")
    d.text((340, 120), "THINGS EVERY", font=F("Black", 64), fill=NAVY, anchor="lm")
    d.text((340, 200), "HOME BUYER", font=F("Black", 64), fill=ACCENT, anchor="lm")
    d.text((340, 280), "SHOULD KNOW", font=F("Black", 64), fill=NAVY, anchor="lm")
    return shadowed(im, blur=24, off=(0, 12), alpha=130)

def tip_img(n, title):
    font = F("Black", 66)
    tw = int(text_w(font, title)); pw = max(700, tw + 120)
    im = Image.new("RGBA", (pw, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 90, pw-1, 419], 46, fill=(255, 255, 255, 245))
    cx = pw / 2
    d.ellipse([cx-95, 0, cx+95, 190], fill=ACCENT, outline=WHITE, width=10)
    d.text((cx, 98), str(n), font=F("Black", 120), fill=WHITE, anchor="mm")
    d.text((cx, 245), f"TIP {n} OF 4", font=F("ExtraBold", 40), fill=ACCENT, anchor="mm")
    d.text((cx, 330), title, font=font, fill=NAVY, anchor="mm")
    return shadowed(im, blur=24, off=(0, 12), alpha=130)

def stamp_img(top, bottom):
    im = Image.new("RGBA", (560, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([20, 20, 540, 540], fill=GREEN + (255,), outline=WHITE, width=14)
    d.ellipse([52, 52, 508, 508], outline=(255, 255, 255, 150), width=4)
    d.text((280, 175), top, font=F("Black", 62), fill=WHITE, anchor="mm")
    d.text((280, 245), bottom, font=F("Black", 62), fill=WHITE, anchor="mm")
    d.line([(180, 350), (250, 420), (385, 290)], fill=WHITE, width=34, joint="curve")
    return shadowed(im, blur=24, off=(0, 14), alpha=130)

def rate_img(p):
    """'%' badge with 'Interest rate' crossed and the other things growing."""
    pw, ph = 900, 400
    im = rrect((pw, ph), 40, (255, 255, 255, 240)); d = ImageDraw.Draw(im)
    d.ellipse([40, 60, 320, 340], fill=ACCENT)
    d.text((180, 200), "%", font=F("Black", 170), fill=WHITE, anchor="mm")
    d.text((370, 135), "Interest rate", font=F("ExtraBold", 58), fill=NAVY, anchor="lm")
    d.text((370, 215), "is not the", font=F("Bold", 50), fill=(90, 100, 120), anchor="lm")
    d.text((370, 285), "only thing!", font=F("ExtraBold", 58), fill=RED, anchor="lm")
    if p > 0.45:
        q = ease_out((p - 0.45) / 0.25); x1 = 370 + (790 - 370) * q
        d.line([(370, 140), (x1, 140)], fill=RED, width=9)
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def job_img(p):
    pw, ph = 900, 380
    im = rrect((pw, ph), 40, (255, 255, 255, 240)); d = ImageDraw.Draw(im)
    a = ease_out(p / 0.4)
    briefcase_icon(d, 150, 150, 70, NAVY)
    # arrow
    ax = 250 + 30 * a
    d.line([(250, 150), (ax + 100, 150)], fill=ACCENT, width=14)
    d.polygon([(ax + 130, 150), (ax + 95, 122), (ax + 95, 178)], fill=ACCENT)
    briefcase_icon(d, 500, 150, 70, (120, 130, 150))
    d.text((630, 112), "New", font=F("ExtraBold", 50), fill=NAVY, anchor="lm")
    d.text((630, 182), "job?", font=F("ExtraBold", 50), fill=NAVY, anchor="lm")
    d.rounded_rectangle([40, 255, pw - 40, 345], 26, fill=(255, 240, 205))
    warn_icon(d, 100, 298, 30)
    d.text((155, 300), "Talk to your mortgage pro first", font=F("ExtraBold", 42), fill=(150, 60, 0), anchor="lm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def endcard_img():
    im = Image.new("RGBA", (W, 1000), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    house_icon(d, W/2, 170, 120, ACCENT, door=(40, 34, 30))
    d.text((W/2, 400), "Thanks for watching!", font=F("Black", 88), fill=WHITE, anchor="mm")
    d.text((W/2, 500), "Share this with someone", font=F("SemiBold", 48), fill=(225, 232, 245), anchor="mm")
    d.text((W/2, 565), "planning to buy a home.", font=F("SemiBold", 48), fill=(225, 232, 245), anchor="mm")
    x = W/2 - 3*250/2 - 20
    for i, (lab, col) in enumerate((("LIKE", CORAL), ("SHARE", GREEN), ("FOLLOW", ACCENT))):
        cx = x + i * 270 + 125
        d.rounded_rectangle([cx-125, 690, cx+125, 790], 50, fill=col)
        d.text((cx, 740), lab, font=F("Black", 46), fill=WHITE, anchor="mm")
    d.text((W/2, 880), "for more home-buying tips", font=F("Bold", 44), fill=ACCENT, anchor="mm")
    return im

def chapter_img(text):
    font = F("ExtraBold", 34); tw = int(text_w(font, text))
    im = rrect((tw + 70, 66), 33, (0, 0, 0, 150)); d = ImageDraw.Draw(im)
    d.ellipse([22, 25, 38, 41], fill=ACCENT)
    d.text((50, 33), text, font=font, fill=WHITE, anchor="lm")
    return im

# ---------------- sources ----------------
def reader(cmd, w, h):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w*h*3*4)
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()

def aroll_frames():
    for c in ORDER:
        a, b = TRIM[c]
        cmd = ["ffmpeg", "-v", "error", "-i", f"{CLEAN}/c{c}.avi", "-vf", f"select='between(n,{a},{b-1})'",
               "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        i = a; prev = None
        for fr in reader(cmd, W, H):
            if c in INS and i == INS[c][0]:
                for _ in range(INS[c][1]): yield prev
            yield fr; prev = fr; i += 1

def build_speech():
    parts, labs = [], []
    oc, o0, o1 = OR_SRC; NI = len(ORDER)
    def seg(k, a, b, lab):
        d = (b - a) / FPS
        parts.append(f"[{k}:a]atrim={a/FPS:.4f}:{b/FPS:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d-0.02:.4f}:d=0.02,"
                     f"apad=whole_dur={d:.4f},atrim=0:{d:.4f}[{lab}]")
    for k, c in enumerate(ORDER):
        a, b = TRIM[c]
        if c in INS:
            f0, nf = INS[c]; gd = nf / FPS
            seg(k, a, f0, f"p{k}a"); seg(k, f0, b, f"p{k}b")
            parts.append(f"[{NI}:a]atrim={o0}:{o1},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={o1-o0-0.025:.4f}:d=0.025,"
                         f"adelay=40:all=1,apad=whole_dur={gd:.4f},atrim=0:{gd:.4f}[or{k}]")
            labs += [f"[p{k}a]", f"[or{k}]", f"[p{k}b]"]
        else:
            seg(k, a, b, f"a{k}"); labs.append(f"[a{k}]")
    fc = ";".join(parts) + ";" + "".join(labs) + f"concat=n={len(labs)}:v=0:a=1,highpass=f=80,afftdn=nf=-25," \
         "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000[s]"
    ins = sum([["-i", f"{SRC}/c{c}.mov"] for c in ORDER], []) + ["-i", f"{SRC}/c{oc}.mov"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[s]", "-ac", "2", f"{OUT}/speech.wav"], check=True)

def broll_reader(spec):
    f, ss, t0, t1, cx = spec[:5]
    dur = t1 - t0 + 0.3
    x = int(cx * 1280 - 288); x = max(0, min(1280 - 576, x))
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", f"{dur:.3f}", "-i", f"{DL}/broll/{f}",
           "-vf", f"fps=30,scale=1280:720,crop=576:720:{x}:0,scale={CARD_W}:{CARD_H}:flags=lanczos,eq=contrast=1.04:saturation=1.08" + (",colorbalance=rs=0.05:gs=0.01:bs=-0.06:rm=0.03:bm=-0.04,eq=brightness=0.02:saturation=1.12" if f in WARM else ""),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return reader(cmd, CARD_W, CARD_H)

def main():
    only = None
    if "--frames" in sys.argv: only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]
    if only is None: build_speech()
    aroll = aroll_frames()

    cap_cache = {i: caption_img(c[2]) for i, c in enumerate(CAPS)}
    chips = {i: chip_img(b[5], icon=b[6]) for i, b in enumerate(BROLL)}
    chap = {c[2]: chapter_img(c[2]) for c in CHAPTERS}
    tips = {tp[0]: tip_img(tp[0], tp[1]) for tp in TIPS}
    TITLE, END = title_img(), endcard_img()
    STAMP = stamp_img("PRE-", "APPROVED")
    WARN1 = chip_img("May affect your approval", bg=(255, 183, 3), fg=NAVY, size=46, icon=None)
    mask = Image.new("L", (CARD_W, CARD_H), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W-1, CARD_H-1], 46, fill=255)
    card_border = Image.new("RGBA", (CARD_W + 16, CARD_H + 16), (0, 0, 0, 0))
    ImageDraw.Draw(card_border).rounded_rectangle([0, 0, CARD_W + 15, CARD_H + 15], 54, fill=(255, 255, 255, 255))
    card_border = shadowed(card_border, blur=26, off=(0, 16), alpha=150)

    TITLE_T = (g(1, 1.75), g(1, 5.74))
    STAMP_T = (g(2, 2.0), g(2, 4.0))
    AVOID = ("Before closing, avoid", ["Financing a car", "Big furniture buys"], g(4, 5.25), g(4, 9.2),
             [g(4, 5.35), g(4, 5.65)], "x", "Can affect your qualification", g(4, 7.0))
    RATE_T = (g(5, 1.95), g(5, 3.95))
    REVIEW = ("Always review your", ["Terms", "Conditions", "Prepayment privileges", "Penalties", "Other features"],
              g(5, 4.15), g(5, 10.3), [g(5, 5.6), g(5, 6.3), g(5, 7.14), g(5, 8.5), g(5, 9.45)], "check", None, None)
    JOB_T = (g(6, 1.35), g(6, 3.45))
    WARN_T = (g(6, 6.0), g(6, 7.75))
    RECAP = ("Quick recap", ["Get pre-approved", "Avoid big purchases", "Look beyond the rate", "Talk before job changes"],
             g(8, 0.9), g(8, 3.25), [g(8, 1.0), g(8, 1.45), g(8, 1.9), g(8, 2.35)], "check", None, None)
    LISTS = [AVOID, REVIEW, RECAP]

    if only is None:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                                "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                                "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709",
                                "-color_trc", "bt709", f"{OUT}/video_noaudio.mp4"], stdin=subprocess.PIPE)
    br_iters = {}; last_br = {}; end_bg = None; last_frame = None
    for n in range(N):
        t = n / FPS
        frame = next(aroll, None)
        if frame is None: frame = last_frame
        last_frame = frame
        if only is not None and n not in only:
            for i, b in enumerate(BROLL):
                if b[2] <= t < b[3]:
                    if i not in br_iters: br_iters[i] = broll_reader(b)
                    fr = next(br_iters[i], None)
                    if fr is not None: last_br[i] = fr
            if n > max(only): break
            continue
        img = Image.fromarray(frame)
        if t < SPEECH_END:
            z = zoom_at(t)
            if z > 1.001:
                ax, ay = ANCHOR
                x0 = ax - ax / z; y0 = ay - ay / z
                img = img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + W / z, y0 + H / z))
        img = img.convert("RGBA")

        # ---- B-roll card
        for i, b in enumerate(BROLL):
            t0, t1 = b[2], b[3]
            if t0 <= t < t1:
                if i not in br_iters: br_iters[i] = broll_reader(b)
                fr = next(br_iters[i], None)
                if fr is None: fr = last_br[i]
                last_br[i] = fr
                card = Image.fromarray(fr)
                bg = card.crop((int((CARD_W - CARD_H*9/16)/2), 0, int((CARD_W + CARD_H*9/16)/2), CARD_H)).resize((54, 96), Image.BILINEAR)
                bg = bg.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR)
                bg = Image.fromarray((np.asarray(bg).astype(np.float32) * 0.55).astype(np.uint8)).convert("RGBA")
                prev_adj = i > 0 and abs(BROLL[i-1][3] - t0) < 0.05
                next_adj = i < len(BROLL) - 1 and abs(BROLL[i+1][2] - t1) < 0.05
                tin = 9 if prev_adj else (t - t0) / 0.28
                tout = 9 if next_adj else (t1 - t) / 0.2
                a = min(1, ease_out(tin), ease_io(tout))
                s = (0.88 + 0.12 * ease_out_back(tin) if tin < 1 else 1.0) + 0.03 * (t - t0) / (t1 - t0)
                img = Image.blend(img, bg, a) if a < 1 else bg
                c = card.convert("RGBA"); c.putalpha(mask)
                if prev_adj and t - t0 < 0.25:  # slide-swap between adjacent cards
                    q = ease_out((t - t0) / 0.25); ox = (1 - q) * 120; ca = q
                else: ox, ca = 0, 1
                paste(img, card_border, W/2 + ox, CARD_CY + 8, s, a * ca)
                paste(img, c, W/2 + ox, CARD_CY, s, a * ca)
                paste(img, chips[i], W/2, CARD_CY + CARD_H/2 - 10, ease_out_back((t - t0 - 0.2) / 0.35), a)

        L = img
        # ---- title
        a0, a1 = TITLE_T
        if a0 <= t < a1:
            p = (t - a0) / 0.4; q = (a1 - t) / 0.25
            paste(L, TITLE, W/2, 1230 + 60 * (1 - ease_out(p)), ease_out_back(p), min(1, ease_out(p), ease_io(q)))
        # ---- tip cards
        for nn, title, pill, a0, a1 in TIPS:
            if a0 <= t < a1:
                p = (t - a0) / 0.42; q = (a1 - t) / 0.25
                paste(L, tips[nn], W/2, 1200 + 70 * (1 - ease_out(p)), ease_out_back(p), min(1, ease_out(p * 1.5), ease_io(q)))
        # ---- stamp
        a0, a1 = STAMP_T
        if a0 <= t < a1:
            p = (t - a0) / 0.35; q = (a1 - t) / 0.2
            paste(L, STAMP, W/2, 1170, ease_out_back(p) * 0.85, min(1, ease_out(p * 2), ease_io(q)), rot=-10 * (1 - ease_out(p)))
        # ---- lists
        for title, items, a0, a1, tms, mark, foot, ft in LISTS:
            if a0 <= t < a1:
                p = (t - a0) / 0.4; q = (a1 - t) / 0.25
                im = list_img(title, items, tms, t, mark, foot, ft)
                paste(L, im, W/2, 1170 + 80 * (1 - ease_out(p)), 1.0, min(1, ease_out(p), ease_io(q)))
        # ---- rate
        a0, a1 = RATE_T
        if a0 <= t < a1:
            p = (t - a0) / 0.4; q = (a1 - t) / 0.25
            paste(L, rate_img((t - a0) / (a1 - a0)), W/2, 1200 + 80 * (1 - ease_out(p)), 1.0, min(1, ease_out(p), ease_io(q)))
        # ---- job
        a0, a1 = JOB_T
        if a0 <= t < a1:
            p = (t - a0) / 0.4; q = (a1 - t) / 0.25
            paste(L, job_img(t - a0), W/2, 1200 + 80 * (1 - ease_out(p)), 1.0, min(1, ease_out(p), ease_io(q)))
        # ---- approval warning chip
        a0, a1 = WARN_T
        if a0 <= t < a1:
            p = (t - a0) / 0.35; q = (a1 - t) / 0.2
            paste(L, WARN1, W/2, 1300, ease_out_back(p), min(1, ease_io(q)))
        # ---- captions
        if t < SPEECH_END:
            for i, (c0, c1_, _) in enumerate(CAPS):
                if c0 <= t < c1_:
                    p = (t - c0) / 0.15
                    paste(L, cap_cache[i], W/2, 1650, 0.88 + 0.12 * ease_out(p), min(1, ease_out(p * 1.5)))
            for c0, c1_, txt in CHAPTERS:
                if c0 <= t < c1_:
                    p = (t - c0) / 0.35; im = chap[txt]
                    paste(L, im, 40 + im.width/2 - 60 * (1 - ease_out(p)), 82, 1.0, ease_out(p))
        # ---- end card
        if t >= SPEECH_END - 0.25:
            if end_bg is None:
                eb = Image.fromarray(frame).resize((108, 192), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
                ov = Image.new("RGBA", (W, H), (40, 34, 30, 180))
                end_bg = eb.convert("RGBA"); end_bg.alpha_composite(ov)
            p = (t - SPEECH_END + 0.25) / 0.45
            L = Image.blend(L, end_bg, min(1, ease_io(p)))
            if t >= SPEECH_END:
                p = (t - SPEECH_END) / 0.5
                paste(L, END, W/2, 960 + 70 * (1 - ease_out(p)), 0.92 + 0.08 * ease_out_back(p), min(1, ease_out(p)))
        # ---- progress bar
        d = ImageDraw.Draw(L)
        d.rectangle([0, 0, W, 12], fill=(255, 255, 255, 70))
        d.rectangle([0, 0, int(W * min(1, t / SPEECH_END)), 12], fill=ACCENT + (255,))
        if only is not None:
            L.convert("RGB").save(f"{OUT}/still_{n:04d}.jpg", quality=88); continue
        enc.stdin.write(L.convert("RGB").tobytes())
        if n % 150 == 0: print(f"frame {n}/{N}", flush=True)
    if only is not None: return
    enc.stdin.close(); enc.wait()
    ev = {"TOTAL": TOTAL, "SPEECH_END": SPEECH_END, "BROLL": [b[2] for b in BROLL],
          "TIPS": [tp[3] for tp in TIPS], "TITLE": TITLE_T[0], "STAMP": STAMP_T[0],
          "LIST_ITEMS": [x for L_ in LISTS for x in L_[4]], "LISTS": [L_[2] for L_ in LISTS], "FOOT": AVOID[7],
          "RATE": RATE_T[0], "STRIKE": RATE_T[0] + 0.45 * (RATE_T[1] - RATE_T[0]), "JOB": JOB_T[0], "WARN": WARN_T[0],
          "CLIPS": [START[c] / FPS for c in ORDER]}
    json.dump(ev, open(f"{OUT}/timeline.json", "w"), indent=1)

if __name__ == "__main__":
    main()
