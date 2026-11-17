"""Compositor: enhanced A-roll framing + B-roll cards + motion graphics + word-synced captions."""
import subprocess, sys, json, os, re
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from timeline import S, FPS, SEGS, STARTS, SPEECH_END, g, seg_bounds
OUT, DL = f"{S}/out", f"{S}/dl"
W, H = 1080, 1920
FONT = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FONT + f"Inter-{w}.otf", s)
NAVY = (11, 37, 69); AMBER = (255, 183, 3); GREEN = (46, 196, 140); WHITE = (255, 255, 255)
CORAL = (255, 92, 92); GREY = (160, 170, 185); RED = (216, 30, 40)
END_CARD = 3.6
TOTAL = SPEECH_END + END_CARD
N = int(round(TOTAL * FPS))

# ---------------- easing ----------------
def clamp(x): return min(max(x, 0.0), 1.0)
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return x * x * (3 - 2 * x)
def ease_out_back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def env(t, a, b, i=0.35, o=0.22): return min(ease_out((t - a) / i), ease_io((b - t) / o))

# ---------------- timeline events ----------------
TIPS = [(g(2, 0.0), "Get pre-approved first"), (g(4, 0.25), "Avoid big purchases"),
        (g(5, 0.5), "Look beyond the rate"), (g(6, 0.0), "Talk before switching jobs")]
OUTRO = g(7, 0.0)
TITLE_K = (0.15, g(1, 5.76)); TITLE_4 = g(1, 2.80)
# B-roll: (file, src_start, t0, t1, crop_x_center 0-1, chip_text, chip_icon)
BROLL = [
    ("24945.mp4", 0.3, g(1, 5.76), g(1, 7.87), 0.50, "Buying a home in Canada", "house"),
    ("14977.mp4", 1.0, g(2, 2.20), g(3, 0.30), 0.50, "Mortgage pre-approval", "doc"),
    ("23476.mp4", 2.0, g(4, 2.55), g(4, 4.20), 0.62, "Financing a car", "x"),
    ("23420.mp4", 0.5, g(4, 4.20), g(4, 5.85), 0.50, "New furniture", "x"),
    ("46977.mp4", 0.5, g(5, 2.10), g(5, 3.80), 0.50, "Not just the interest rate", "pct"),
    ("5660.mp4", 0.8, g(6, 1.40), g(6, 3.35), 0.40, "Switching jobs?", "brief"),
    ("33357.mp4", 0.8, g(7, 0.00), g(8, 0.90), 0.50, "Make informed decisions", "check"),
]
CARD_W, CARD_H, CARD_CY = 940, 1120, 830
BUDGET = (g(3, 0.30), g(3, 2.145))
WARN1 = (g(4, 6.00), g(4, 9.21), "Before closing", "Big purchases can affect your mortgage qualification")
CHECK = (g(5, 4.55), g(5, 10.33), "Always review", ["Terms", "Conditions", "Prepayment privileges", "Penalties", "Other features"],
         [g(5, 5.62), g(5, 6.30), g(5, 7.12), g(5, 8.56), g(5, 9.32)])
PRO = (g(6, 3.45), g(6, 5.12))
WARN2 = (g(6, 5.12), g(6, 7.867), "Job change?", "It may affect your mortgage approval")
BANNER_D = [g(2, 2.15) - TIPS[0][0], g(4, 2.5) - TIPS[1][0], g(5, 2.05) - TIPS[2][0], g(6, 1.35) - TIPS[3][0]]

# framing: per-segment base zoom (alternating to make jump cuts read as deliberate) + emphasis punch-ins
BASE_Z = [1.40, 1.48, 1.62, 1.45, 1.45, 1.60, 1.45, 1.48, 1.42, 1.58]
PUNCH = [(g(2, 0.0), g(2, 2.15), 1.64), (g(6, 3.45), g(6, 5.12), 1.66), (g(8, 3.3), SPEECH_END + 9, 1.70)]

# ---------------- drawing helpers ----------------
def rrect(size, r, fill):
    im = Image.new("RGBA", size, (0, 0, 0, 0)); ImageDraw.Draw(im).rounded_rectangle([0, 0, size[0]-1, size[1]-1], r, fill=fill); return im
def shadowed(im, blur=18, off=(0, 10), alpha=110):
    pad = blur * 3
    sh = Image.new("RGBA", (im.width + 2*pad, im.height + 2*pad), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh.paste(blk, (pad + off[0], pad + off[1]), blk); sh = sh.filter(ImageFilter.GaussianBlur(blur)); sh.alpha_composite(im, (pad, pad))
    return sh
def paste(layer, im, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if scale <= 0.01 or alpha <= 0.01: return
    if abs(scale - 1) > 1e-3: im = im.resize((max(1, int(im.width*scale)), max(1, int(im.height*scale))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    layer.alpha_composite(im, (int(cx - im.width/2), int(cy - im.height/2)))
def tw(font, s): return font.getlength(s)

def icon(d, kind, cx, cy, r):
    if kind == "check":
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=GREEN)
        d.line([(cx - r*0.45, cy + r*0.02), (cx - r*0.1, cy + r*0.38), (cx + r*0.5, cy - r*0.35)], fill=WHITE, width=max(4, int(r/4)), joint="curve")
    elif kind == "x":
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=CORAL); k = r * 0.38
        for s in (1, -1): d.line([(cx - k, cy - s*k), (cx + k, cy + s*k)], fill=WHITE, width=max(4, int(r/4)))
    elif kind == "house":
        s = r; d.polygon([(cx, cy - s), (cx - s, cy - s*0.05), (cx + s, cy - s*0.05)], fill=AMBER)
        d.rectangle([cx - s*0.7, cy - s*0.1, cx + s*0.7, cy + s*0.8], fill=AMBER); d.rectangle([cx - s*0.18, cy + s*0.3, cx + s*0.18, cy + s*0.8], fill=NAVY)
    elif kind == "doc":
        s = r; d.rounded_rectangle([cx-s*0.75, cy-s, cx+s*0.75, cy+s], 5, fill=WHITE)
        for k in range(3): d.line([cx-s*0.45, cy-s*0.5+k*s*0.45, cx+s*0.45, cy-s*0.5+k*s*0.45], fill=NAVY, width=4)
    elif kind == "pct":
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=AMBER); d.text((cx, cy+2), "%", font=F("Black", int(r*1.3)), fill=NAVY, anchor="mm")
    elif kind == "brief":
        s = r; d.rounded_rectangle([cx-s, cy-s*0.55, cx+s, cy+s*0.8], 8, fill=AMBER)
        d.rounded_rectangle([cx-s*0.38, cy-s*0.9, cx+s*0.38, cy-s*0.45], 6, outline=AMBER, width=6); d.line([cx-s, cy+s*0.05, cx+s, cy+s*0.05], fill=NAVY, width=4)
    elif kind == "warn":
        d.polygon([(cx, cy - r), (cx - r*1.1, cy + r*0.85), (cx + r*1.1, cy + r*0.85)], fill=AMBER)
        d.text((cx, cy + r*0.22), "!", font=F("Black", int(r*1.15)), fill=NAVY, anchor="mm")
    elif kind == "chat":
        d.rounded_rectangle([cx-r, cy-r*0.8, cx+r, cy+r*0.45], 14, fill=WHITE); d.polygon([(cx-r*0.45, cy+r*0.4), (cx-r*0.7, cy+r*0.95), (cx-r*0.05, cy+r*0.4)], fill=WHITE)
        for k in (-1, 0, 1): d.ellipse([cx+k*r*0.45-7, cy-r*0.18-7, cx+k*r*0.45+7, cy-r*0.18+7], fill=NAVY)

def chip_img(text, ic=None, bg=NAVY, fg=WHITE, size=46):
    font = F("ExtraBold", size); h = int(size * 1.95); padx = 36; iw = int(h * 0.8) if ic else 0
    im = rrect((int(tw(font, text)) + 2*padx + iw, h), h // 2, bg + (245,)); d = ImageDraw.Draw(im)
    if ic: icon(d, ic, padx + iw*0.36, h/2, int(h*0.29))
    d.text((padx + iw, h/2), text, font=font, fill=fg, anchor="lm")
    return shadowed(im, blur=12, off=(0, 6), alpha=120)

def panel(title, body_h, pw=920, hcol=NAVY):
    im = rrect((pw, 120 + body_h), 42, (255, 255, 255, 242)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw-1, 116], 42, fill=hcol + (255,)); d.rectangle([0, 72, pw-1, 116], fill=hcol + (255,))
    return im, d

def kicker_img():
    font = F("ExtraBold", 40); t = "HOME BUYING IN CANADA"
    im = rrect((int(tw(font, t)) + 140, 86), 43, RED + (245,)); d = ImageDraw.Draw(im)
    icon(d, "house", 52, 41, 24); d.text((92, 43), t, font=font, fill=WHITE, anchor="lm")
    return shadowed(im, blur=14, off=(0, 6), alpha=120)
def title_img(p):
    im = Image.new("RGBA", (980, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 979, 419], 46, fill=NAVY + (245,))
    s = ease_out_back(p)
    big = Image.new("RGBA", (300, 300), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
    bd.ellipse([10, 10, 290, 290], fill=AMBER); bd.text((150, 158), "4", font=F("Black", 210), fill=NAVY, anchor="mm")
    if s > 0.02: big = big.resize((max(1, int(300*s)), max(1, int(300*s))), Image.BICUBIC); im.alpha_composite(big, (int(190 - big.width/2), int(210 - big.height/2)))
    d.text((360, 120), "THINGS", font=F("Black", 112), fill=WHITE, anchor="lm")
    d.text((364, 230), "every home buyer", font=F("Bold", 54), fill=(225, 232, 245), anchor="lm")
    d.text((364, 300), "should know", font=F("Bold", 54), fill=AMBER, anchor="lm")
    return shadowed(im, blur=24, off=(0, 12), alpha=130)

def banner_img(n, text):
    font = F("Black", 64); w = max(760, int(tw(font, text)) + 120)
    im = Image.new("RGBA", (w, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 70, w-1, 299], 40, fill=NAVY + (245,))
    d.rounded_rectangle([w/2 - 150, 0, w/2 + 150, 120], 60, fill=AMBER)
    d.text((w/2, 62), f"TIP {n:02d}", font=F("Black", 66), fill=NAVY, anchor="mm")
    d.text((w/2, 215), text, font=font, fill=WHITE, anchor="mm")
    return shadowed(im, blur=22, off=(0, 12), alpha=130)

def tracker_img(k, text):
    font = F("ExtraBold", 34); label = f"TIP {k+1}/4  ·  {text.upper()}" if k < 4 else "REMEMBER"
    w = int(tw(font, label)) + 70
    im = rrect((w, 104), 30, (0, 0, 0, 150)); d = ImageDraw.Draw(im)
    d.text((34, 34), label, font=font, fill=WHITE, anchor="lm")
    seg = (w - 68) / 4
    for i in range(4):
        x0 = 34 + i * seg
        d.rounded_rectangle([x0, 70, x0 + seg - 10, 80], 5, fill=AMBER if i <= k else (255, 255, 255, 90))
    return im

def budget_img(p):
    im, d = panel("", 370); pw = im.width
    d.text((pw/2, 58), "Know your budget", font=F("ExtraBold", 52), fill=WHITE, anchor="mm")
    d.text((pw/2, 175), "How much can you afford?", font=F("Bold", 46), fill=NAVY, anchor="mm")
    x0, x1, y = 70, pw - 70, 318
    for i, col in enumerate([GREEN, AMBER, CORAL]):
        a = x0 + (x1 - x0) * i / 3; b = x0 + (x1 - x0) * (i + 1) / 3
        d.rounded_rectangle([a + (0 if i == 0 else -20), y, b + (0 if i == 2 else 20), y + 44], 22, fill=col)
    for i, col in enumerate([GREEN, AMBER, CORAL]):
        a = x0 + (x1 - x0) * i / 3; b = x0 + (x1 - x0) * (i + 1) / 3
        if i: d.rectangle([a - 2, y, a + 2, y + 44], fill=WHITE)
    d.text((x0 + 10, y + 82), "Comfortable", font=F("Bold", 34), fill=GREEN, anchor="lm")
    d.text((x1 - 10, y + 82), "Stretched", font=F("Bold", 34), fill=CORAL, anchor="rm")
    mx = x0 + (x1 - x0) * (0.85 - 0.62 * ease_out(p))      # marker settles in the green zone
    d.polygon([(mx - 22, y - 34), (mx + 22, y - 34), (mx, y - 4)], fill=NAVY)
    d.rounded_rectangle([mx - 70, y - 96, mx + 70, y - 40], 18, fill=NAVY); d.text((mx, y - 68), "$$$", font=F("Black", 36), fill=AMBER, anchor="mm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def warn_img(head, body):
    font = F("Bold", 48); words = body.split(); lines, cur = [], ""
    for w_ in words:
        if cur and tw(font, cur + " " + w_) > 760: lines.append(cur); cur = w_
        else: cur = (cur + " " + w_).strip()
    lines.append(cur)
    im, d = panel("", 60 + 64 * len(lines), hcol=(196, 58, 40)); pw = im.width
    icon(d, "warn", 90, 60, 34)
    d.text((pw/2 + 30, 60), head, font=F("ExtraBold", 54), fill=WHITE, anchor="mm")
    for i, ln in enumerate(lines): d.text((pw/2, 120 + 62 + 64 * i), ln, font=font, fill=NAVY, anchor="mm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def checklist_img(title, items, shown, pops):
    row = 96; im, d = panel("", row * len(items) + 30); pw = im.width
    d.text((pw/2, 58), title, font=F("ExtraBold", 52), fill=WHITE, anchor="mm")
    for i, it in enumerate(items):
        y = 135 + i * row + row / 2 - 10
        if i < shown:
            s = pops[i]; ic = Image.new("RGBA", (90, 90), (0, 0, 0, 0)); icon(ImageDraw.Draw(ic), "check", 45, 45, 34)
            ic = ic.resize((max(1, int(90*s)), max(1, int(90*s))), Image.BICUBIC); im.alpha_composite(ic, (int(90 - ic.width/2), int(y - ic.height/2)))
            d.text((155, y), it, font=F("Bold", 52), fill=NAVY, anchor="lm")
        else:
            d.ellipse([90-30, y-30, 90+30, y+30], outline=(200, 205, 215), width=5)
            d.text((155, y), it, font=F("Bold", 52), fill=(200, 206, 216), anchor="lm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def pro_img():
    im = rrect((900, 250), 44, GREEN + (248,)); d = ImageDraw.Draw(im)
    d.ellipse([40, 55, 180, 195], fill=NAVY); icon(d, "chat", 110, 128, 40)
    d.text((210, 92), "Speak with your", font=F("Bold", 50), fill=WHITE, anchor="lm")
    d.text((210, 160), "mortgage professional", font=F("Black", 58), fill=NAVY, anchor="lm")
    return shadowed(im, blur=22, off=(0, 12), alpha=120)

def endcard_img():
    im = Image.new("RGBA", (W, 1500), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    icon(d, "house", W/2, 110, 95)
    d.text((W/2, 300), "Before you buy, remember", font=F("Black", 66), fill=WHITE, anchor="mm")
    items = ["Get pre-approved first", "Avoid big purchases before closing", "Review terms, not just the rate", "Talk to a pro before changing jobs"]
    for i, it in enumerate(items):
        y = 440 + i * 128
        d.rounded_rectangle([70, y - 50, W - 70, y + 50], 50, fill=(255, 255, 255, 235))
        d.ellipse([92, y - 36, 164, y + 36], fill=AMBER); d.text((128, y + 2), str(i + 1), font=F("Black", 44), fill=NAVY, anchor="mm")
        d.text((190, y), it, font=F("Bold", 40), fill=NAVY, anchor="lm")
    d.text((W/2, 1010), "Thanks for watching!", font=F("Black", 80), fill=AMBER, anchor="mm")
    for i, (lab, col) in enumerate((("LIKE", CORAL), ("SHARE", GREEN), ("FOLLOW", AMBER))):
        cx = W/2 + (i - 1) * 290
        d.rounded_rectangle([cx-130, 1110, cx+130, 1210], 50, fill=col)
        d.text((cx, 1160), lab, font=F("Black", 46), fill=NAVY if col == AMBER else WHITE, anchor="mm")
    d.text((W/2, 1300), "for more home-buying tips", font=F("Bold", 44), fill=(225, 232, 245), anchor="mm")
    return im

# ---------------- captions (word-synced, active-word highlight) ----------------
KEY = set("four important home buyer canada mortgage pre-approval afford big purchases car furniture closing qualification interest rate "
          "terms conditions prepayment privileges penalties features switching job professional approval informed decisions financial stress".split())
def build_words():
    raw = json.load(open(f"{S}/src/words.json")); out = []
    for c in range(1, 9):
        ws = raw[str(c)]
        merged = []
        for s, e, w in ws:
            w = w.strip()
            if w.startswith("-") and merged: merged[-1] = [merged[-1][0], e, merged[-1][2] + w]; continue
            merged.append([s, e, {"hunt.": "hunt,", "rate.": "rate!"}.get(w, w)])
        for s, e, w in merged:
            for (cc, a, b), s0 in zip(SEGS, STARTS):
                if cc == c and a - 0.15 <= (s + e) / 2 <= b + 0.05:
                    out.append([s0 + max(s, a) - a, s0 + min(e, b) - a, w]); break
    return out
SPLITS = [2, 3, 3, 3, 4, 2, 2, 4,      # intro
          2, 3, 3, 2, 2, 3,                  # tip 1
          5, 3,
          1, 2, 2, 4, 1, 2, 4, 2, 1,         # tip 2
          1, 4, 3, 2, 2, 1, 2, 1, 3,         # tip 3
          2, 4, 3, 2, 3, 4, 3,               # tip 4
          1, 3, 4, 3, 2, 3, 2]               # outro
def phrases(words):
    if sum(SPLITS) == len(words):
        out, i = [], 0
        for k in SPLITS: out.append(words[i:i + k]); i += k
        return out
    print("caption split mismatch", sum(SPLITS), len(words))
    ph, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        brk = w[2][-1] in ".,?!" or len(cur) >= 4 or nxt is None or nxt[0] - w[1] > 0.35 or len(" ".join(x[2] for x in cur)) > 22
        if brk: ph.append(cur); cur = []
    return ph
CAP_Y = 1610
def caption_img(ph, active):
    font = F("ExtraBold", 70); sw = 7; gap = tw(font, " ")
    toks = [w[2] for w in ph]; widths = [tw(font, t) for t in toks]
    total = sum(widths) + gap * (len(toks) - 1)
    im = Image.new("RGBA", (W, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = (W - total) / 2; y = 75
    for i, (t, wd) in enumerate(zip(toks, widths)):
        bare = re.sub(r"[^a-z\-]", "", t.lower())
        if i == active:
            d.rounded_rectangle([x - 14, y - 50, x + wd + 14, y + 48], 20, fill=AMBER)
            d.text((x, y), t, font=font, fill=NAVY, anchor="lm")
        else:
            d.text((x, y), t, font=font, fill=AMBER if bare in KEY else WHITE, anchor="lm", stroke_width=sw, stroke_fill=(0, 0, 0))
        x += wd + gap
    return shadowed(im, blur=10, off=(0, 4), alpha=120)

# ---------------- sources ----------------
def reader(cmd, w, h):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w*h*3*4)
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()
def broll_reader(spec):
    f, ss, t0, t1, cx = spec[:5]; dur = t1 - t0 + 0.3
    cw = int(720 * CARD_W / CARD_H); x = max(0, min(1280 - cw, int(cx * 1280 - cw / 2)))
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", f"{dur:.3f}", "-i", f"{DL}/broll/{f}", "-vf",
           f"fps=30,scale=1280:720,crop={cw}:720:{x}:0,scale={CARD_W}:{CARD_H}:flags=lanczos,eq=contrast=1.05:saturation=1.12,unsharp=5:5:0.5",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return reader(cmd, CARD_W, CARD_H)

def framing():
    faces = []
    for k in range(4): faces += json.load(open(f"{OUT}/enh{k}.mp4.faces.json"))
    centers = []
    for s0, s1, _ in seg_bounds():
        fs = [f for f in faces[int(round(s0 * FPS)):int(round(s1 * FPS))] if f]
        centers.append((float(np.median([f[0] for f in fs])), float(np.median([f[1] for f in fs]))) if fs else (540, 500))
    return centers
def seg_index(t):
    for i, (s0, s1, _) in enumerate(seg_bounds()):
        if t < s1: return i
    return len(SEGS) - 1
def crop_frame(fr, t, centers):
    i = seg_index(min(t, SPEECH_END - 1e-3)); s0, s1, _ = seg_bounds()[i]
    z = BASE_Z[i] + 0.04 * clamp((t - s0) / max(0.1, s1 - s0))
    for a, b, zz in PUNCH:
        if a <= t < b: z = zz + 0.02 * clamp((t - a) / max(0.1, b - a))
    fx, fy = centers[i]; w2, h2 = W / z, H / z
    x0 = min(max(fx - w2 / 2, 0), W - w2); y0 = min(max(fy - 0.22 * h2, 0), H - h2)
    M = np.array([[z, 0, -x0 * z], [0, z, -y0 * z]], np.float32)
    out = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    bl = cv2.GaussianBlur(out, (0, 0), 1.2)
    return cv2.addWeighted(out, 1.35, bl, -0.35, 0)

def main():
    centers = framing()
    aroll = reader(["ffmpeg", "-v", "error", "-i", f"{OUT}/aroll.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], W, H)
    words = build_words(); PH = phrases(words)
    cap_cache = {}
    chips = [chip_img(b[5], b[6]) for b in BROLL]
    tracks = {k: tracker_img(k, TIPS[k][1] if k < 4 else "") for k in range(5)}
    banners = [banner_img(i + 1, t) for i, (_, t) in enumerate(TIPS)]
    KICK, END, PROI = kicker_img(), endcard_img(), pro_img()
    W1, W2 = warn_img(*WARN1[2:]), warn_img(*WARN2[2:])
    mask = Image.new("L", (CARD_W, CARD_H), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W-1, CARD_H-1], 46, fill=255)
    border = Image.new("RGBA", (CARD_W + 16, CARD_H + 16), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle([0, 0, CARD_W + 15, CARD_H + 15], 54, fill=(255, 255, 255, 255)); border = shadowed(border, 26, (0, 16), 150)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", f"{OUT}/video_noaudio.mp4"], stdin=subprocess.PIPE)
    br_it, last_br, end_bg, last = {}, {}, None, None
    for n in range(N):
        t = n / FPS
        fr = next(aroll, None)
        if fr is None: fr = last
        last = fr
        L = Image.fromarray(crop_frame(fr, t, centers)).convert("RGBA")
        # B-roll cards
        for i, b in enumerate(BROLL):
            t0, t1 = b[2], b[3]
            if t0 <= t < t1:
                if i not in br_it: br_it[i] = broll_reader(b)
                c = next(br_it[i], None); c = last_br[i] if c is None else c; last_br[i] = c
                card = Image.fromarray(c)
                bg = card.resize((54, 64), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR)
                bg = Image.fromarray((np.asarray(bg).astype(np.float32) * 0.5).astype(np.uint8)).convert("RGBA")
                tin, tout = (t - t0) / 0.28, (t1 - t) / 0.2
                a = min(1, ease_out(tin), ease_io(tout))
                s = 0.88 + 0.12 * ease_out_back(tin) if tin < 1 else 1.0 + 0.03 * (t - t0 - 0.28) / (t1 - t0)
                L = Image.blend(L, bg, a) if a < 1 else bg
                cc = card.convert("RGBA"); cc.putalpha(mask)
                paste(L, border, W/2, CARD_CY + 8, s, a); paste(L, cc, W/2, CARD_CY, s, a)
                paste(L, chips[i], W/2, CARD_CY + CARD_H/2 - 6, ease_out_back((t - t0 - 0.22) / 0.35), a)
        # hook title
        a0, a1 = TITLE_K
        if a0 <= t < a1:
            paste(L, KICK, W/2 + 80 * (1 - ease_out((t - a0) / 0.4)), 300, 1.0, env(t, a0, a1))
            if t >= TITLE_4 - 0.05:
                p = (t - TITLE_4) / 0.45
                paste(L, title_img(clamp(p * 1.2)), W/2, 1180 + 70 * (1 - ease_out(p)), 0.9 + 0.1 * ease_out_back(p), env(t, TITLE_4, a1))
        # tip banners + tracker
        for k, (t0, txt) in enumerate(TIPS):
            t1 = t0 + BANNER_D[k]
            if t0 <= t < t1:
                p = (t - t0) / 0.4
                paste(L, banners[k], W/2, 1150 + 60 * (1 - ease_out(p)), 0.85 + 0.15 * ease_out_back(p), env(t, t0, t1, 0.3, 0.2))
        if TIPS[0][0] <= t < SPEECH_END:
            k = 4 if t >= OUTRO else max(i for i, (t0, _) in enumerate(TIPS) if t >= t0)
            st = OUTRO if k == 4 else TIPS[k][0]
            im = tracks[k]; p = (t - st) / 0.35
            paste(L, im, 40 + im.width / 2 - 50 * (1 - ease_out(p)), 110, 1.0, ease_out(p))
        # budget meter
        a0, a1 = BUDGET
        if a0 <= t < a1: paste(L, budget_img((t - a0) / 1.1), W/2, 1170 + 70 * (1 - ease_out((t - a0) / 0.4)), 1.0, env(t, a0, a1))
        # warnings
        for (a0, a1, *_), im in ((WARN1, W1), (WARN2, W2)):
            if a0 <= t < a1:
                p = (t - a0) / 0.4; wob = 3 * np.sin((t - a0) * 30) * max(0, 1 - (t - a0) / 0.5)
                paste(L, im, W/2, 1180 + 70 * (1 - ease_out(p)), 0.9 + 0.1 * ease_out_back(p), env(t, a0, a1), rot=wob)
        # checklist
        a0, a1, title, items, tms = CHECK
        if a0 <= t < a1:
            shown = sum(1 for x in tms if t >= x); pops = [ease_out_back((t - x) / 0.3) for x in tms]
            paste(L, checklist_img(title, items, shown, pops), W/2, 1220 + 70 * (1 - ease_out((t - a0) / 0.4)), 1.0, env(t, a0, a1))
        # mortgage professional
        a0, a1 = PRO
        if a0 <= t < a1:
            p = (t - a0) / 0.4; paste(L, PROI, W/2 - 200 * (1 - ease_out(p)), 1260, 1.0, env(t, a0, a1))
        # captions
        if t < SPEECH_END - 0.05:
            for pi, ph in enumerate(PH):
                st = ph[0][0] - 0.05; en = PH[pi + 1][0][0] - 0.05 if pi + 1 < len(PH) else ph[-1][1] + 0.4
                en = min(en, ph[-1][1] + 0.6)
                if st <= t < en:
                    act = max([i for i, w in enumerate(ph) if t >= w[0] - 0.03] or [0])
                    if t > ph[-1][1] + 0.05: act = -1
                    key = (pi, act)
                    if key not in cap_cache: cap_cache[key] = caption_img(ph, act)
                    p = (t - st) / 0.15
                    paste(L, cap_cache[key], W/2, CAP_Y, 0.9 + 0.1 * ease_out(p), ease_out(p * 1.5))
                    break
        # end card
        if t >= SPEECH_END - 0.25:
            if end_bg is None:
                eb = L.convert("RGB").resize((108, 192), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
                end_bg = eb.convert("RGBA"); end_bg.alpha_composite(Image.new("RGBA", (W, H), NAVY + (190,)))
            L = Image.blend(L, end_bg, ease_io((t - SPEECH_END + 0.25) / 0.45))
            if t >= SPEECH_END:
                p = (t - SPEECH_END) / 0.5
                paste(L, END, W/2, 980 + 70 * (1 - ease_out(p)), 0.92 + 0.08 * ease_out_back(p), ease_out(p))
        d = ImageDraw.Draw(L)
        d.rectangle([0, 0, W, 12], fill=(255, 255, 255, 70)); d.rectangle([0, 0, int(W * min(1, t / SPEECH_END)), 12], fill=AMBER + (255,))
        enc.stdin.write(L.convert("RGB").tobytes())
        if n % 150 == 0: print(f"frame {n}/{N}", flush=True)
    enc.stdin.close(); enc.wait()
    ev = {"TOTAL": TOTAL, "SPEECH_END": SPEECH_END, "TITLE_K": TITLE_K[0], "TITLE_4": TITLE_4, "TIPS": [x[0] for x in TIPS],
          "BROLL": [b[2] for b in BROLL], "BUDGET": BUDGET[0], "WARN": [WARN1[0], WARN2[0]], "CHECK": [CHECK[0]] + CHECK[4], "PRO": PRO[0]}
    json.dump(ev, open(f"{OUT}/events.json", "w"))

if __name__ == "__main__":
    main()
