"""Track the sagging background cable per frame (DP ridge path) and inpaint it out."""
import cv2, numpy as np, sys, json
SEEDS = {
 1: [[(100,1),(160,5),(215,12),(245,18)], [(245,18),(300,60),(450,128),(570,240),(630,285),(690,322),(790,352),(870,430),(890,450)]],
 2: [(570,0),(675,82),(810,195),(915,270),(997,315)],
 3: [(630,15),(705,75),(810,150),(900,210),(975,255)],
 4: [(645,0),(810,105),(915,195),(990,240)],
 5: [(615,15),(690,75),(810,150),(915,225),(990,262)],
 6: [(615,0),(690,75),(825,150),(930,240),(1005,270)],
 7: [(630,0),(810,150),(930,225),(990,255)],
 8: [(645,0),(825,120),(945,195),(1020,240)],
}
KER = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
YMAX = 520

def blackhat(gray):
    bh = cv2.morphologyEx(gray[:YMAX], cv2.MORPH_BLACKHAT, KER).astype(np.float32)
    return cv2.GaussianBlur(bh, (3, 3), 0)

def dp_path(bh, xs, center, band, maxdy=2):
    """Max-sum path over columns xs, y within center[x]±band, |dy|<=maxdy per column."""
    n = len(xs); B = 2 * band + 1
    score = np.full((n, B), -1e9, np.float32); back = np.zeros((n, B), np.int16)
    def col(i):
        x = xs[i]; c = int(round(center[i])); ys = np.arange(c - band, c + band + 1)
        v = np.full(B, -1e9, np.float32); ok = (ys >= 0) & (ys < bh.shape[0])
        v[ok] = bh[ys[ok], x]; return v, c
    v, c0 = col(0); score[0] = v; cs = [c0]
    for i in range(1, n):
        v, c = col(i); cs.append(c); shift = c - cs[i - 1]
        prev = score[i - 1]
        best = np.full(B, -1e9, np.float32); arg = np.zeros(B, np.int16)
        for d in range(-maxdy, maxdy + 1):
            # current index k corresponds to prev index k + shift + d
            k = np.arange(B); pk = k + shift + d; ok = (pk >= 0) & (pk < B)
            cand = np.full(B, -1e9, np.float32); cand[ok] = prev[pk[ok]] - 0.5 * abs(d)
            m = cand > best; best[m] = cand[m]; arg[m] = pk[m]
        score[i] = best + v; back[i] = arg
    k = int(np.argmax(score[-1])); ys = np.zeros(n)
    for i in range(n - 1, -1, -1):
        ys[i] = cs[i] - band + k; k = back[i, k]
    return ys

def seed_curve(pts, xs):
    p = np.array(pts, float); return np.interp(xs, p[:, 0], p[:, 1])

def track(clip, src, out=None, overlay=None, stride=1, nmax=None):
    cap = cv2.VideoCapture(src); N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    seeds = SEEDS[clip] if isinstance(SEEDS[clip][0], list) else [SEEDS[clip]]
    st = []
    for pts in seeds:
        xs = np.arange(pts[0][0], pts[-1][0] + 1, 2).astype(float)
        st.append({"xs": xs, "c": seed_curve(pts, xs)})
    prev_gray = None; wr = None; band = 40
    for n in range(N if nmax is None else nmax):
        ok, f = cap.read()
        if not ok: break
        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            (dx, dy), _ = cv2.phaseCorrelate(np.float32(prev_gray[:280]), np.float32(gray[:280]))
            for s_ in st: s_["xs"] = s_["xs"] + dx; s_["c"] = s_["c"] + dy
            band = 10
        prev_gray = gray
        bh = blackhat(gray)
        mask = np.zeros(gray.shape, np.uint8)
        for s_ in st:
            xs = s_["xs"]; xi = np.round(xs).astype(int); c = s_["c"]
            ok_ = (c >= 2) & (xi >= 0) & (xi <= 1079)
            if ok_.sum() < 8:
                continue
            idx = np.where(ok_)[0]; a_, b_ = idx[0], idx[-1] + 1
            ys = c.copy(); ys[a_:b_] = dp_path(bh, xi[a_:b_], c[a_:b_], band)
            from scipy.ndimage import median_filter, uniform_filter1d
            sm = uniform_filter1d(median_filter(ys[a_:b_], 5, mode="nearest"), 5, mode="nearest")
            ys2 = c.copy(); ys2[a_:b_] = sm
            s_["c"] = ys2
            P = np.stack([xs, s_["c"]], 1).astype(np.int32)
            cv2.polylines(mask, [P], False, 255, 11)
        if overlay is not None:
            if n % stride == 0:
                g = f.copy(); g[mask > 0] = (0, 0, 255); cv2.imwrite(f"{overlay}_{n:03d}.jpg", g[:600])
            continue
        if mask.any():
            roi = f[:YMAX + 40]; m = mask[:YMAX + 40]
            f[:YMAX + 40] = cv2.inpaint(roi, m, 5, cv2.INPAINT_TELEA)
        if wr is None:
            wr = cv2.VideoWriter(out + ".avi", cv2.VideoWriter_fourcc(*"FFV1"), 30, (f.shape[1], f.shape[0]))
        wr.write(f)
    if wr: wr.release()

if __name__ == "__main__":
    c = int(sys.argv[1]); mode = sys.argv[2]
    if mode == "overlay":
        track(c, f"sdr/c{c}.mp4", overlay=f"ov2/c{c}", stride=int(sys.argv[3]))
    else:
        track(c, f"sdr/c{c}.mp4", out=f"clean/c{c}")
