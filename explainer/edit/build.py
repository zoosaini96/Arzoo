"""Explainer video compositor: A-roll + B-roll cards + motion graphics + captions."""
import subprocess, sys, math, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, DL, OUT = f"{S}/src", f"{S}/dl", f"{S}/out"
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FONT + f"Inter-{w}.otf", s)

# ---------------- timeline ----------------
C1 = (0.55, 10.2067); C2 = (0.35, 8.2017); C3 = (0.0, 23.25)
CUT2 = (5.9333, 6.2667)  # remove 'current' before 'position'
CUTLEN2 = CUT2[1] - CUT2[0]
CUT3 = (10.5667, 10.70)  # remove 'i' vowel: 'debits' -> 'debts'
CUTLEN = CUT3[1] - CUT3[0]
D1, D2, D3 = C1[1]-C1[0], C2[1]-C2[0]-CUTLEN2, C3[1]-C3[0]-CUTLEN
O1, O2, O3 = -C1[0], D1 - C2[0], D1 + D2 - C3[0]
SPEECH_END = D1 + D2 + D3
END_CARD = 2.9
TOTAL = SPEECH_END + END_CARD
N = int(round(TOTAL * FPS))
g1 = lambda t: t + O1; g2 = lambda t: t + O2 - (CUTLEN2 if t >= CUT2[1] - 0.001 else 0); g3 = lambda t: t + O3 - (CUTLEN if t >= CUT3[1] - 0.001 else 0)
B2, B3 = D1, D1 + D2  # clip boundaries

NAVY = (11, 37, 69); AMBER = (255, 183, 3); GREEN = (46, 196, 140); WHITE = (255, 255, 255)
CORAL = (255, 107, 107); GREY = (160, 170, 185)

# captions: (start, end, text) ; *word* = highlight
CAPS = [
    (g1(0.62), g1(2.0), "On *maternity leave*?"),
    (g1(2.0), g1(4.75), "Wondering if you can *buy a home*?"),
    (g1(5.25), g1(6.55), "Well, the answer is *YES!*"),
    (g1(6.55), g1(8.3), "You can *qualify for a mortgage*"),
    (g1(8.3), g1(10.2), "even on *maternity leave*."),
    (g2(0.43), g2(1.8), "Your *employer* only needs"),
    (g2(1.8), g2(3.0), "a *return-to-work letter*"),
    (g2(3.0), g2(5.3), "showing your *return date*,"),
    (g2(5.6), g2(8.2), "*position* & *salary*."),
    (g3(0.0), g3(2.9), "Many *lenders* can consider"),
    (g3(2.9), g3(4.4), "your *regular employment income*"),
    (g3(4.4), g3(5.55), "instead of reduced *maternity benefits*."),
    (g3(5.6), g3(7.9), "But *every lender* has a different policy"),
    (g3(7.95), g3(9.7), "and your *credit history*,"),
    (g3(9.7), g3(10.8), "*existing debts*"),
    (g3(10.8), g3(13.87), "and *financial situation* matter a lot."),
    (g3(13.9), g3(16.1), "So if you think you *can't buy*"),
    (g3(16.1), g3(18.3), "a house on *maternity leave*..."),
    (g3(18.4), g3(20.45), "*explore your options*"),
    (g3(20.45), g3(22.45), "before putting your *dream home* on hold."),
    (g3(22.45), SPEECH_END, "*Thank you!*"),
]

# B-roll: (file, src_start, t0, t1, crop_center_x (0-1 of 1280), label)
BROLL = [
    ("24945.mp4", 0.5, g1(2.15), g1(4.75), 0.55, None),
    ("17051.mp4", 1.9, g2(1.75), g2(3.05), 0.55, "Return-to-Work Letter"),
    ("49970.mp4", 0.2, g3(14.0), g3(16.6), 0.50, None),
    ("33357.mp4", 1.0, g3(18.4), g3(21.0), 0.50, "Explore your options"),
]
CARD_W, CARD_H, CARD_CY = 940, 1175, 860

CHAPTERS = [(0, B2, "MORTGAGE ON MATERNITY LEAVE"), (B2, B3, "WHAT YOU NEED"),
            (B3, g3(13.87), "HOW LENDERS DECIDE"), (g3(13.87), SPEECH_END, "MY ADVICE")]

# A-roll zoom keyframes (start, end, zoom). Default gentle push.
PUNCH = [(g1(5.2), g1(7.05), 1.20), (g1(7.05), g1(10.2), 1.08), (g3(5.6), g3(7.95), 1.12), (g2(0.0), g2(1.75), 1.10), (g2(3.05), g2(CUT2[0]), 1.0), (g2(CUT2[1]), g2(8.2), 1.08),
         (g3(2.9), g3(5.6), 1.0), (g3(7.95), g3(CUT3[0]), 1.0), (g3(CUT3[1]), g3(13.87), 1.08), (g3(16.6), g3(18.4), 1.14),
         (g3(21.0), SPEECH_END + 10, 1.12)]

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
    # gentle drift within clip
    for a, b in ((0, B2), (B2, B3), (B3, SPEECH_END + 10)):
        if a <= t < b: return 1.0 + 0.05 * (t - a) / (b - a)
    return 1.0

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

def house_icon(d, cx, cy, s, col):
    d.polygon([(cx, cy - s), (cx - s, cy - s*0.05), (cx + s, cy - s*0.05)], fill=col)
    d.rectangle([cx - s*0.7, cy - s*0.1, cx + s*0.7, cy + s*0.8], fill=col)
    d.rectangle([cx - s*0.18, cy + s*0.3, cx + s*0.18, cy + s*0.8], fill=NAVY)

def text_w(font, s): return font.getlength(s)

def caption_img(text):
    font = F("ExtraBold", 66)
    parts = []  # (word, highlight)
    hl = False
    for tok in text.replace("*", " * ").split():
        if tok == "*": hl = not hl; continue
        if parts and all(ch in ".,?!" for ch in tok):
            parts[-1] = (parts[-1][0] + tok, parts[-1][1]); continue
        parts.append((tok, hl))
    # wrap
    lines, cur, maxw = [], [], 960
    for w_, h_ in parts:
        trial = " ".join(x for x, _ in cur + [(w_, h_)])
        if cur and text_w(font, trial) > maxw: lines.append(cur); cur = [(w_, h_)]
        else: cur.append((w_, h_))
    lines.append(cur)
    lh = 84; sw = 7
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
    im = rrect((tw + 2*padx + iw, h), h // 2, bg + (240,))
    d = ImageDraw.Draw(im)
    if icon == "check": check_icon(d, padx + iw*0.35, h/2, int(h*0.3))
    if icon == "house": house_icon(d, padx + iw*0.35, h/2, h*0.27, AMBER)
    if icon == "bulb":
        r = h*0.22; cx = padx + iw*0.35
        d.ellipse([cx-r, h/2-r*1.25, cx+r, h/2+r*0.75], fill=AMBER)
        d.rectangle([cx-r*0.5, h/2+r*0.6, cx+r*0.5, h/2+r*1.2], fill=GREY)
    if icon == "doc":
        cx = padx + iw*0.35; s = h*0.25
        d.rectangle([cx-s*0.8, h/2-s, cx+s*0.8, h/2+s], fill=WHITE)
        for k in range(3): d.line([cx-s*0.5, h/2-s*0.5+k*s*0.45, cx+s*0.5, h/2-s*0.5+k*s*0.45], fill=NAVY, width=3)
    d.text((padx + iw, h/2), text, font=font, fill=fg, anchor="lm")
    return shadowed(im, blur=12, off=(0, 6), alpha=120)

def checklist_img(title, items, shown, pop_scales):
    """Panel with title + list items; shown = number of items visible."""
    pw, row = 900, 104
    ph = 130 + row * len(items) + 30
    im = rrect((pw, ph), 40, (255, 255, 255, 238))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw-1, 112], 40, fill=NAVY + (255,))
    d.rectangle([0, 70, pw-1, 112], fill=NAVY + (255,))
    d.text((pw/2, 58), title, font=F("ExtraBold", 50), fill=WHITE, anchor="mm")
    for i, it in enumerate(items):
        y = 130 + i * row + row/2
        if i < shown:
            s = pop_scales[i]
            ic = Image.new("RGBA", (90, 90), (0, 0, 0, 0)); check_icon(ImageDraw.Draw(ic), 45, 45, 36)
            ic = ic.resize((max(1, int(90*s)), max(1, int(90*s))), Image.BICUBIC)
            im.alpha_composite(ic, (int(90 - ic.width/2), int(y - ic.height/2)))
            d.text((160, y), it, font=F("Bold", 54), fill=NAVY, anchor="lm")
        else:
            d.ellipse([90-30, y-30, 90+30, y+30], outline=(200, 205, 215), width=5)
            d.text((160, y), it, font=F("Bold", 54), fill=(205, 210, 220), anchor="lm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def compare_img(p):
    """Bars: regular income vs maternity benefits, p = 0..1 grow."""
    pw, ph = 900, 430
    im = rrect((pw, ph), 40, (255, 255, 255, 238)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw-1, 112], 40, fill=NAVY + (255,)); d.rectangle([0, 70, pw-1, 112], fill=NAVY + (255,))
    d.text((pw/2, 58), "Many lenders can use", font=F("ExtraBold", 50), fill=WHITE, anchor="mm")
    full = pw - 120
    rows = [("Regular salary", 1.0, GREEN, True), ("Maternity benefits", 0.42, GREY, False)]
    for i, (lab, frac, col, ok) in enumerate(rows):
        y = 150 + i * 135
        d.text((60, y), lab, font=F("Bold", 44), fill=NAVY, anchor="lt")
        bw = int(full * frac * ease_out(p - i * 0.15))
        d.rounded_rectangle([60, y + 58, 60 + full, y + 100], 21, fill=(232, 236, 242))
        if bw > 42: d.rounded_rectangle([60, y + 58, 60 + bw, y + 100], 21, fill=col)
        if ok and p > 0.6:
            check_icon(d, pw - 70, y + 22, 26)
        if not ok and p > 0.6:
            d.text((pw - 60, y + 22), "reduced", font=F("SemiBold", 34), fill=CORAL, anchor="rm")
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def title_img():
    im = Image.new("RGBA", (980, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 979, 329], 44, fill=NAVY + (245,))
    house_icon(d, 110, 150, 62, AMBER)
    d.text((205, 108), "BUYING A HOME", font=F("Black", 74), fill=WHITE, anchor="lm")
    d.rounded_rectangle([196, 172, 960, 268], 18, fill=AMBER)
    d.text((578, 222), "ON MATERNITY LEAVE?", font=F("Black", 62), fill=NAVY, anchor="mm")
    return shadowed(im, blur=24, off=(0, 12), alpha=130)

def yes_img():
    im = Image.new("RGBA", (520, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([20, 20, 500, 500], fill=GREEN + (255,), outline=WHITE, width=14)
    d.text((260, 200), "YES!", font=F("Black", 150), fill=WHITE, anchor="mm")
    d.line([(165, 335), (232, 400), (360, 280)], fill=WHITE, width=30, joint="curve")
    return shadowed(im, blur=24, off=(0, 14), alpha=130)

def endcard_img():
    im = Image.new("RGBA", (W, 1000), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    house_icon(d, W/2, 170, 120, AMBER)
    d.text((W/2, 400), "Thanks for watching!", font=F("Black", 88), fill=WHITE, anchor="mm")
    d.text((W/2, 500), "Don't put your dream home on hold.", font=F("SemiBold", 48), fill=(225, 232, 245), anchor="mm")
    d.text((W/2, 565), "Explore your mortgage options today.", font=F("SemiBold", 48), fill=(225, 232, 245), anchor="mm")
    x = W/2 - 3*250/2 - 20
    for i, (lab, col) in enumerate((("LIKE", CORAL), ("SHARE", GREEN), ("FOLLOW", AMBER))):
        cx = x + i * 270 + 125
        d.rounded_rectangle([cx-125, 690, cx+125, 790], 50, fill=col)
        d.text((cx, 740), lab, font=F("Black", 46), fill=NAVY if col == AMBER else WHITE, anchor="mm")
    d.text((W/2, 880), "for more home-buying tips", font=F("Bold", 44), fill=AMBER, anchor="mm")
    return im

def chapter_img(text):
    font = F("ExtraBold", 34); tw = int(text_w(font, text))
    im = rrect((tw + 70, 66), 33, (0, 0, 0, 150)); d = ImageDraw.Draw(im)
    d.ellipse([22, 25, 38, 41], fill=AMBER)
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

def build_aroll():
    vf = ("[0:v]trim={0}:{1},setpts=PTS-STARTPTS[a];[1:v]trim={2}:{9},setpts=PTS-STARTPTS[b];[1:v]trim={10}:{3},setpts=PTS-STARTPTS[b2];"
          "[2:v]trim={4}:{5},setpts=PTS-STARTPTS[c];[2:v]trim={6}:{7},setpts=PTS-STARTPTS[d];[a][b][b2][c][d]concat=n=5:v=1:a=0,fps=30,"
          "scale=1080:1920:flags=lanczos,eq=contrast=1.06:saturation=1.12:brightness=0.01,"
          "unsharp=5:5:0.6,tpad=stop_mode=clone:stop_duration={8}[v]").format(*C1, *C2, C3[0], CUT3[0], CUT3[1], C3[1], END_CARD + 1, *CUT2)
    af = ("[0:a]atrim={0}:{1},asetpts=PTS-STARTPTS[a];[1:a]atrim={2}:{9},asetpts=PTS-STARTPTS,afade=t=out:st={11}:d=0.006[b];"
          "[1:a]atrim={10}:{3},asetpts=PTS-STARTPTS,afade=t=in:d=0.006[b2];"
          "[2:a]atrim={4}:{5},asetpts=PTS-STARTPTS,afade=t=out:st={8}:d=0.006[c];"
          "[2:a]atrim={6}:{7},asetpts=PTS-STARTPTS,afade=t=in:d=0.006[d];[a][b][b2][c][d]concat=n=5:v=0:a=1,"
          "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
          "loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000[s]").format(*C1, *C2, C3[0], CUT3[0], CUT3[1], C3[1], CUT3[0] - C3[0] - 0.006, CUT2[0], CUT2[1], CUT2[0] - C2[0] - 0.006)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{SRC}/c1.mov", "-i", f"{SRC}/c2.mov", "-i", f"{SRC}/c3.mov",
                    "-filter_complex", vf + ";" + af, "-map", "[v]", "-c:v", "libx264", "-crf", "10", "-preset", "fast",
                    "-pix_fmt", "yuv420p", f"{OUT}/aroll.mp4", "-map", "[s]", "-ac", "2", f"{OUT}/speech.wav"], check=True)

def broll_reader(spec):
    f, ss, t0, t1, cx, _ = spec
    dur = t1 - t0 + 0.2
    x = int(cx * 1280 - 288); x = max(0, min(1280 - 576, x))
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", f"{dur:.3f}", "-i", f"{DL}/broll/{f}",
           "-vf", f"fps=30,scale=1280:720,crop=576:720:{x}:0,scale={CARD_W}:{CARD_H}:flags=lanczos,eq=contrast=1.04:saturation=1.08",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return reader(cmd, CARD_W, CARD_H)

def main():
    if not os.path.exists(f"{OUT}/aroll.mp4") or "--rebuild" in sys.argv: build_aroll()
    aroll = reader(["ffmpeg", "-v", "error", "-i", f"{OUT}/aroll.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], W, H)

    cap_cache = {i: caption_img(c[2]) for i, c in enumerate(CAPS)}
    chips = {i: chip_img(b[5], icon={1: "doc", 3: "bulb"}.get(i)) for i, b in enumerate(BROLL) if b[5]}
    chips_extra = {"dream": chip_img("Don't put your dream home on hold", bg=(255, 183, 3), fg=NAVY, size=40, icon=None)}
    chap = {c[2]: chapter_img(c[2]) for c in CHAPTERS}
    TITLE, YES, END = title_img(), yes_img(), endcard_img()
    mask = Image.new("L", (CARD_W, CARD_H), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W-1, CARD_H-1], 46, fill=255)
    card_border = Image.new("RGBA", (CARD_W + 16, CARD_H + 16), (0, 0, 0, 0))
    ImageDraw.Draw(card_border).rounded_rectangle([0, 0, CARD_W + 15, CARD_H + 15], 54, fill=(255, 255, 255, 255))
    card_border = shadowed(card_border, blur=26, off=(0, 16), alpha=150)

    CL1 = ("Your letter should show", ["Return date", "Position", "Salary"], g2(3.05), g2(8.2), [g2(4.5), g2(6.3), g2(6.85)])
    CL2 = ("Lenders also check", ["Credit history", "Existing debts", "Financial situation"], g3(7.95), g3(13.87), [g3(8.6), g3(9.8), g3(10.9)])
    CMP = (g3(2.9), g3(5.55))
    YES_T = (g1(5.25), g1(7.05))
    TITLE_T = (g1(0.62), g1(4.75))

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", f"{OUT}/video_noaudio.mp4"],
                           stdin=subprocess.PIPE)
    br_iters = {}; last_br = {}; end_bg = None
    for n in range(N):
        t = n / FPS
        frame = next(aroll, None)
        if frame is None: frame = last_frame
        last_frame = frame
        img = Image.fromarray(frame)
        # ---- A-roll punch zoom (anchor upper body)
        if t < SPEECH_END:
            z = zoom_at(t)
            if z > 1.001:
                ax, ay = 540, 520
                w2, h2 = W / z, H / z
                x0 = ax - ax / z; y0 = ay - ay / z
                img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w2, y0 + h2))
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
                # blurred background from the card itself
                bg = card.crop((int((CARD_W - CARD_H*9/16)/2), 0, int((CARD_W + CARD_H*9/16)/2), CARD_H)).resize((54, 96), Image.BILINEAR)
                bg = bg.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR)
                bg = Image.fromarray((np.asarray(bg).astype(np.float32) * 0.55).astype(np.uint8)).convert("RGBA")
                tin, tout = (t - t0) / 0.28, (t1 - t) / 0.2
                a = min(1, ease_out(tin), ease_io(tout))
                s = 0.88 + 0.12 * ease_out_back(tin) if tin < 1 else 1.0 + 0.03 * (t - t0 - 0.28) / (t1 - t0)
                img = Image.blend(img, bg, a) if a < 1 else bg
                c = card.convert("RGBA"); c.putalpha(mask)
                paste(img, card_border, W/2, CARD_CY + 8, s, a)
                paste(img, c, W/2, CARD_CY, s, a)
                if b[5]:
                    ch = chips[i]
                    if b[0] == "33357.mp4" and t > g3(20.0): ch = chips_extra["dream"]
                    paste(img, ch, W/2, CARD_CY + CARD_H/2 - 10, ease_out_back((t - t0 - 0.25) / 0.35), a)

        L = img
        # ---- title
        a0, a1 = TITLE_T
        if a0 <= t < a1:
            p = (t - a0) / 0.4; q = (a1 - t) / 0.25
            ty = 1270 if t < BROLL[0][2] else CARD_CY + CARD_H/2 - 60
            if t >= BROLL[0][2]:
                p2 = (t - BROLL[0][2]) / 0.3
                ty = 1270 + (CARD_CY + CARD_H/2 - 60 - 1270) * ease_out(p2)
            paste(L, TITLE, W/2, ty + 60 * (1 - ease_out(p)), ease_out_back(p) * min(1, ease_io(q) * 0.3 + 0.7), min(1, ease_out(p), ease_io(q)))
        # ---- YES stamp
        a0, a1 = YES_T
        if a0 <= t < a1:
            p = (t - a0) / 0.35; q = (a1 - t) / 0.2
            paste(L, YES, W/2, 1150, ease_out_back(p) * 0.9, min(1, ease_out(p * 2), ease_io(q)), rot=-8 * (1 - ease_out(p)))
        # ---- checklists
        for title, items, a0, a1, tms in (CL1, CL2):
            if a0 <= t < a1:
                shown = sum(1 for x in tms if t >= x)
                pops = [ease_out_back((t - x) / 0.3) for x in tms]
                p = (t - a0) / 0.4; q = (a1 - t) / 0.25
                paste(L, checklist_img(title, items, shown, pops), W/2, 1210 + 80 * (1 - ease_out(p)), 1.0, min(1, ease_out(p), ease_io(q)))
        # ---- comparison
        a0, a1 = CMP
        if a0 <= t < a1:
            p = (t - a0) / 0.4; q = (a1 - t) / 0.25
            paste(L, compare_img((t - a0) / 1.2), W/2, 1180 + 80 * (1 - ease_out(p)), 1.0, min(1, ease_out(p), ease_io(q)))
        # ---- captions
        if t < SPEECH_END:
            for i, (c0, c1_, _) in enumerate(CAPS):
                if c0 <= t < c1_:
                    p = (t - c0) / 0.15
                    paste(L, cap_cache[i], W/2, 1640, 0.88 + 0.12 * ease_out(p), min(1, ease_out(p * 1.5)))
            # chapter pill
            for c0, c1_, txt in CHAPTERS:
                if c0 <= t < c1_:
                    p = (t - c0) / 0.35
                    im = chap[txt]
                    paste(L, im, 40 + im.width/2 - 60 * (1 - ease_out(p)), 82, 1.0, ease_out(p))
        # ---- end card
        if t >= SPEECH_END - 0.25:
            if end_bg is None:
                eb = Image.fromarray(frame).resize((108, 192), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
                ov = Image.new("RGBA", (W, H), NAVY + (170,))
                end_bg = eb.convert("RGBA"); end_bg.alpha_composite(ov)
            p = (t - SPEECH_END + 0.25) / 0.45
            L = Image.blend(L, end_bg, min(1, ease_io(p)))
            if t >= SPEECH_END:
                p = (t - SPEECH_END) / 0.5
                paste(L, END, W/2, 960 + 70 * (1 - ease_out(p)), 0.92 + 0.08 * ease_out_back(p), min(1, ease_out(p)))
        # ---- progress bar
        d = ImageDraw.Draw(L)
        d.rectangle([0, 0, W, 12], fill=(255, 255, 255, 70))
        d.rectangle([0, 0, int(W * min(1, t / SPEECH_END)), 12], fill=AMBER + (255,))
        enc.stdin.write(L.convert("RGB").tobytes())
        if n % 150 == 0: print(f"frame {n}/{N}", flush=True)
    enc.stdin.close(); enc.wait()
    json.dump({"TOTAL": TOTAL, "SPEECH_END": SPEECH_END, "O2": O2, "O3": O3, "CUT3": CUT3, "CUTLEN": CUTLEN, "CUT2": CUT2, "CUTLEN2": CUTLEN2, "B2": B2, "B3": B3,
               "BROLL": [b[2] for b in BROLL]}, open(f"{OUT}/timeline.json", "w"))

if __name__ == "__main__":
    if "--still" in sys.argv:
        pass
    main()
