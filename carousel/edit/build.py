"""Render the 7-slide "5 mortgage myths" Instagram carousel (1080x1350 PNGs)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FONT + f"Inter-{w}.otf", s)

W, H = 1080, 1350
M = 96                                   # side margin
NAVY_TOP, NAVY_BOT = (16, 31, 58), (9, 19, 38)
GOLD = (212, 168, 79)
GOLD_SOFT = (212, 168, 79, 60)
WHITE = (246, 241, 230)
MUTED = (150, 162, 186)
BODY = (205, 212, 226)
TOTAL = 7

MYTHS = [
    ("You need 20% down.",
     "In Canada, you can put as little as 5% down on the first $500K.",
     "Then 10% on the portion from $500K up to $1.5M. With less than "
     "20% down, mortgage default insurance is required."),
    ("Your bank will give you the best rate.",
     "Your bank's first offer often isn't the best one out there.",
     "Rates and terms vary between lenders. Compare several, or work "
     "with a mortgage broker who can shop them for you."),
    ("Pre-approved means you're approved.",
     "A pre-approval is not a final approval.",
     "It's an estimate and a rate hold. Final approval comes after the "
     "lender verifies your income, documents and the property itself."),
    ("The lowest rate is always the best mortgage.",
     "The terms can matter as much as the rate.",
     "Check prepayment penalties, prepayment privileges and portability. "
     "A low rate with a big penalty can cost more if you break it early."),
    ("Just sign your renewal letter.",
     "Your renewal offer is negotiable.",
     "The first offer isn't always the best. Start comparing about four "
     "months before your term ends, then negotiate or switch lenders."),
]


def background():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOT)))
    # thin gold frame and corner accent
    d.rectangle([40, 40, W - 41, H - 41], outline=(212, 168, 79, 255), width=2)
    return img.convert("RGBA")


def wrap(font, text, maxw):
    text = text.replace("'", "\u2019")
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(trial) > maxw:
            lines.append(cur); cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


def block(d, text, font, y, fill, maxw=W - 2 * M, lh=1.22, x=M):
    """Draw wrapped text, return list of (x0, y_top, x1, line_h) and the new y."""
    boxes, size = [], font.size
    for ln in wrap(font, text, maxw):
        d.text((x, y), ln, font=font, fill=fill)
        boxes.append((x, y, x + font.getlength(ln), size))
        y += int(size * lh)
    return boxes, y


def chrome(d, n):
    d.text((M, 88), "MORTGAGE MYTHS", font=F("Bold", 26), fill=GOLD, anchor="lm")
    d.text((W - M, 88), f"{n} / {TOTAL}", font=F("SemiBold", 26), fill=MUTED, anchor="rm")
    if n < TOTAL:
        d.text((W - M, H - 92), "Swipe  →", font=F("SemiBold", 28), fill=GOLD, anchor="rm")


def pill(d, x, y, text, fg, bg, font):
    tw = font.getlength(text); padx, h = 24, 54
    d.rounded_rectangle([x, y, x + tw + 2 * padx, y + h], radius=h // 2, fill=bg)
    d.text((x + padx, y + h / 2), text, font=font, fill=fg, anchor="lm")
    return y + h


def centred(layer, top=150, bottom=H - 150):
    img = background()
    x0, y0, x1, y1 = layer.getbbox()
    off = (top + bottom) // 2 - (y0 + y1) // 2
    img.alpha_composite(layer, (0, off))
    return img


def cover():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    y = 330
    d.text((M, y), "5", font=F("Black", 300), fill=GOLD, anchor="ls")
    y += 70
    _, y = block(d, "mortgage myths", F("Black", 104), y, WHITE, lh=1.08)
    _, y = block(d, "that could", F("Black", 104), y, WHITE, lh=1.08)
    _, y = block(d, "cost you.", F("Black", 104), y, GOLD, lh=1.08)
    y += 50
    d.rectangle([M, y, M + 120, y + 6], fill=GOLD)
    y += 50
    block(d, "Read these before you buy, sign or renew.", F("Medium", 40), y, BODY, maxw=760)
    img = centred(layer); chrome(ImageDraw.Draw(img), 1)
    return img


def myth(i, text, truth, detail):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    y = 190
    y = pill(d, M, y, f"MYTH #{i + 1}", (12, 24, 46), GOLD, F("ExtraBold", 28)) + 44

    # the myth, struck through
    boxes, y = block(d, f"“{text}”", F("Bold", 66), y, MUTED, lh=1.2)
    for x0, yt, x1, s in boxes:
        my = yt + s * 0.58
        d.line([(x0 - 6, my), (x1 + 6, my)], fill=GOLD, width=5)
    # cross-out badge
    cx, cy, r = W - M - 40, 190 + 27, 27
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=4)
    k = 11
    d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=GOLD, width=5)
    d.line([(cx - k, cy + k), (cx + k, cy - k)], fill=GOLD, width=5)

    y += 54
    d.line([(M, y), (W - M, y)], fill=(110, 92, 58), width=2)
    y += 56

    # the truth
    d.ellipse([M, y, M + 46, y + 46], fill=GOLD)
    d.line([(M + 12, y + 24), (M + 20, y + 32), (M + 35, y + 15)], fill=(12, 24, 46), width=6, joint="curve")
    d.text((M + 66, y + 23), "THE TRUTH", font=F("ExtraBold", 30), fill=GOLD, anchor="lm")
    y += 86
    _, y = block(d, truth, F("ExtraBold", 60), y, WHITE, lh=1.18)
    y += 30
    block(d, detail, F("Medium", 38), y, BODY, lh=1.42)
    img = centred(layer); chrome(ImageDraw.Draw(img), i + 2)
    return img


def cta():
    img = background(); d = ImageDraw.Draw(img)
    chrome(d, TOTAL)
    y = 230
    _, y = block(d, "Buying, renewing or", F("Black", 84), y, WHITE, lh=1.1)
    _, y = block(d, "refinancing?", F("Black", 84), y, GOLD, lh=1.1)
    y += 34
    _, y = block(d, "Get a second opinion before you sign. "
                    "A few questions now can save you thousands later.",
                 F("Medium", 40), y, BODY, lh=1.4)
    y += 54
    for icon, label in [("↓", "Save this post for later"),
                        ("↗", "Share it with someone house hunting"),
                        ("✉", "Send a DM with your questions")]:
        d.rounded_rectangle([M, y, W - M, y + 92], radius=20, fill=(22, 38, 68),
                            outline=(150, 122, 66), width=2)
        d.ellipse([M + 22, y + 20, M + 74, y + 72], fill=GOLD)
        ifont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        d.text((M + 48, y + 46), icon, font=ifont, fill=(12, 24, 46), anchor="mm")
        d.text((M + 100, y + 46), label, font=F("SemiBold", 36), fill=WHITE, anchor="lm")
        y += 116
    # disclaimer
    y = H - 260
    d.line([(M, y), (W - M, y)], fill=(110, 92, 58), width=2)
    block(d, "General information only, not financial advice. Mortgage rules, "
             "rates and eligibility depend on your situation and can change. "
             "Talk to a licensed mortgage professional before making decisions.",
          F("Regular", 25), y + 28, MUTED, lh=1.45)
    return img


if __name__ == "__main__":
    slides = [cover()] + [myth(i, *m) for i, m in enumerate(MYTHS)] + [cta()]
    for n, s in enumerate(slides, 1):
        p = os.path.join(OUT, f"slide-{n}.png")
        s.convert("RGB").save(p, optimize=True)
        print(p, s.size)
