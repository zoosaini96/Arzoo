def ease_out_back(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_io(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)

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
    font = GUR(70) if any("\u0a00" <= ch <= "\u0a7f" for ch in text) else F("ExtraBold", 66)
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

