"""Relight the presenter and beautify the background, frame by frame.
Person/face masks: MediaPipe selfie-multiclass segmenter. Usage: enhance.py <first_frame> <last_frame_excl> <out.mp4>"""
import sys, json, subprocess, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from timeline import S
W, H = 1080, 1920
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=f"{S}/dl/mc.tflite"), output_confidence_masks=True))
YY = np.linspace(0, 1, H, dtype=np.float32)[:, None]; XX = np.linspace(-1, 1, W, dtype=np.float32)[None]
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
VIG = (1 - 0.30 * (XX ** 2 * 0.7 + (YY * 2 - 1) ** 2 * 0.35))[..., None] * 0.95
GLOW = (0.32 * np.exp(-(((XX + 0.9) ** 2) / 0.5 + ((YY * 2 - 1 + 0.9) ** 2) / 0.35)))[..., None] * np.array([1.0, 0.75, 0.4], np.float32)
T = np.clip(YY / 0.30, 0, 1)[..., None]
SKYC = (np.array([0.20, 0.47, 0.88], np.float32) * (1 - T) + np.array([0.62, 0.80, 0.97], np.float32) * T)
WB = np.array([1.05, 1.0, 0.93], np.float32)
def sat(x, k):
    l = (x * LUMA).sum(2, keepdims=True); return np.clip(l + (x - l) * k, 0, 1)
def ss(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0, 1); return x * x * (3 - 2 * x)
prev = None
def process(rgb):
    global prev
    # segment two overlapping square crops (top/bottom) -> twice the mask detail of one squashed pass
    m = np.zeros((H, W), np.float32); skin = np.zeros((H, W), np.float32); facem = np.zeros((H, W), np.float32)
    wsum = np.zeros((H, 1), np.float32)
    for y0 in (0, H - W):
        r = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb[y0:y0 + W])))
        cm = [np.squeeze(c.numpy_view()) for c in r.confidence_masks]
        wy = np.ones((W, 1), np.float32)
        ov = W - (H - W)                        # overlap rows
        ramp = np.linspace(0, 1, ov, dtype=np.float32)[:, None]
        if y0 == 0: wy[W - ov:] = 1 - ramp
        else: wy[:ov] = ramp
        m[y0:y0 + W] += cv2.resize(1.0 - cm[0], (W, W)) * wy
        skin[y0:y0 + W] += cv2.resize(cm[3] + cm[2], (W, W)) * wy
        facem[y0:y0 + W] += cv2.resize(cm[3], (W, W)) * wy
        wsum[y0:y0 + W] += wy
    m /= wsum; skin /= wsum; facem /= wsum
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    m = cv2.ximgproc.guidedFilter(g, np.clip(m, 0, 1).astype(np.float32), 8, 2e-4)
    if prev is not None: m = 0.65 * m + 0.35 * prev            # temporal smoothing against flicker
    prev = m
    hard = ss(0.35, 0.65, m)
    f = np.clip(rgb.astype(np.float32) / 255 * WB, 0, 1)
    # subject: midtone lift, brighter + warmer face/hands, outfit blacks preserved
    sm = cv2.resize(cv2.GaussianBlur(cv2.resize(skin, (W // 4, H // 4)), (0, 0), 1.5), (W, H))[..., None]
    s = np.clip(f + 0.10 * np.sin(np.pi * f) * (1 - f), 0, 1)
    face = (1 - (1 - s) ** 1.45) * np.array([1.04, 1.0, 0.95], np.float32)
    s = s * (1 - 0.6 * sm) + face * 0.6 * sm
    s = np.clip((sat(s, 1.10) - 0.5) * 1.06 + 0.5, 0, 1)
    # background: richer colour, golden warmth, blue sky, soft depth blur, vignette, sun glow
    hsv = cv2.cvtColor((f * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    sv, vv = hsv[..., 1].astype(np.float32) / 255, hsv[..., 2].astype(np.float32) / 255
    halo = cv2.dilate(hard, np.ones((13, 13), np.uint8))
    skyraw = np.clip((vv - 0.62) / 0.15, 0, 1) * np.clip((0.30 - sv) / 0.18, 0, 1) * np.clip((0.33 - YY) / 0.10, 0, 1)
    edge = (skyraw * (1 - ss(0.75, 0.97, m)))[..., None]       # sky pixels caught in the soft hair edge
    skym = skyraw * (1 - halo)
    skym = cv2.resize(cv2.GaussianBlur(cv2.resize(skym, (W // 2, H // 2)), (0, 0), 2), (W, H))[..., None]
    b = np.clip((sat(f, 1.45) - 0.5) * 1.10 + 0.5, 0, 1) * np.array([1.07, 1.01, 0.88], np.float32)
    b = b * (1 - 0.92 * skym) + SKYC * (0.75 + 0.25 * b.mean(2, keepdims=True)) * 0.92 * skym
    q = (W // 4, H // 4)                                          # inpaint the person-shaped hole, then blur (no light silhouette)
    hq = (cv2.resize(halo, q, interpolation=cv2.INTER_AREA) > 0.02).astype(np.uint8)
    bq = cv2.resize((np.clip(b, 0, 1) * 255).astype(np.uint8), q, interpolation=cv2.INTER_AREA)
    bq = cv2.inpaint(bq, hq, 7, cv2.INPAINT_TELEA)
    b = cv2.resize(cv2.GaussianBlur(bq.astype(np.float32) / 255, (0, 0), 1.6), (W, H), interpolation=cv2.INTER_LINEAR)
    b = 1 - (1 - b * VIG) * (1 - GLOW)
    skyfix = SKYC * (0.75 + 0.25 * s.mean(2, keepdims=True))
    s = s * (1 - 0.92 * edge) + skyfix * 0.92 * edge
    comp = ss(0.50, 0.90, m)[..., None]
    out = s * comp + b * (1 - comp)
    ys, xs = np.nonzero(facem[::8, ::8] > 0.5); fm = facem[::8, ::8]
    fc = (float(xs.mean() / fm.shape[1] * W), float(ys.mean() / fm.shape[0] * H)) if len(xs) > 20 else None
    return (np.clip(out, 0, 1) * 255).astype(np.uint8), fc

if __name__ == "__main__":
    n0, n1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", f"{S}/out/aroll_raw.mp4", "-vf", f"select='between(n\\,{n0}\\,{n1-1})'",
                            "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                            "-c:v", "libx264", "-crf", "11", "-preset", "fast", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    faces = []
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: break
        o, fc = process(np.frombuffer(buf, np.uint8).reshape(H, W, 3)); faces.append(fc)
        enc.stdin.write(o.tobytes())
    enc.stdin.close(); enc.wait()
    json.dump(faces, open(out + ".faces.json", "w"))
    print("done", n0, n1, len(faces))
