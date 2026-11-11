"""Closing-costs explainer, style 2: warm editorial.
Cream / forest green / terracotta palette, EB Garamond + Manrope + DM Mono, warm grade,
sentence-case caption bars, tilted photo-card B-roll, printed receipt list, chapter tags.
Writes out/video.mp4 and out/timeline.json (SFX cues for mixaudio.py)."""
import cv2, numpy as np, json, subprocess, math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__)); os.chdir(S)
os.makedirs("out", exist_ok=True)
W, H, FPS = 1080, 1920, 30
PREVIEW = len(sys.argv) > 1

def garamond(style, size):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/ebgaramond/EBGaramond12-{style}.otf", size)
def manrope(w, size): return ImageFont.truetype(f"/usr/share/fonts/truetype/manrope/Manrope-{w}.ttf", size)
def mono(w, size): return ImageFont.truetype(f"/usr/share/fonts/truetype/dm-mono/DMMono-{w}.ttf", size)

CREAM = (245, 238, 226); PAPER = (250, 247, 240); FOREST = (30, 59, 51); TERRA = (214, 101, 59)
INK = (30, 43, 39); MUTED = (98, 112, 104)

# ------------------------------------------------------------------ timeline (same cut as style 1)
SEGS = [(1, 0.00, 5.95), (1, 6.62, 11.30), (2, 0.00, 4.76), (3, 0.25, 9.20),
        (4, 0.10, 3.79), (5, 0.03, 5.22), (6, 0.00, 5.65)]
OUTRO = 2.4
offs = []; t = 0
for c, a, b in SEGS: offs.append(t); t += b - a
VOICE_END = t; TOTAL = t + OUTRO
def T(seg, src): return offs[seg] + src - SEGS[seg][1]

CAP = [
 (0, 0.00, 1.18, "Saved up the required"), (0, 1.18, 2.68, "*down payment?*"),
 (0, 2.68, 3.98, "Think you're completely"), (0, 3.98, 5.95, "ready to *buy a home?*"),
 (1, 7.48, 8.38, "There's something else"), (1, 8.38, 9.60, "you need to *budget* for"),
 (2, 0.00, 1.52, "Besides the *down payment,*"), (2, 1.52, 3.18, "there are *additional expenses*"),
 (2, 3.18, 4.76, "called *closing costs*"),
 (3, 0.25, 1.40, "like *lender fees,*"), (3, 1.40, 2.55, "*home inspection* fees,"),
 (3, 2.55, 3.65, "*title insurance,*"), (3, 3.65, 4.85, "*title registration,*"),
 (3, 4.85, 6.40, "*property tax* adjustments"), (3, 6.40, 7.60, "and sometimes"),
 (3, 7.60, 9.20, "an *appraisal fee* too"),
 (4, 0.10, 1.74, "So before you buy,"), (4, 1.74, 2.66, "for *closing costs*"),
 (4, 2.66, 3.79, "keep a *separate budget*"),
 (5, 0.03, 1.98, "Check with your *mortgage professional*"), (5, 1.98, 3.00, "or *lawyer*"),
 (5, 3.00, 5.22, "and confirm your *estimated* closing costs"),
 (6, 0.00, 1.52, "Got any questions"), (6, 1.52, 3.52, "about *closing costs?*"),
 (6, 3.52, 5.07, "Feel free to *reach out to me*"),
]
CAPS = [(T(s, a), T(s, b), txt) for s, a, b, txt in CAP]

CARDS = [  # photo-card B-roll windows (final time), clip id, handwritten label, tilt
 (T(0, 3.98), T(0, 5.95), "4009", "your future home", -3.0),
 (T(2, 0.05), T(2, 4.76), "18263", "additional expenses", 2.5),
 (T(4, 0.10), T(4, 3.79), "1717715134", "a separate budget", -2.5),
 (T(5, 0.03), T(5, 2.60), "4809", "your mortgage professional", 3.0),
 (T(5, 2.60), T(5, 5.22), "241", "or your lawyer", -3.0),
]
RECEIPT = [("Lender fees", 0.58), ("Home inspection", 1.54), ("Title insurance", 2.68),
           ("Title registration", 3.76), ("Property tax adj.", 5.02), ("Appraisal fee*", 7.76)]
CHAPTERS = [(0, "01", "The surprise"), (T(2, 0), "02", "What's included"), (T(4, 0.1), "03", "Plan ahead"),
            (T(6, 0), "04", "Questions")]

SFX = []
def sfx(t, name, vol): SFX.append({"t": round(max(0, t), 3), "f": name, "v": vol})
sfx(0.05, "1490", 0.3)
sfx(T(0, 1.25), "2354", 0.45)
for t0, t1, k, lab, tilt in CARDS:
    sfx(t0 - 0.05, "1492", 0.22); sfx(t0 + 0.22, "1133", 0.55)
sfx(T(1, 6.95), "1489", 0.5)
sfx(T(1, 9.70), "2903", 0.38)
sfx(T(2, 0.6), "1993", 0.35)
sfx(T(3, 0.25) - 0.05, "1492", 0.25)
for _, s in RECEIPT: sfx(T(3, s), "1125", 0.75)
sfx(T(3, 8.55), "1120", 0.6)
sfx(T(4, 2.75), "2995", 0.6)
sfx(T(6, 0.25), "2354", 0.45)
sfx(T(6, 5.12), "938", 0.35)
sfx(VOICE_END - 0.05, "1490", 0.35)

# ------------------------------------------------------------------ helpers
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def back(x, s=1.4):
    x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2

def paste(canvas, el, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01: return
    if abs(rot) > 0.01: el = el.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        el = el.resize((max(1, int(el.width * scale)), max(1, int(el.height * scale))), Image.LANCZOS)
    if alpha < 1:
        el = el.copy(); el.putalpha(el.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(el, (int(cx - el.width / 2), int(cy - el.height / 2)))

def with_shadow(im, blur=16, off=(0, 12), op=120):
    pad = blur * 2 + max(abs(off[0]), abs(off[1]))
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: int(v * op / 255))
    sh.paste((0, 0, 0, 255), (pad + off[0], pad + off[1]), a)
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(im, (pad, pad)); return out

def text_img(txt, f, fill, shadow=True, hl=TERRA):
    parts = []; on = False
    for chunk in txt.split("*"):
        if chunk: parts.append((chunk, hl if on else fill))
        on = not on
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = sum(d.textlength(p, font=f) for p, _ in parts); asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(w) + 8, asc + desc + 8), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); x = 4
    for p, col in parts: dr.text((x, 4), p, font=f, fill=col); x += d.textlength(p, font=f)
    return with_shadow(im, blur=10, off=(0, 4), op=150) if shadow else im

_cache = {}
def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]

def draw_check(d, x, y, s, col, w=6):
    d.line([(x, y + s * .5), (x + s * .38, y + s * .85), (x + s, y + s * .1)], fill=col, width=w, joint="curve")

def house_line(size, col, w=10):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = size
    d.line([(s*.12, s*.5), (s*.5, s*.15), (s*.88, s*.5)], fill=col, width=w, joint="curve")
    d.line([(s*.22, s*.42), (s*.22, s*.86), (s*.78, s*.86), (s*.78, s*.42)], fill=col, width=w, joint="curve")
    d.line([(s*.44, s*.86), (s*.44, s*.64), (s*.56, s*.64), (s*.56, s*.86)], fill=col, width=w, joint="curve")
    return im

# ------------------------------------------------------------------ sources + grade
class Clip:
    def __init__(self, path):
        cap = cv2.VideoCapture(path); self.f = []
        while True:
            ok, fr = cap.read()
            if not ok: break
            self.f.append(fr)
    def at(self, t): return self.f[min(len(self.f) - 1, max(0, int(round(t * FPS))))]

clips = {i: Clip(f"work/clean{i}.mp4") for i in range(1, 6)}
clips[6] = Clip("work/clean6_fixed.mp4")
brolls = {k: Clip(f"broll/{k}.mp4") for k in ["4009", "18263", "1717715134", "4809", "241"]}

# warm film grade: lifted blacks, gentle S-curve, warm balance, vignette
_x = np.arange(256) / 255.0
_curve = 0.035 + 0.94 * (_x + 0.12 * np.sin(2 * np.pi * _x) * -0.5 * 0 + 0.0)
_curve = 0.035 + 0.94 * (3 * _x**2 - 2 * _x**3) * 0.35 + 0.94 * _x * 0.65
LUT = np.stack([np.clip(_curve * m, 0, 1) for m in (0.95, 1.0, 1.05)], 1)  # B, G, R
LUT = (LUT * 255).astype(np.uint8)
yy, xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.28 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.7)) ** 2)).clip(0.6, 1)[..., None].astype(np.float32)
def grade(img, desat=0.0):
    out = np.empty_like(img)
    for c in range(3): out[..., c] = LUT[img[..., c], c]
    if desat > 0:
        g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)[..., None]
        out = (out * (1 - desat) + g * desat).astype(np.uint8)
    return (out.astype(np.float32) * VIG).astype(np.uint8)

def presenter(src, zoom, cy_frac=0.42):
    h, w = src.shape[:2]; cw, ch = w / zoom, h / zoom
    x0 = clamp(w / 2 - cw / 2, 0, w - cw); y0 = clamp(h * cy_frac - ch * cy_frac, 0, h - ch)
    M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
    fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    bl = cv2.GaussianBlur(fr, (0, 0), 1.2)
    return cv2.addWeighted(fr, 1.3, bl, -0.3, 0)

# ------------------------------------------------------------------ elements
def caption_el(txt):
    def mk():
        f = manrope("ExtraBold", 54)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        words = txt.split(" "); lines = []; cur = ""
        for w_ in words:
            test = (cur + " " + w_).strip()
            if d.textlength(test.replace("*", ""), font=f) > 860 and cur: lines.append(cur); cur = w_
            else: cur = test
        lines.append(cur)
        fixed = []; open_ = False
        for ln in lines:
            s = ("*" if open_ else "") + ln
            if ln.count("*") % 2: open_ = not open_
            if open_: s += "*"
            fixed.append(s)
        bars = []
        for ln in fixed:
            ti = text_img(ln, f, INK, shadow=False)
            bar = Image.new("RGBA", (ti.width + 44, ti.height + 10), (0, 0, 0, 0))
            ImageDraw.Draw(bar).rounded_rectangle((0, 0, bar.width - 1, bar.height - 1), 14, fill=CREAM + (240,))
            bar.alpha_composite(ti, (22, 2)); bars.append(bar)
        wm = max(b.width for b in bars); hs = sum(b.height for b in bars) + 6 * (len(bars) - 1)
        out = Image.new("RGBA", (wm, hs), (0, 0, 0, 0)); y = 0
        for b in bars: out.alpha_composite(b, ((wm - b.width) // 2, y)); y += b.height + 6
        return with_shadow(out, blur=12, off=(0, 6), op=90)
    return cached(("cap", txt), mk)

def chapter_el(num, name):
    def mk():
        f1 = mono("Medium", 26); f2 = manrope("Bold", 28)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        w = int(d.textlength(num, font=f1) + d.textlength(name, font=f2)) + 76
        im = Image.new("RGBA", (w, 56), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
        dr.rounded_rectangle((0, 0, w - 1, 55), 28, fill=FOREST + (215,))
        dr.text((24, 28), num, font=f1, fill=TERRA, anchor="lm")
        x = 24 + d.textlength(num, font=f1) + 14
        dr.line([(x, 18), (x, 38)], fill=CREAM + (120,), width=2)
        dr.text((x + 14, 28), name, font=f2, fill=CREAM, anchor="lm")
        return im
    return cached(("ch", num), mk)

def photo_card(key, lt, label):
    fr = brolls[key].at(lt)
    h, w = fr.shape[:2]; ch = int(w / 1.5); y0 = (h - ch) // 2
    z = 1 + 0.06 * min(lt / 4, 1); cw2, ch2 = int(w / z), int(ch / z)
    crop = fr[y0 + (ch - ch2) // 2: y0 + (ch - ch2) // 2 + ch2, (w - cw2) // 2:(w - cw2) // 2 + cw2]
    img = cv2.cvtColor(cv2.resize(crop, (720, 480), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    card = Image.new("RGBA", (760, 600), PAPER + (255,))
    card.paste(Image.fromarray(img), (20, 20))
    d = ImageDraw.Draw(card)
    d.text((380, 548), label, font=garamond("Italic", 46), fill=FOREST, anchor="mm")
    return with_shadow(card, blur=18, off=(0, 14), op=130)

def receipt_el(k):
    """k = time since receipt start (seg 3)."""
    Wr = 620; rows = len(RECEIPT); hdr = 150; rowh = 66; foot = 120
    Hr = hdr + rows * rowh + foot
    im = Image.new("RGBA", (Wr, Hr + 24), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, Wr, Hr), fill=PAPER)
    for x in range(0, Wr, 24): d.polygon([(x, Hr), (x + 12, Hr + 16), (x + 24, Hr)], fill=PAPER)  # torn edge
    d.text((Wr / 2, 52), "CLOSING COSTS", font=mono("Medium", 42), fill=INK, anchor="mm")
    d.text((Wr / 2, 98), "beyond the down payment", font=garamond("Italic", 34), fill=MUTED, anchor="mm")
    def dash(y):
        for x in range(36, Wr - 36, 18): d.line([(x, y), (x + 9, y)], fill=(170, 165, 150), width=3)
    dash(hdr - 14)
    src0 = SEGS[3][1]; fm = mono("Regular", 32)
    for i, (label, s) in enumerate(RECEIPT):
        kk = k - (s - src0)
        if kk < 0: break
        y = hdr + i * rowh + rowh / 2
        n = int(len(label) * clamp(kk / 0.22))
        d.text((40, y), label[:n], font=fm, fill=INK, anchor="lm")
        if kk > 0.22:
            tw = d.textlength(label, font=fm)
            for x in range(int(40 + tw + 14), Wr - 96, 14): d.ellipse((x, y + 6, x + 4, y + 10), fill=(185, 178, 160))
            draw_check(d, Wr - 82, y - 16, 34, TERRA, w=6)
    kk = k - (8.55 - src0)
    if kk >= 0:
        y = hdr + rows * rowh + 12; dash(y)
        a = int(255 * clamp(kk / 0.2))
        d.text((40, y + 52), "TOTAL", font=mono("Medium", 36), fill=INK + (a,), anchor="lm")
        d.text((Wr - 40, y + 52), "plan ahead", font=garamond("BoldItalic" if False else "Bold", 44), fill=TERRA + (a,), anchor="rm")
        d.text((40, y + 96), "*sometimes", font=mono("Regular", 22), fill=MUTED + (a,), anchor="lm")
    return with_shadow(im, blur=18, off=(0, 14), op=120)

def sticky(lines, rot=4):
    im = Image.new("RGBA", (330, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 329, 189), fill=(252, 228, 160))
    d.rectangle((115, 0, 215, 14), fill=(255, 255, 255, 120))  # tape
    d.text((165, 62), lines[0], font=manrope("Bold", 34), fill=INK, anchor="mm")
    d.text((150, 122), lines[1], font=garamond("Italic", 50), fill=TERRA, anchor="mm")
    if len(lines) > 2 and lines[2] == "check":
        tw = d.textlength(lines[1], font=garamond("Italic", 50)); draw_check(d, 150 + tw / 2 + 12, 104, 34, TERRA, w=6)
    return with_shadow(im.rotate(rot, resample=Image.BICUBIC, expand=True), blur=12, off=(0, 8), op=110)

def plate(txt, f, col):
    ti = text_img(txt, f, col, shadow=False)
    im = Image.new("RGBA", (ti.width + 90, ti.height + 30), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 22, fill=CREAM + (246,))
    im.alpha_composite(ti, (45, 8)); return with_shadow(im)

def lower_title():
    im = Image.new("RGBA", (880, 270), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 879, 269), 18, fill=CREAM + (248,))
    d.rectangle((0, 30, 12, 240), fill=TERRA)
    d.text((56, 108), "Closing costs", font=garamond("Bold", 116), fill=FOREST, anchor="lm")
    d.text((60, 210), "THE COSTS BEYOND YOUR DOWN PAYMENT", font=manrope("Bold", 30), fill=MUTED, anchor="lm")
    return with_shadow(im)

def cta_card():
    im = Image.new("RGBA", (860, 250), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 859, 249), 18, fill=CREAM + (248,))
    d.text((56, 100), "Questions?", font=garamond("Bold", 100), fill=FOREST, anchor="lm")
    d.text((60, 192), "SEND ME A MESSAGE", font=manrope("ExtraBold", 34), fill=TERRA, anchor="lm")
    tw = d.textlength("SEND ME A MESSAGE", font=manrope("ExtraBold", 34))
    x = 60 + tw + 20; d.line([(x, 192), (x + 60, 192)], fill=TERRA, width=6)
    d.polygon([(x + 60, 180), (x + 80, 192), (x + 60, 204)], fill=TERRA)
    return with_shadow(im)

# ------------------------------------------------------------------ render
ZOOM = {0: (1.0, 1.04), 2: (1.12, 1.15), 3: (1.0, 1.02), 4: (1.12, 1.15), 5: (1.03, 1.06), 6: (1.10, 1.14)}
def seg_at(t):
    for i in range(len(SEGS) - 1, -1, -1):
        if t >= offs[i]: return i
    return 0

def render(fi):
    t = fi / FPS
    if t >= VOICE_END: return render_outro(t - VOICE_END)
    si = seg_at(t); c, a, b = SEGS[si]; lt = t - offs[si]
    src = clips[c].at(a + lt)
    if si == 1:
        k = t - T(1, 6.95); z = 1.06 + (0.12 * back(k / 0.2) if k >= 0 else 0)
        k2 = t - T(1, 9.70)
        if k2 >= 0: z = 1.18 - 0.10 * ease_out(k2 / 0.6)
    else:
        z0, z1 = ZOOM[si]; z = z0 + (z1 - z0) * ease_in_out(lt / (b - a))
    desat = 0.0
    if si == 1:
        k = t - T(1, 6.95)
        if 0 <= k < 1.2: desat = 0.85 * (1 - ease_in_out((k - 0.7) / 0.5))
    canvas = Image.fromarray(cv2.cvtColor(grade(presenter(src, z), desat), cv2.COLOR_BGR2RGB)).convert("RGBA")

    # chapter tag + series title
    cur = [ch for ch in CHAPTERS if t >= ch[0]][-1]
    k = t - cur[0]
    paste(canvas, chapter_el(cur[1], cur[2]), 48 + chapter_el(cur[1], cur[2]).width / 2 - 30 * (1 - ease_out(k / 0.4)), 78, alpha=ease_out(k / 0.35))
    paste(canvas, cached("series", lambda: text_img("Closing Costs 101", garamond("Italic", 40), CREAM)), 860, 78)

    overlays(canvas, t, si)

    # photo cards
    for t0, t1, key, lab, tilt in CARDS:
        if t0 <= t < t1 + 0.25:
            k = t - t0; e = back(k / 0.45, 1.1); out = ease_in_out((t - t1) / 0.25) if t >= t1 else 0
            card = photo_card(key, k, lab)
            paste(canvas, card, 540 + 700 * out * (1 if tilt > 0 else -1), 1070 + 800 * (1 - e),
                  rot=tilt + 6 * (1 - ease_out(k / 0.5)), alpha=1 - out)
            if key == "1717715134" and t >= T(4, 2.75):
                kk = t - T(4, 2.75)
                paste(canvas, cached("st_budget", lambda: sticky(["keep it", "separate!"], rot=-6)), 800, 830,
                      scale=1.4 - 0.4 * ease_out(kk / 0.15), alpha=clamp(kk / 0.1))
    # receipt
    r0, r1 = T(3, 0.25), T(3, 9.20)
    if r0 <= t < r1:
        k = t - r0; out = ease_in_out((t - (r1 - 0.3)) / 0.3) if t >= r1 - 0.3 else 0
        rc = receipt_el(k)
        paste(canvas, rc, 540, 650 + rc.height / 2 + 900 * (1 - ease_out(k / 0.45)) + 1100 * out, rot=-1.5)

    # captions
    for c0, c1, txt in CAPS:
        if c0 <= t < c1:
            k = t - c0; el = caption_el(txt)
            paste(canvas, el, 540, 1600 + 14 * (1 - ease_out(k / 0.18)), alpha=ease_out(k / 0.12))
            break
    return canvas

def overlays(canvas, t, si):
    if si == 0:
        k = t - 0.1
        l1 = cached("h1", lambda: text_img("BEFORE YOU BUY A HOME", manrope("ExtraBold", 34), (252, 228, 160)))
        l2 = cached("h2", lambda: text_img("the cost nobody mentions", garamond("Italic", 92), CREAM))
        paste(canvas, l1, 540, 170 - 20 * (1 - ease_out(k / 0.4)), alpha=ease_out(k / 0.35))
        paste(canvas, l2, 540, 240 - 20 * (1 - ease_out((k - 0.12) / 0.4)), alpha=ease_out((k - 0.12) / 0.35))
        # underline drawing itself
        p = ease_in_out((k - 0.45) / 0.6)
        if p > 0:
            d = ImageDraw.Draw(canvas); x0 = 540 - 330; d.line([(x0, 300), (x0 + 660 * p, 296)], fill=TERRA, width=7)
        k = t - T(0, 1.25)
        if k >= 0 and t < T(0, 3.9):
            paste(canvas, cached("st_dp", lambda: sticky(["Down payment", "saved", "check"], rot=5)), 820, 760,
                  scale=back(k / 0.3), alpha=clamp(k / 0.1))
    if si == 1:
        k = t - T(1, 6.95)
        if 0 <= k and t < T(1, 9.6):
            wt = cached("wait", lambda: plate("Wait.", garamond("Italic", 190), TERRA))
            paste(canvas, wt, 540, 1130 + 30 * (1 - ease_out(k / 0.3)), alpha=ease_out(k / 0.2) * (1 - clamp((t - T(1, 9.35)) / 0.25)))
        k = t - T(1, 9.70)
        if k >= 0:
            lt_ = cached("lt", lower_title)
            paste(canvas, lt_, 540 - 900 * (1 - ease_out(k / 0.45)), 1150)
    if si == 6:
        k = t - T(6, 0.25)
        if k >= 0 and t < T(6, 5.07):
            paste(canvas, cached("cta", cta_card), 540, 1150 + 700 * (1 - ease_out(k / 0.45)))
        k = t - T(6, 5.07)
        if k >= 0:
            paste(canvas, cached("ty", lambda: plate("Thank you!", garamond("Italic", 130), FOREST)), 540, 1150,
                  scale=0.9 + 0.1 * ease_out(k / 0.3), alpha=ease_out(k / 0.2))

def render_outro(k):
    if "bg" not in _cache:
        src = clips[6].at(SEGS[6][2] - 0.05)
        _cache["bg"] = Image.fromarray(cv2.cvtColor(grade(presenter(src, 1.14)), cv2.COLOR_BGR2RGB)).convert("RGBA")
    canvas = _cache["bg"].copy()
    # cream panel rises from the bottom
    p = ease_in_out(k / 0.45); top = int(H * (1 - p))
    ImageDraw.Draw(canvas).rectangle((0, top, W, H), fill=CREAM)
    if p >= 1:
        q = k - 0.45
        paste(canvas, cached("oh", lambda: house_line(170, TERRA, 9)), 540, 640, alpha=ease_out(q / 0.3))
        paste(canvas, cached("o1", lambda: text_img("Plan for", garamond("Regular", 110), FOREST, shadow=False)), 540, 830 - 20 * (1 - ease_out(q / 0.4)), alpha=ease_out(q / 0.35))
        paste(canvas, cached("o2", lambda: text_img("closing costs.", garamond("Italic", 124), TERRA, shadow=False)), 540, 960 - 20 * (1 - ease_out((q - 0.12) / 0.4)), alpha=ease_out((q - 0.12) / 0.35))
        q2 = q - 0.45
        if q2 > 0:
            d = ImageDraw.Draw(canvas)
            d.line([(400, 1065), (680, 1065)], fill=FOREST, width=3)
            paste(canvas, cached("o3", lambda: text_img("SAVE  ·  SHARE  ·  FOLLOW", manrope("ExtraBold", 38), FOREST, shadow=False)), 540, 1140, alpha=ease_out(q2 / 0.3))
            paste(canvas, cached("o4", lambda: text_img("for more home-buying tips", garamond("Italic", 46), MUTED, shadow=False)), 540, 1210, alpha=ease_out((q2 - 0.1) / 0.3))
    fo = clamp((k - (OUTRO - 0.3)) / 0.3)
    if fo > 0: canvas.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fo))))
    return canvas

# ------------------------------------------------------------------ main
NF = int(round(TOTAL * FPS))
json.dump({"sfx": SFX, "segs": SEGS, "offs": offs, "voice_end": VOICE_END, "total": NF / FPS}, open("out/timeline.json", "w"), indent=1)
if PREVIEW:
    for tt in [float(x) for x in sys.argv[1].split(",")]:
        render(int(tt * FPS)).convert("RGB").save(f"out/v2_{tt:05.2f}.jpg", quality=88)
    print("total", TOTAL); sys.exit()
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "out/video.mp4"], stdin=subprocess.PIPE)
for fi in range(NF):
    p.stdin.write(np.asarray(render(fi).convert("RGB")).tobytes())
    if fi % 300 == 0: print("frame", fi, "/", NF, flush=True)
p.stdin.close(); p.wait(); print("done", NF / FPS)
