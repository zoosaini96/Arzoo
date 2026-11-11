"""Compose the final 1080x1920 explainer: layouts, B-roll, motion graphics, captions.
Writes video-only to out/video.mp4 and an SFX cue list to out/sfx.json."""
import cv2, numpy as np, json, subprocess, math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__)); os.chdir(S)
os.makedirs("out", exist_ok=True)
W, H, FPS = 1080, 1920, 30
PREVIEW = len(sys.argv) > 1  # write a few stills only

FD = "/usr/share/fonts/truetype/montserrat/"
def font(w, size): return ImageFont.truetype(FD + f"Montserrat-{w}.ttf", size)

NAVY = (14, 27, 61); GOLD = (255, 201, 60); WHITE = (255, 255, 255); BEIGE = (232, 211, 176)
INK = (20, 20, 28)

# ------------------------------------------------------------------ timeline
# (clip, src_in, src_out)
SEGS = [(1, 0.00, 5.95), (1, 6.62, 11.30), (2, 0.00, 4.76), (3, 0.25, 9.20),
        (4, 0.10, 3.79), (5, 0.03, 5.22), (6, 0.00, 5.65)]
OUTRO = 2.2
offs = []; t = 0
for c, a, b in SEGS: offs.append(t); t += b - a
VOICE_END = t; TOTAL = t + OUTRO
def T(seg, src): return offs[seg] + src - SEGS[seg][1]   # source time -> final time

# presenter crop anchor (waist row per clip, from segmentation)
WAIST = {1: 582, 2: 602, 3: 612, 4: 582, 5: 628, 6: 656}

# captions: (seg, src_start, src_end, text) ; *word* = highlight
CAP = [
 (0, 0.00, 1.18, "SAVED UP THE REQUIRED"), (0, 1.18, 2.68, "*DOWN PAYMENT?*"),
 (0, 2.68, 3.98, "THINK YOU'RE COMPLETELY"), (0, 3.98, 5.95, "READY TO *BUY A HOME?*"),
 (1, 7.48, 8.38, "THERE'S SOMETHING ELSE"),
 (1, 8.38, 9.60, "YOU NEED TO *BUDGET* FOR"),
 (2, 0.00, 1.52, "BESIDES THE *DOWN PAYMENT,*"), (2, 1.52, 3.18, "THERE ARE *ADDITIONAL EXPENSES*"),
 (2, 3.18, 4.76, "CALLED *CLOSING COSTS*"),
 (3, 0.25, 1.40, "LIKE *LENDER FEES,*"), (3, 1.40, 2.55, "*HOME INSPECTION* FEES,"),
 (3, 2.55, 3.65, "*TITLE INSURANCE,*"), (3, 3.65, 4.85, "*TITLE REGISTRATION,*"),
 (3, 4.85, 6.40, "*PROPERTY TAX* ADJUSTMENTS"), (3, 6.40, 7.60, "AND SOMETIMES"),
 (3, 7.60, 9.20, "AN *APPRAISAL FEE* TOO"),
 (4, 0.10, 1.74, "SO BEFORE YOU BUY,"), (4, 1.74, 2.66, "FOR *CLOSING COSTS*"),
 (4, 2.66, 3.79, "KEEP A *SEPARATE BUDGET*"),
 (5, 0.03, 1.98, "CHECK WITH YOUR *MORTGAGE PROFESSIONAL*"), (5, 1.98, 3.00, "OR *LAWYER*"),
 (5, 3.00, 5.22, "AND CONFIRM YOUR *ESTIMATED* CLOSING COSTS"),
 (6, 0.00, 1.52, "GOT ANY QUESTIONS"), (6, 1.52, 3.52, "ABOUT *CLOSING COSTS?*"),
 (6, 3.52, 5.07, "FEEL FREE TO *REACH OUT TO ME!*"),
]
CAPS = [(T(s, a), T(s, b), txt) for s, a, b, txt in CAP]

# layout windows (final time): split-screen with top content
SPLITS = [  # (t0, t1, kind, arg)
 (T(0, 3.98), T(0, 5.95), "broll", "4009"),
 (T(2, 0.00), T(2, 4.76), "broll", "18263"),
 (T(3, 0.25), T(3, 9.20), "checklist", None),
 (T(4, 0.10), T(4, 3.79), "broll", "1717715134"),
 (T(5, 0.03), T(5, 2.60), "broll", "4809"),
 (T(5, 2.60), T(5, 5.22), "broll", "241"),
]
LABELS = {"4009": "YOUR DREAM HOME", "18263": "+ ADDITIONAL EXPENSES", "1717715134": "SEPARATE BUDGET",
          "4809": "MORTGAGE PROFESSIONAL", "241": "LAWYER"}
CHECK = [("Lender fees", 0.58), ("Home inspection fees", 1.54), ("Title insurance", 2.68),
         ("Title registration", 3.76), ("Property tax adjustments", 5.02), ("Appraisal fee (sometimes)", 7.76)]

SFX = []
def sfx(t, name, vol): SFX.append({"t": round(t, 3), "f": name, "v": vol})
sfx(0.05, "1490", 0.45)                       # intro whoosh
sfx(T(0, 1.25), "2354", 0.55)                 # down payment badge
for t0, t1, k, a in SPLITS:
    if k != "checklist" or True: sfx(max(0, t0 - 0.12), "1492", 0.35)
sfx(T(1, 6.95), "1489", 0.6)                  # WAIT punch-in
sfx(T(1, 9.70), "2903", 0.55)                 # CLOSING COSTS slam
sfx(T(2, 0.25), "1993", 0.45)                 # coins
for _, s in CHECK: sfx(T(3, s), "2357", 0.6)  # checklist pops
sfx(T(4, 2.75), "1120", 0.7)                  # budget stamp
sfx(T(6, 0.25), "2354", 0.5)                  # CTA pop
sfx(T(6, 5.12), "938", 0.4)                   # thank you
sfx(VOICE_END + 0.05, "1490", 0.4)            # outro whoosh

# ------------------------------------------------------------------ easing / helpers
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def paste(canvas, el, cx, cy, scale=1.0, alpha=1.0):
    """alpha-composite RGBA PIL element centred at (cx,cy) onto RGB PIL canvas."""
    if scale <= 0.01 or alpha <= 0.01: return
    if abs(scale - 1) > 1e-3:
        el = el.resize((max(1, int(el.width * scale)), max(1, int(el.height * scale))), Image.LANCZOS)
    if alpha < 1:
        a = el.getchannel("A").point(lambda v: int(v * alpha)); el = el.copy(); el.putalpha(a)
    canvas.alpha_composite(el, (int(cx - el.width / 2), int(cy - el.height / 2)))

def rounded(w, h, r, fill, outline=None, width=0, shadow=True):
    pad = 24 if shadow else 0
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 8, pad + w, pad + h + 8), r, fill=(0, 0, 0, 110))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill, outline=outline, width=width)
    return im, pad

def text_el(txt, f, fill=WHITE, stroke=0, stroke_fill=INK, hl=GOLD):
    """Render text (supports *highlight*) to a tight RGBA image."""
    parts = []; on = False
    for i, chunk in enumerate(txt.split("*")):
        if chunk: parts.append((chunk, hl if on else fill))
        on = not on
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    wsum = sum(d.textlength(p, font=f) for p, _ in parts)
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(wsum) + 2 * stroke + 4, asc + desc + 2 * stroke + 4), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im); x = stroke + 2
    for p, col in parts:
        dr.text((x, stroke + 2), p, font=f, fill=col, stroke_width=stroke, stroke_fill=stroke_fill)
        x += d.textlength(p, font=f)
    return im

def wrap_caption(txt, f, maxw):
    words = txt.split(" "); lines = []; cur = ""
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for w_ in words:
        test = (cur + " " + w_).strip()
        if d.textlength(test.replace("*", ""), font=f) > maxw and cur: lines.append(cur); cur = w_
        else: cur = test
    lines.append(cur)
    # carry highlight state across line breaks
    out = []; open_ = False
    for ln in lines:
        s = ("*" if open_ else "") + ln
        if ln.count("*") % 2: open_ = not open_
        if open_: s += "*"
        out.append(s)
    return out

_cache = {}
def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]

# ------------------------------------------------------------------ icons
def house_icon(size, col=GOLD, width=14):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = size; w = width
    d.line([(s * .1, s * .5), (s * .5, s * .12), (s * .9, s * .5)], fill=col, width=w, joint="curve")
    d.line([(s * .2, s * .42), (s * .2, s * .88), (s * .8, s * .88), (s * .8, s * .42)], fill=col, width=w, joint="curve")
    d.rectangle((s * .42, s * .6, s * .58, s * .88), fill=col)
    return im

def check_icon(size, bg=GOLD, fg=NAVY):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=bg)
    d.line([(size * .27, size * .52), (size * .44, size * .69), (size * .74, size * .34)], fill=fg, width=max(3, size // 9), joint="curve")
    return im

def chat_icon(size, col=NAVY):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((size * .08, size * .12, size * .92, size * .72), size * .16, fill=col)
    d.polygon([(size * .25, size * .7), (size * .25, size * .92), (size * .48, size * .7)], fill=col)
    for i in range(3): d.ellipse((size * (.28 + i * .17), size * .37, size * (.36 + i * .17), size * .45), fill=GOLD)
    return im

# ------------------------------------------------------------------ sources
class Clip:
    def __init__(self, path):
        cap = cv2.VideoCapture(path); self.f = []
        while True:
            ok, fr = cap.read()
            if not ok: break
            self.f.append(fr)
    def at(self, t):
        return self.f[min(len(self.f) - 1, max(0, int(round(t * FPS))))]

clips = {i: Clip(f"work/clean{i}.mp4") for i in range(1, 6)}
clips[6] = Clip("work/clean6_fixed.mp4")  # re-timed: "reach out to me"
brolls = {k: Clip(f"broll/{k}.mp4") for k in ["4009", "18263", "1717715134", "4809", "241"]}

def sharpen(img):
    bl = cv2.GaussianBlur(img, (0, 0), 1.2)
    return cv2.addWeighted(img, 1.35, bl, -0.35, 0)

def presenter_full(src, zoom, cy_frac=0.42):
    """src 720x1280 -> 1080x1920 with zoom about a point (face-ish)."""
    h, w = src.shape[:2]
    cw, ch = w / zoom, h / zoom
    cx = w / 2; cy = h * cy_frac
    x0 = clamp(cx - cw / 2, 0, w - cw); y0 = clamp(cy - ch * cy_frac, 0, h - ch)
    M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)

def presenter_half(src, waist, zoom=1.0):
    """upper body crop into 1080x960 panel."""
    h, w = src.shape[:2]
    cw = w / zoom; ch = cw * 960 / 1080
    y0 = clamp(waist - ch * 0.80, 0, h - ch); x0 = (w - cw) / 2
    M = np.float32([[W / cw, 0, -x0 * W / cw], [0, 960 / ch, -y0 * 960 / ch]])
    return cv2.warpAffine(src, M, (W, 960), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)

def broll_panel(key, lt, dur):
    fr = brolls[key].at(lt)
    z = 1.0 + 0.08 * (lt / max(dur, 0.1))  # Ken Burns
    h, w = fr.shape[:2]; cw, ch = 1080 / z, 960 / z
    x0 = (w - cw) / 2; y0 = (h - ch) / 2
    M = np.float32([[1080 / cw, 0, -x0 * 1080 / cw], [0, 960 / ch, -y0 * 960 / ch]])
    return cv2.warpAffine(fr, M, (1080, 960), flags=cv2.INTER_LINEAR)

# ------------------------------------------------------------------ graphic panels
def checklist_panel(lt):
    """lt = time since the checklist split started (seg 3)."""
    im = Image.new("RGBA", (1080, 960), NAVY + (255,)); d = ImageDraw.Draw(im)
    # subtle diagonal stripes
    for x in range(-960, 1080, 60): d.line([(x, 960), (x + 960, 0)], fill=(20, 36, 78, 255), width=18)
    head = cached("ck_head", lambda: text_el("CLOSING COSTS *INCLUDE:*", font("Black", 62)))
    p = ease_out(lt / 0.4)
    paste(im, head, 540, 110 - 40 * (1 - p), alpha=p)
    d.rounded_rectangle((540 - 160 * p, 160, 540 + 160 * p, 168), 4, fill=GOLD)
    src0 = SEGS[3][1]
    for i, (label, s) in enumerate(CHECK):
        k = lt - (s - src0)
        if k < 0: continue
        y = 250 + i * 112
        pp = ease_out(k / 0.35)
        card = cached(("ck", i), lambda: _ck_card(label, i))
        paste(im, card, 540 + 120 * (1 - pp), y, alpha=pp)
        ic = cached("chk", lambda: check_icon(70))
        paste(im, ic, 120 + 120 * (1 - pp), y, scale=0.6 + 0.4 * back(k / 0.35), alpha=pp)
    return im

def _ck_card(label, i):
    card, pad = rounded(840, 92, 24, (255, 255, 255, 245), shadow=True)
    d = ImageDraw.Draw(card)
    d.text((pad + 110, pad + 46), label, font=font("ExtraBold", 44), fill=NAVY, anchor="lm")
    d.text((pad + 800, pad + 46), f"0{i+1}", font=font("Black", 38), fill=(200, 160, 40), anchor="rm")
    return card

# ------------------------------------------------------------------ frame render
CAP_FONT = font("Black", 70)
def caption_el(txt):
    def mk():
        lines = wrap_caption(txt, CAP_FONT, 900)
        ims = [text_el(l, CAP_FONT, stroke=9, stroke_fill=(0, 0, 0)) for l in lines]
        wmax = max(i.width for i in ims); hs = sum(i.height for i in ims) - 14 * (len(ims) - 1)
        out = Image.new("RGBA", (wmax, hs), (0, 0, 0, 0)); y = 0
        for i in ims: out.alpha_composite(i, ((wmax - i.width) // 2, y)); y += i.height - 14
        return out
    return cached(("cap", txt), mk)

def in_split(t):
    for s in SPLITS:
        if s[0] <= t < s[1]: return s
    return None

def seg_at(t):
    for i in range(len(SEGS) - 1, -1, -1):
        if t >= offs[i]: return i
    return 0

def render(fi):
    t = fi / FPS
    if t >= VOICE_END:
        return render_outro(t - VOICE_END)
    si = seg_at(t); c, a, b = SEGS[si]; lt = t - offs[si]; src_t = a + lt
    src = clips[c].at(src_t)
    split = in_split(t)

    # zoom logic (full layout): gentle push, punch-ins hide jump cuts
    zoom = 1.0 + 0.04 * ease_in_out(lt / (b - a))
    if si == 1:
        k = t - T(1, 6.95)
        zoom = 1.08 + (0.22 * back(k / 0.18) if k >= 0 else 0)
        k2 = t - T(1, 9.70)
        if k2 >= 0: zoom = 1.30 - 0.18 * ease_out(k2 / 0.5)
    if si == 6: zoom = 1.12 + 0.05 * ease_in_out(lt / (b - a))
    shake = 0
    if si == 1 and 0 <= t - T(1, 9.70) < 0.3:
        shake = int(14 * math.sin((t - T(1, 9.70)) * 90) * (1 - (t - T(1, 9.70)) / 0.3))

    if split:
        t0, t1, kind, arg = split
        frame = np.zeros((H, W, 3), np.uint8)
        frame[960:] = presenter_half(src, WAIST[c], zoom=1.0 + 0.03 * ease_in_out((t - t0) / (t1 - t0)))
        if kind == "broll":
            top = broll_panel(arg, t - t0, t1 - t0)
            frame[:960] = top
        canvas = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        if kind == "checklist":
            canvas.alpha_composite(checklist_panel(t - t0), (0, 0))
        # slide-in reveal of the top panel on entry
        e = ease_out((t - t0) / 0.3)
        if e < 1:
            full = Image.fromarray(cv2.cvtColor(presenter_full(src, zoom), cv2.COLOR_BGR2RGB)).convert("RGBA")
            cut = int(960 * e)
            full_part = full.crop((0, cut, W, 960 + 0))
            canvas.alpha_composite(full_part, (0, cut)) if cut < 960 else None
        # divider
        d = ImageDraw.Draw(canvas); d.rectangle((0, 954, W, 966), fill=GOLD)
        if kind == "broll":
            lab = cached(("lab", arg), lambda: _label(LABELS[arg]))
            k = t - t0 - 0.15
            paste(canvas, lab, 540, 860 + 40 * (1 - ease_out(k / 0.35)), scale=1, alpha=ease_out(k / 0.3))
            if arg == "1717715134":  # budget stamp
                k = t - T(4, 2.75)
                if k >= 0:
                    st = cached("stamp", _stamp)
                    paste(canvas, st, 540, 420, scale=1.6 - 0.6 * ease_out(k / 0.18), alpha=ease_out(k / 0.12))
        cap_y = 1010 + 0  # just under the divider... placed over presenter shoulders
        cap_y = 1700
    else:
        fr = presenter_full(src, zoom)
        if shake: fr = np.roll(fr, shake, axis=1)
        canvas = Image.fromarray(cv2.cvtColor(sharpen(fr), cv2.COLOR_BGR2RGB)).convert("RGBA")
        cap_y = 1450
        overlays_full(canvas, t, si)

    # captions
    for c0, c1, txt in CAPS:
        if c0 <= t < c1:
            el = caption_el(txt)
            k = t - c0
            sc = 0.8 + 0.2 * back(k / 0.16)
            paste(canvas, el, 540, cap_y, scale=sc, alpha=ease_out(k / 0.08))
            break
    # progress bar
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, int(W * t / VOICE_END), 10), fill=GOLD)
    return canvas

def _label(txt):
    f = font("Black", 46)
    tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(txt, font=f))
    card, pad = rounded(tw + 70, 86, 43, GOLD + (255,))
    ImageDraw.Draw(card).text((pad + (tw + 70) / 2, pad + 44), txt, font=f, fill=NAVY, anchor="mm")
    return card

def _stamp():
    im = Image.new("RGBA", (560, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, 552, 192), 26, outline=(220, 40, 60, 255), width=12)
    d.text((280, 100), "BUDGET IT!", font=font("Black", 82), fill=(220, 40, 60, 255), anchor="mm")
    return im.rotate(-8, resample=Image.BICUBIC, expand=True)

def overlays_full(canvas, t, si):
    # Seg 0: hook title + down payment badge
    if si == 0:
        k = t - 0.05
        title = cached("hook", lambda: _hook())
        paste(canvas, title, 540, 145 - 60 * (1 - ease_out(k / 0.45)), alpha=ease_out(k / 0.3))
        k = t - T(0, 1.25)
        if k >= 0:
            badge = cached("dp", lambda: _badge("DOWN PAYMENT", "SAVED"))
            paste(canvas, badge, 770, 820, scale=back(k / 0.3), alpha=clamp(k / 0.1))
    if si == 1:
        k = t - T(1, 6.95)
        if 0 <= k < T(1, 9.6) - T(1, 6.95):
            wait = cached("wait", lambda: text_el("WAIT!", font("Black", 210), fill=GOLD, stroke=14, stroke_fill=NAVY))
            jit = 6 * math.sin(k * 40) * max(0, 1 - k / 0.5)
            paste(canvas, wait.rotate(-6 + jit, expand=True, resample=Image.BICUBIC), 540, 1150, scale=1.5 - 0.5 * back(k / 0.25), alpha=clamp(k / 0.08))
        k = t - T(1, 9.70)
        if k >= 0:
            cc = cached("cc", _cc_title)
            paste(canvas, cc, 540, 1150, scale=2.0 - 1.0 * ease_out(k / 0.2), alpha=clamp(k / 0.1))
    if si == 6:
        k = t - T(6, 0.25)
        if k >= 0 and t < T(6, 5.07):
            cta = cached("cta", _cta)
            paste(canvas, cta, 540 + 700 * (1 - ease_out(k / 0.4)), 1130)
        k = t - T(6, 5.07)
        if k >= 0:
            ty = cached("ty", lambda: text_el("THANK YOU!", font("Black", 120), fill=WHITE, stroke=10, stroke_fill=NAVY))
            paste(canvas, ty, 540, 1150, scale=back(k / 0.3))

def _hook():
    card, pad = rounded(900, 200, 40, NAVY + (235,))
    d = ImageDraw.Draw(card)
    card.alpha_composite(house_icon(120), (pad + 40, pad + 40))
    d.text((pad + 190, pad + 62), "BUYING A HOME?", font=font("Black", 66), fill=WHITE, anchor="lm")
    d.text((pad + 190, pad + 138), "Don't miss this hidden cost", font=font("Bold", 42), fill=GOLD, anchor="lm")
    return card

def _badge(a, b):
    card, pad = rounded(470, 150, 30, (255, 255, 255, 245))
    card.alpha_composite(check_icon(90), (pad + 22, pad + 30))
    d = ImageDraw.Draw(card)
    d.text((pad + 128, pad + 52), a, font=font("Black", 36), fill=NAVY, anchor="lm")
    d.text((pad + 128, pad + 102), b, font=font("Black", 40), fill=(30, 150, 80), anchor="lm")
    return card

def _cc_title():
    card, pad = rounded(940, 250, 40, GOLD + (255,))
    d = ImageDraw.Draw(card)
    d.text((pad + 470, pad + 90), "CLOSING", font=font("Black", 120), fill=NAVY, anchor="mm")
    d.text((pad + 470, pad + 190), "COSTS", font=font("Black", 96), fill=NAVY, anchor="mm")
    return card

def _cta():
    card, pad = rounded(860, 230, 40, (255, 255, 255, 248))
    card.alpha_composite(chat_icon(140), (pad + 40, pad + 45))
    d = ImageDraw.Draw(card)
    d.text((pad + 210, pad + 80), "QUESTIONS?", font=font("Black", 70), fill=NAVY, anchor="lm")
    d.text((pad + 210, pad + 160), "Send me a message", font=font("Bold", 46), fill=(60, 70, 100), anchor="lm")
    return card

_last = {}
def render_outro(k):
    if "bg" not in _last:
        src = clips[6].at(SEGS[6][2] - 0.05)
        fr = presenter_full(src, 1.17)
        bg = cv2.GaussianBlur(fr, (0, 0), 18)
        _last["bg"] = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB)).convert("RGBA")
    canvas = _last["bg"].copy()
    ov = Image.new("RGBA", (W, H), NAVY + (int(200 * ease_out(k / 0.4)),))
    canvas.alpha_composite(ov)
    paste(canvas, cached("ohouse", lambda: house_icon(220, width=20)), 540, 620, scale=back(k / 0.4), alpha=clamp(k / 0.15))
    l1 = cached("o1", lambda: text_el("PLAN FOR", font("Black", 96)))
    l2 = cached("o2", lambda: text_el("*CLOSING COSTS*", font("Black", 110)))
    paste(canvas, l1, 540, 860 + 50 * (1 - ease_out((k - 0.1) / 0.4)), alpha=ease_out((k - 0.1) / 0.3))
    paste(canvas, l2, 540, 980 + 50 * (1 - ease_out((k - 0.2) / 0.4)), alpha=ease_out((k - 0.2) / 0.3))
    k3 = k - 0.6
    if k3 > 0:
        pill = cached("opill", lambda: _label("SAVE  •  SHARE  •  FOLLOW"))
        paste(canvas, pill, 540, 1180, scale=back(k3 / 0.3))
        sub = cached("osub", lambda: text_el("More home-buying tips coming soon", font("Bold", 44), fill=BEIGE))
        paste(canvas, sub, 540, 1290, alpha=ease_out(k3 / 0.4))
    # fade to black last 0.3s
    fo = clamp((k - (OUTRO - 0.35)) / 0.35)
    if fo > 0: canvas.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fo))))
    return canvas

# ------------------------------------------------------------------ main
NF = int(round(TOTAL * FPS))
json.dump({"sfx": SFX, "segs": SEGS, "offs": offs, "voice_end": VOICE_END, "total": NF / FPS}, open("out/timeline.json", "w"), indent=1)
if PREVIEW:
    ts = [float(x) for x in sys.argv[1].split(",")]
    for tt in ts:
        render(int(tt * FPS)).convert("RGB").save(f"out/prev_{tt:05.2f}.jpg", quality=88)
    print("total", TOTAL); sys.exit()
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "out/video.mp4"], stdin=subprocess.PIPE)
for fi in range(NF):
    p.stdin.write(np.asarray(render(fi).convert("RGB")).tobytes())
    if fi % 150 == 0: print("frame", fi, "/", NF, flush=True)
p.stdin.close(); p.wait(); print("done", NF / FPS)
