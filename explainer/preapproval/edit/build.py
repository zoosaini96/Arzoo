"""Mortgage pre-approval explainer: joins the 4 cleaned clips in upload order and adds reframing,
punch-in zooms, B-roll cards, motion graphics, captions, chapter pills, progress bar and an end card."""
import subprocess, sys, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.environ.get("WS") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, DL, OUT = f"{S}/src", f"{S}/dl", f"{S}/out"
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FONT + f"Inter-{w}.otf", s)
NAVY = (11, 37, 69); AMBER = (255, 183, 3); GREEN = (46, 196, 140); WHITE = (255, 255, 255)
CORAL = (255, 107, 107); GREY = (160, 170, 185)
def GUR(s):
    """Noto Sans Gurmukhi (SIL OFL), bold weight, for Punjabi captions."""
    f = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansGurmukhi-VF.ttf"), s, layout_engine=ImageFont.Layout.RAQM)
    try: f.set_variation_by_axes([800, 100])
    except Exception: f.set_variation_by_name("Bold")
    return f
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers_src.py")).read())

# ---------------- timeline: (clip, src_in, src_out) in upload order ----------------
# every clip is used in full, start to end, so no speech is cut
SEGS = [(1, 0.0, 9.82), (2, 0.0, 14.40), (3, 0.0, 5.83), (4, 0.0, 8.25)]
GST = []; acc = 0.0
for s in SEGS: GST.append(acc); acc += s[2] - s[1]
SPEECH_END = acc; END_CARD = 3.0; TOTAL = SPEECH_END + END_CARD; N = int(round(TOTAL * FPS))
def g(c, t):
    """source time in clip c -> global time"""
    for (cc, a, b), st in zip(SEGS, GST):
        if cc == c and a - 1e-3 <= t <= b + 1e-3: return st + t - a
    best = min(((abs(t - a), st) if t < a else (abs(t - b), st + b - a) for (cc, a, b), st in zip(SEGS, GST) if cc == c))
    return best[1]
def clip_at(t):
    for (cc, a, b), st in zip(SEGS, GST):
        if st <= t < st + b - a: return cc
    return SEGS[-1][0]
CUTS = GST[1:]

CAPS = [
    (1, 0.45, 3.06, "Planning to buy your *dream home*?"),
    (1, 3.30, 4.30, "Before buying a home,"),
    (1, 4.30, 5.52, "the *most important step*"),
    (1, 5.52, 7.80, "that many *buyers ignore*..."),
    (1, 7.80, 9.82, "That's *mortgage pre-approval!*"),
    (2, 0.00, 1.56, "*Pre-approval* gives you"),
    (2, 1.56, 3.06, "a clear idea of your"),
    (2, 3.06, 4.24, "*income*, *debts*"),
    (2, 4.24, 5.06, "and *credit profile*"),
    (2, 5.06, 7.40, "for *mortgage qualification*."),
    (2, 8.20, 9.58, "*Second*, you get"),
    (2, 9.58, 10.80, "a *realistic budget*"),
    (2, 10.80, 14.40, "and can *research confidently*."),
    (3, 0.00, 1.38, "*Third*,"),
    (3, 1.38, 2.90, "*sellers* feel confident"),
    (3, 2.90, 4.60, "you're *financially prepared*"),
    (3, 4.60, 5.83, "to *buy their home*."),
    (4, 0.00, 1.30, "But *remember*,"),
    (4, 1.30, 2.60, "*pre-approval* is *NOT*"),
    (4, 2.60, 4.30, "your *final mortgage approval*."),
    (4, 4.30, 5.60, "*Final approval* depends on"),
    (4, 5.60, 6.60, "*lender policies*"),
    (4, 6.60, 8.25, "and *property eligibility*."),
]
CAPS = [(g(c, a), g(c, b), t) for c, a, b, t in CAPS]

# B-roll: (file, src_start, t0, t1, crop_center_x (0-1), label)
BROLL = [
    ("24945.mp4", 0.5, g(1, 3.10), g(1, 7.40), 0.50, None),
    ("46994.mp4", 9.0, g(2, 9.45), g(2, 10.80), 0.70, "Realistic budget"),
    ("4713.mp4", 2.0, g(2, 10.80), g(2, 13.60), 0.58, "Shop with confidence"),
    ("12946.mp4", 5.5, g(3, 1.40), g(3, 4.50), 0.62, "Sellers take you seriously"),
    ("6021.mp4", 0.3, g(4, 4.30), g(4, 5.55), 0.45, None),
]
CARD_W, CARD_H, CARD_CY = 940, 1175, 860
CHAPTERS = [(0, GST[1], "THE STEP BUYERS SKIP"), (GST[1], GST[3], "WHY GET PRE-APPROVED"), (GST[3], SPEECH_END, "KEEP IN MIND")]
# numbered reason badges (t0, t1, n, text)
REASONS = [(g(2, 0.0), g(2, 8.0), "1", "Know what you qualify for"),
           (g(2, 8.0), g(2, 14.4), "2", "Get a realistic budget"),
           (g(3, 0.0), g(3, 5.83), "3", "Sellers trust your offer")]

# reframing: crop centre x per clip (1080 space) - also crops away the far edges of the yard
CX = {1: 548, 2: 552, 3: 532, 4: 566}
BASEZ = 1.2
PUNCH = [(g(1, 7.70), g(1, 9.82), 1.55), (g(2, 3.06), g(2, 7.40), 1.38), (g(2, 8.20), g(2, 9.45), 1.5),
         (g(3, 0.0), g(3, 1.40), 1.5), (g(3, 4.5), g(3, 5.84), 1.35), (g(4, 0.0), g(4, 1.3), 1.5),
         (g(4, 1.3), g(4, 4.3), 1.3), (g(4, 5.55), SPEECH_END + 10, 1.25)]
def zoom_at(t):
    for a, b, z in PUNCH:
        if a <= t < b: return z
    for st, (c, a, b) in zip(GST, SEGS):
        if st <= t < st + b - a: return BASEZ + 0.06 * (t - st) / (b - a)
    return BASEZ

def badge_img(n, text):
    font = F("ExtraBold", 44); tw = int(text_w(font, text)); h = 96
    im = rrect((tw + 150, h), h // 2, (255, 255, 255, 245)); d = ImageDraw.Draw(im)
    d.ellipse([10, 10, h - 10, h - 10], fill=AMBER)
    d.text((h / 2, h / 2), n, font=F("Black", 48), fill=NAVY, anchor="mm")
    d.text((h + 20, h / 2), text, font=font, fill=NAVY, anchor="lm")
    return shadowed(im, blur=14, off=(0, 8), alpha=120)

def stamp_img():
    im = Image.new("RGBA", (940, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 930, 410], 48, fill=NAVY + (245,), outline=AMBER, width=10)
    check_icon(d, 140, 210, 84)
    d.text((250, 150), "MORTGAGE", font=F("Black", 82), fill=WHITE, anchor="lm")
    d.text((250, 270), "PRE-APPROVAL", font=F("Black", 82), fill=AMBER, anchor="lm")
    return shadowed(im, blur=24, off=(0, 14), alpha=130)

def title_img2():
    im = Image.new("RGBA", (980, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 979, 329], 44, fill=NAVY + (245,))
    house_icon(d, 110, 150, 62, AMBER)
    d.text((205, 108), "BUYING A HOME?", font=F("Black", 74), fill=WHITE, anchor="lm")
    d.rounded_rectangle([196, 172, 960, 268], 18, fill=AMBER)
    d.text((578, 222), "DON'T SKIP STEP #1", font=F("Black", 62), fill=NAVY, anchor="mm")
    return shadowed(im, blur=24, off=(0, 12), alpha=130)

def notequal_img(p):
    pw, ph = 940, 330
    im = rrect((pw, ph), 40, (255, 255, 255, 240)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 70, 400, 260], 30, fill=(232, 245, 239))
    d.text((220, 135), "Pre-", font=F("Black", 58), fill=GREEN, anchor="mm")
    d.text((220, 200), "approval", font=F("Black", 58), fill=GREEN, anchor="mm")
    d.rounded_rectangle([540, 70, 900, 260], 30, fill=(232, 238, 248))
    d.text((720, 135), "Final", font=F("Black", 58), fill=NAVY, anchor="mm")
    d.text((720, 200), "approval", font=F("Black", 58), fill=NAVY, anchor="mm")
    s = ease_out_back(p)
    if s > 0.05:
        ne = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); dd = ImageDraw.Draw(ne)
        dd.ellipse([0, 0, 139, 139], fill=CORAL); dd.text((70, 66), "≠", font=F("Black", 110), fill=WHITE, anchor="mm")
        ne = ne.resize((max(1, int(140 * s)), max(1, int(140 * s))), Image.BICUBIC)
        im.alpha_composite(ne, (int(470 - ne.width / 2), int(165 - ne.height / 2)))
    return shadowed(im, blur=22, off=(0, 12), alpha=110)

def endcard_img2():
    im = Image.new("RGBA", (W, 1000), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    house_icon(d, W/2, 170, 120, AMBER)
    d.text((W/2, 400), "Get pre-approved first!", font=F("Black", 82), fill=WHITE, anchor="mm")
    d.text((W/2, 500), "Know your budget. Shop with confidence.", font=F("SemiBold", 44), fill=(225, 232, 245), anchor="mm")
    d.text((W/2, 562), "Make stronger offers.", font=F("SemiBold", 44), fill=(225, 232, 245), anchor="mm")
    x = W/2 - 3*250/2 - 20
    for i, (lab, col) in enumerate((("LIKE", CORAL), ("SHARE", GREEN), ("FOLLOW", AMBER))):
        cx = x + i * 270 + 125
        d.rounded_rectangle([cx-125, 690, cx+125, 790], 50, fill=col)
        d.text((cx, 740), lab, font=F("Black", 46), fill=NAVY if col == AMBER else WHITE, anchor="mm")
    d.text((W/2, 880), "for more home-buying tips", font=F("Bold", 44), fill=AMBER, anchor="mm")
    return im

# ---------------- sources ----------------
# clip 1 word swap: she says "sab ton | ik | zaruri step"; the edit plays "ik | sab ton | zaruri step".
# boundaries (s) were picked at energy minima of the source audio.
SWAP1 = (4.30, 4.62, 4.845)   # [a,b) = "sab ton", [b,c) = "ik" (she runs "ton ik" together; split verified by ASR)
def fix_c1_audio():
    import wave
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{SRC}/c1.mov", "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", f"{OUT}/c1_audio_src.wav"], check=True)
    w = wave.open(f"{OUT}/c1_audio_src.wav"); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32)
    a, b, c = (int(round(v * sr)) for v in SWAP1)
    pieces = [x[:a], x[b:c], x[a:b], x[c:]]
    fl = int(0.004 * sr); ramp = np.linspace(0, 1, fl)[:, None]
    for k, pc in enumerate(pieces):       # 4 ms fade at each joint, length unchanged
        pc = pc.copy()
        if k > 0: pc[:fl] *= ramp
        if k < len(pieces) - 1: pc[-fl:] *= ramp[::-1]
        pieces[k] = pc
    y = np.clip(np.concatenate(pieces), -32768, 32767).astype(np.int16)
    assert len(y) == len(x)
    o = wave.open(f"{OUT}/c1_audio_fixed.wav", "wb"); o.setnchannels(2); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.tobytes()); o.close()

def build_aroll():
    fix_c1_audio()
    vf, af, n = [], [], 0
    for k, (c, a, b) in enumerate(SEGS):
        vf.append(f"[{c-1}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps=30[v{k}]")
        af.append(f"[{4+c-1}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.012,afade=t=out:st={b-a-0.012:.3f}:d=0.012[a{k}]")
    vf.append("".join(f"[v{k}]" for k in range(len(SEGS))) + f"concat=n={len(SEGS)}:v=1:a=0,eq=contrast=1.05:saturation=1.10,unsharp=5:5:0.5,tpad=stop_mode=clone:stop_duration={END_CARD+1}[v]")
    af.append("".join(f"[a{k}]" for k in range(len(SEGS))) + f"concat=n={len(SEGS)}:v=0:a=1,highpass=f=80,afftdn=nf=-25,"
              "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000[s]")
    ins = []
    for c in (1, 2, 3, 4): ins += ["-i", f"{OUT}/c{c}_clean.mp4"]
    for c in (1, 2, 3, 4): ins += ["-i", f"{OUT}/c1_audio_fixed.wav" if c == 1 else f"{SRC}/c{c}.mov"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(vf + af),
                    "-map", "[v]", "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", f"{OUT}/aroll.mp4",
                    "-map", "[s]", "-ac", "2", f"{OUT}/speech.wav"], check=True)

def broll_reader(spec):
    f, ss, t0, t1, cx, _ = spec
    x = int(cx * 1280 - 288); x = max(0, min(1280 - 576, x))
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", f"{t1 - t0 + 0.3:.3f}", "-i", f"{DL}/broll/{f}",
           "-vf", f"fps=30,scale=1280:720,crop=576:720:{x}:0,scale={CARD_W}:{CARD_H}:flags=lanczos,eq=contrast=1.04:saturation=1.08",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return reader(cmd, CARD_W, CARD_H)

def fade(t, a0, a1, i=0.35, o=0.25):
    p = (t - a0) / i; q = (a1 - t) / o
    return p, min(1, ease_out(p), ease_io(q))

def main():
    if not os.path.exists(f"{OUT}/aroll.mp4") or "--rebuild" in sys.argv: build_aroll()
    aroll = reader(["ffmpeg", "-v", "error", "-i", f"{OUT}/aroll.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], W, H)
    cap_cache = {i: caption_img(c[2]) for i, c in enumerate(CAPS)}
    chips = {i: chip_img(b[5], icon={1: "house", 2: "house", 3: "doc"}.get(i)) for i, b in enumerate(BROLL) if b[5]}
    chap = {c[2]: chapter_img(c[2]) for c in CHAPTERS}
    badges = [badge_img(n, tx) for _, _, n, tx in REASONS]
    TITLE, STAMP, END = title_img2(), stamp_img(), endcard_img2()
    mask = Image.new("L", (CARD_W, CARD_H), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W-1, CARD_H-1], 46, fill=255)
    card_border = Image.new("RGBA", (CARD_W + 16, CARD_H + 16), (0, 0, 0, 0))
    ImageDraw.Draw(card_border).rounded_rectangle([0, 0, CARD_W + 15, CARD_H + 15], 54, fill=(255, 255, 255, 255))
    card_border = shadowed(card_border, blur=26, off=(0, 16), alpha=150)
    CL1 = ("What lenders review", ["Income", "Debts", "Credit profile"], g(2, 2.9), g(2, 7.4), [g(2, 3.06), g(2, 3.62), g(2, 4.24)])
    CL2 = ("Final approval depends on", ["Lender policies", "Property eligibility"], g(4, 5.55), SPEECH_END, [g(4, 5.62), g(4, 6.86)])
    NEQ = (g(4, 1.3), g(4, 4.3)); TITLE_T = (0.05, g(1, 3.06)); STAMP_T = (g(1, 7.70), g(1, 9.82))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", f"{OUT}/video_noaudio.mp4"], stdin=subprocess.PIPE)
    br_iters, last_br, end_bg, last_frame = {}, {}, None, None
    for n in range(N):
        t = n / FPS
        frame = next(aroll, None)
        if frame is None: frame = last_frame
        last_frame = frame
        img = Image.fromarray(frame)
        # ---- reframe + punch zoom
        if t < SPEECH_END: z = zoom_at(t); c = clip_at(t)
        else: z = PUNCH[-1][2]; c = 4
        cx = CX[c]; cy = 960 - max(0, z - BASEZ) * 600
        w2, h2 = W / z, H / z
        x0 = min(max(0, cx - w2 / 2), W - w2); y0 = min(max(0, cy - h2 / 2), H - h2)
        img = img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w2, y0 + h2)).convert("RGBA")
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
                chained_in = any(abs(t0 - bb[3]) < 0.05 for bb in BROLL); chained_out = any(abs(t1 - bb[2]) < 0.05 for bb in BROLL)
                tin, tout = (t - t0) / 0.28, (t1 - t) / 0.2
                bga = (1 if chained_in else min(1, ease_out(tin))); bga = min(bga, 1 if chained_out else ease_io(tout))
                a = min(1, ease_out(tin), 1 if chained_out else ease_io(tout))
                s = 0.88 + 0.12 * ease_out_back(tin) if tin < 1 else 1.0 + 0.03 * (t - t0 - 0.28) / (t1 - t0)
                img = Image.blend(img, bg, bga) if bga < 1 else bg
                cc = card.convert("RGBA"); cc.putalpha(mask)
                paste(img, card_border, W/2, CARD_CY + 8, s, a)
                paste(img, cc, W/2, CARD_CY, s, a)
                if b[5]: paste(img, chips[i], W/2, CARD_CY + CARD_H/2 - 10, ease_out_back((t - t0 - 0.25) / 0.35), a)
        L = img
        # ---- title
        if TITLE_T[0] <= t < TITLE_T[1]:
            p, al = fade(t, *TITLE_T, 0.4, 0.25)
            paste(L, TITLE, W/2, 1240 + 60 * (1 - ease_out(p)), ease_out_back(p), al)
        # ---- stamp
        if STAMP_T[0] <= t < STAMP_T[1]:
            p, al = fade(t, *STAMP_T, 0.35, 0.2)
            paste(L, STAMP, W/2, 1220, ease_out_back(p) * 0.95, al, rot=-6 * (1 - ease_out(p)))
        # ---- reason badges
        for k, (a0, a1, _, _) in enumerate(REASONS):
            if a0 <= t < a1:
                p, al = fade(t, a0, a1, 0.4, 0.2)
                paste(L, badges[k], W/2 + 120 * (1 - ease_out(p)), 205, 1.0, al)
        # ---- checklists
        for title, items, a0, a1, tms in (CL1, CL2):
            if a0 <= t < a1:
                shown = sum(1 for x in tms if t >= x)
                pops = [ease_out_back((t - x) / 0.3) for x in tms]
                p, al = fade(t, a0, a1, 0.4, 0.25)
                paste(L, checklist_img(title, items, shown, pops), W/2, 1170 + 80 * (1 - ease_out(p)), 1.0, al)
        # ---- not-equal
        if NEQ[0] <= t < NEQ[1]:
            p, al = fade(t, *NEQ, 0.4, 0.25)
            paste(L, notequal_img((t - NEQ[0] - 0.9) / 0.4), W/2, 1180 + 80 * (1 - ease_out(p)), 1.0, al)
        # ---- captions + chapter pills
        if t < SPEECH_END:
            for i, (c0, c1_, _) in enumerate(CAPS):
                if c0 <= t < c1_:
                    p = (t - c0) / 0.15
                    paste(L, cap_cache[i], W/2, 1640, 0.88 + 0.12 * ease_out(p), min(1, ease_out(p * 1.5)))
            for c0, c1_, txt in CHAPTERS:
                if c0 <= t < c1_:
                    p = (t - c0) / 0.35; im = chap[txt]
                    paste(L, im, 40 + im.width/2 - 60 * (1 - ease_out(p)), 82, 1.0, ease_out(p))
        # ---- end card
        if t >= SPEECH_END - 0.25:
            if end_bg is None:
                eb = L.convert("RGB").resize((108, 192), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
                end_bg = eb.convert("RGBA"); end_bg.alpha_composite(Image.new("RGBA", (W, H), NAVY + (170,)))
            p = (t - SPEECH_END + 0.25) / 0.45
            L = Image.blend(L, end_bg, min(1, ease_io(p)))
            if t >= SPEECH_END:
                p = (t - SPEECH_END) / 0.5
                paste(L, END, W/2, 960 + 70 * (1 - ease_out(p)), 0.92 + 0.08 * ease_out_back(p), min(1, ease_out(p)))
        d = ImageDraw.Draw(L)
        d.rectangle([0, 0, W, 12], fill=(255, 255, 255, 70))
        d.rectangle([0, 0, int(W * min(1, t / SPEECH_END)), 12], fill=AMBER + (255,))
        enc.stdin.write(L.convert("RGB").tobytes())
        if n % 300 == 0: print(f"frame {n}/{N}", flush=True)
    enc.stdin.close(); enc.wait()
    json.dump({"TOTAL": TOTAL, "SPEECH_END": SPEECH_END, "GST": GST, "CUTS": CUTS, "BROLL": [[b[2], b[3]] for b in BROLL],
               "REASONS": [r[0] for r in REASONS], "CL1": CL1[4], "CL2": CL2[4], "STAMP": STAMP_T[0], "NEQ": NEQ[0] + 0.9}, open(f"{OUT}/timeline.json", "w"))

if __name__ == "__main__":
    main()
