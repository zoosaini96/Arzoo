"""Minimal, natural edit: one colour grade on the original footage, gentle push-ins,
full-screen B-roll only where it matches the words, clean modern captions."""
import subprocess, json, re
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from timeline import S, FPS, SEGS, STARTS, SPEECH_END, g, seg_bounds
from build import build_words, phrases, reader
OUT, DL = f"{S}/out", f"{S}/dl"
W, H = 1080, 1920
TAIL = 0.8                                   # hold after "Thank you" then fade
TOTAL = SPEECH_END + TAIL
N = int(round(TOTAL * FPS))
GRADE = ("curves=master='0/0 0.12/0.17 0.45/0.53 0.82/0.85 1/0.96':blue='0/0 0.5/0.48 1/1',"
         "colorbalance=rs=0.03:bs=-0.02:rm=0.03:gm=0.005:bm=-0.03,vibrance=intensity=0.38,"
         "eq=contrast=1.09:saturation=1.10,unsharp=5:5:0.4")
BGRADE = "eq=contrast=1.04:saturation=1.06,vibrance=intensity=0.15"

# B-roll strictly on the matching words: (file, src_start, t0, t1, crop_center_x 0-1)
BROLL = [
    ("6021.mp4",  1.0, g(2, 4.05), g(3, 0.35), 0.50),   # "before starting a house hunt"
    ("23476.mp4", 2.0, g(4, 2.60), g(4, 4.25), 0.35),   # "like financing a car"
    ("23420.mp4", 11.5, g(4, 4.25), g(4, 5.85), 0.62),   # "furniture before closing"
    ("46977.mp4", 0.5, g(5, 4.60), g(5, 6.85), 0.55),   # "always review your terms, conditions"
    ("5660.mp4",  0.8, g(6, 0.85), g(6, 3.30), 0.27),   # "before switching your job during mortgage process"
    ("14977.mp4", 1.0, g(6, 3.45), g(6, 5.15), 0.50),   # "speak with your mortgage professional"
    ("33357.mp4", 0.8, g(7, 2.15), g(8, 0.75), 0.50),   # "before buying a home" (covers the clip join)
]
XF = 0.12  # quick dissolve

FONT = "/usr/share/fonts/opentype/inter/"
CAPF = ImageFont.truetype(FONT + "Inter-ExtraBold.otf", 68)
HIL = (255, 214, 64)
CAP_Y = 1330

def clamp(x): return min(max(x, 0.0), 1.0)
def caption_img(ph, active):
    toks = [w[2] for w in ph]; gap = CAPF.getlength(" ")
    widths = [CAPF.getlength(t) for t in toks]; total = sum(widths) + gap * (len(toks) - 1)
    im = Image.new("RGBA", (W, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = (W - total) / 2
    for i, (t, wd) in enumerate(zip(toks, widths)):
        d.text((x, 85), t, font=CAPF, fill=HIL if i == active else (255, 255, 255), anchor="lm")
        x += wd + gap
    a = im.split()[3]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); blk = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sh.paste(blk, (0, 3), a.point(lambda v: v * 200 // 255)); sh = sh.filter(ImageFilter.GaussianBlur(7))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh); out.alpha_composite(sh); out.alpha_composite(im)
    return out

def broll_reader(spec):
    f, ss, t0, t1, cx = spec; dur = t1 - t0 + 0.4
    cw = 405; x = max(0, min(1280 - cw, int(cx * 1280 - cw / 2)))
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", f"{dur:.3f}", "-i", f"{DL}/broll/{f}", "-vf",
           f"fps=30,scale=1280:720,crop={cw}:720:{x}:0,scale={W}:{H}:flags=lanczos,{BGRADE},unsharp=7:7:0.7",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return reader(cmd, W, H)

def push(fr, t):
    """gentle push-in inside each shot; alternate on the tightened pauses so jump cuts read as cuts"""
    for i, (s0, s1, _) in enumerate(seg_bounds()):
        if t < s1 or i == len(SEGS) - 1: break
    base = 1.08 if i in (5,) else 1.0
    z = base + 0.045 * clamp((t - s0) / max(0.5, s1 - s0))
    if z < 1.002: return fr
    w2, h2 = W / z, H / z; x0 = (W - w2) / 2; y0 = (H - h2) * 0.3
    M = np.array([[z, 0, -x0 * z], [0, z, -y0 * z]], np.float32)
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_CUBIC)

def main():
    aroll = reader(["ffmpeg", "-v", "error", "-i", f"{OUT}/aroll_raw.mp4", "-vf", GRADE, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], W, H)
    PH = phrases(build_words()); cache = {}
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", f"{OUT}/v2_noaudio.mp4"], stdin=subprocess.PIPE)
    its, lastb, last = {}, {}, None
    for n in range(N):
        t = n / FPS
        fr = next(aroll, None); fr = last if fr is None else fr; last = fr
        img = push(fr, min(t, SPEECH_END - 1e-3)).astype(np.float32)
        for i, b in enumerate(BROLL):
            if b[2] - XF <= t < b[3] + XF:
                if i not in its: its[i] = broll_reader(b)
                bf = next(its[i], None); bf = lastb[i] if bf is None else bf; lastb[i] = bf
                a = clamp(min((t - b[2] + XF) / (2 * XF), (b[3] + XF - t) / (2 * XF)))
                img = img * (1 - a) + bf.astype(np.float32) * a
        L = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        if t < SPEECH_END:
            for pi, ph in enumerate(PH):
                st = ph[0][0] - 0.04
                en = min(PH[pi + 1][0][0] - 0.04 if pi + 1 < len(PH) else ph[-1][1] + 0.5, ph[-1][1] + 0.5)
                if st <= t < en:
                    act = max([i for i, w in enumerate(ph) if t >= w[0] - 0.03] or [0])
                    key = (pi, act)
                    if key not in cache: cache[key] = caption_img(ph, act)
                    im = cache[key]; p = clamp((t - st) / 0.12)
                    if p < 1: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * p)))
                    L.alpha_composite(im, (0, int(CAP_Y - 85 + 12 * (1 - p))))
                    break
        f = clamp(t / 0.3) * clamp((TOTAL - t) / 0.6)           # fade in from / out to black
        out = np.asarray(L.convert("RGB")).astype(np.float32) * f if f < 1 else np.asarray(L.convert("RGB"))
        enc.stdin.write(np.asarray(out, np.uint8).tobytes())
        if n % 300 == 0: print(f"frame {n}/{N}", flush=True)
    enc.stdin.close(); enc.wait()
    json.dump({"TOTAL": TOTAL, "SPEECH_END": SPEECH_END, "BROLL": [b[2] for b in BROLL]}, open(f"{OUT}/events2.json", "w"))

if __name__ == "__main__":
    main()
