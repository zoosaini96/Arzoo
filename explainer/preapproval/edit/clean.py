"""Background cleanup: removes clutter (pallets, plastic box, black polythene, dustbin, bench)
by inpainting a clean plate on a reference frame and tracking it onto every frame with a
background homography. Pixels that differ from the reference (the speaker moving in front)
are left untouched. Output: out/c{i}_clean.mp4 at 1080x1920 (before reframing)."""
import cv2, numpy as np, subprocess, sys, os
S = os.environ.get("WS") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = f"{S}/src", f"{S}/out"; os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1920
# object masks in 1080x1920 space of the reference frame (t=REF) : list of polygons
R = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
SPEC = {
 1: dict(ref=0.3, person=(330, 520, 760, 1920), objs=[
        R(0, 900, 285, 1235),          # wooden pallets + bag
        R(0, 1060, 70, 1280),          # black polythene bag
        R(705, 925, 800, 990),         # plastic box on grass
        R(915, 870, 1000, 940),        # bench by fence
        R(975, 840, 1080, 1440)]),     # dustbin edge
 2: dict(ref=0.3, person=(300, 300, 800, 1920), objs=[
        R(0, 730, 245, 1080), R(735, 750, 820, 810), R(970, 680, 1080, 770), R(995, 490, 1080, 650)]),
 3: dict(ref=0.3, person=(300, 340, 760, 1920), objs=[
        R(0, 755, 250, 1105), R(750, 778, 840, 832), R(995, 700, 1080, 780), R(1015, 500, 1080, 670)]),
 4: dict(ref=0.3, person=(320, 280, 780, 1920), objs=[
        R(0, 710, 285, 1055), R(0, 900, 50, 1110), R(782, 705, 880, 770), R(1035, 640, 1080, 710), R(1055, 400, 1080, 580)]),
}
# black covered object right behind the shoulder: polygons hugging the fence side of the dupatta
SHOULDER = {
 2: [(612, 455), (650, 455), (655, 520), (622, 520)],
 3: [(612, 510), (668, 505), (672, 575), (650, 590), (622, 585)],
 4: [(612, 455), (686, 450), (690, 535), (660, 520), (622, 470)],
}
HDR = {2, 3, 4}

def frames(i):
    vf = f"scale={W}:{H}:flags=lanczos"
    if i in HDR:  # iPhone HLG/BT.2020 -> SDR BT.709 (without this the clips look grey and washed out)
        # hable keeps skin tones natural; brightness/saturation matched to the SDR first clip
        vf = ("zscale=t=linear:npl=300,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,eq=contrast=1.04:saturation=0.95:gamma=1.08," + vf)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", f"{SRC}/c{i}.mov", "-vf", vf,
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=W*H*3*2)
    while True:
        b = p.stdout.read(W*H*3)
        if len(b) < W*H*3: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()
    p.wait()

def objmask(i):
    m = np.zeros((H, W), np.uint8)
    for poly in SPEC[i]["objs"] + ([SHOULDER[i]] if i in SHOULDER else []):
        cv2.fillPoly(m, [np.array(poly, np.int32)], 255)
    return m

def clean_plate(ref, m):
    out = ref.copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    for k in range(1, n):
        x, y, w, h, _ = st[k]; pad = max(60, w // 2, h // 2)
        x0, y0, x1, y1 = max(0, x-pad), max(0, y-pad), min(W, x+w+pad), min(H, y+h+pad)
        roi = out[y0:y1, x0:x1]; mm = (lab[y0:y1, x0:x1] == k).astype(np.uint8)
        mm = cv2.dilate(mm, np.ones((9, 9), np.uint8))
        dst = np.zeros_like(roi)
        # FSR wants a mask where 0 = missing
        cv2.xphoto.inpaint(roi, 1 - mm, dst, cv2.xphoto.INPAINT_FSR_FAST)
        out[y0:y1, x0:x1] = np.where(mm[..., None] > 0, dst, roi)
        if x == 0 and w * h > 40000:   # pallets: gravel below the foundation line, mirrored from just below
            yb = y + h; hb = min(h, H - yb - 1, 130)
            yy = np.arange(y - 10, yb)
            src_rows = yb + ((yb - 1 - yy) % hb)
            grav = ref[src_rows, :x + w + 20]
            line = lambda xx: y + 0.62 * h - (0.35 * h) * xx / (x + w)
            below = np.zeros((len(yy), x + w + 20), np.float32)
            for xx in range(x + w + 20): below[:, xx] = np.clip((yy - line(xx)) / 12, 0, 1)
            mk = cv2.GaussianBlur(cv2.dilate((lab == k).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (15, 15), 0)[y - 10:yb, :x + w + 20]
            a = (below * mk)[..., None]
            # wall/siding above the line: mirror the band just right of the mask horizontally
            per = 36; rows = (y - 12) - (np.abs(yy - (y - 12)) % per)
            wall = cv2.GaussianBlur(ref[rows, :x + w + 20], (5, 5), 0).astype(np.float32)
            aw = ((1 - below) * mk)[..., None]
            seg0 = out[y - 10:yb, :x + w + 20].astype(np.float32)
            out[y - 10:yb, :x + w + 20] = (seg0 * (1 - aw) + wall * aw).astype(np.uint8)
            seg = out[y - 10:yb, :x + w + 20].astype(np.float32)
            out[y - 10:yb, :x + w + 20] = (seg * (1 - a) + grav * a).astype(np.uint8)
    return out

def main(i, debug=False):
    sp = SPEC[i]; m = objmask(i)
    it = frames(i); allf = list(it)
    ref = allf[int(sp["ref"] * 30)]
    if debug:
        d = ref.copy(); d[m > 0] = (0.5*d[m > 0] + [0, 0, 127]).astype(np.uint8)
        x0, y0, x1, y1 = sp["person"]; cv2.rectangle(d, (x0, y0), (x1, y1), (0, 255, 0), 3)
        cv2.imwrite(f"{OUT}/dbg_mask{i}.jpg", d); cv2.imwrite(f"{OUT}/dbg_plate{i}.jpg", clean_plate(ref, m)); return
    plate = clean_plate(ref, m)
    md = cv2.dilate(m, np.ones((15, 15), np.uint8))
    feat = np.full((H, W), 255, np.uint8); x0, y0, x1, y1 = sp["person"]; feat[y0:y1, x0:x1] = 0; feat[md > 0] = 0
    orb = cv2.ORB_create(4000); g0 = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    k0, d0 = orb.detectAndCompute(g0, feat); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    soft = cv2.GaussianBlur(md.astype(np.float32) / 255, (31, 31), 0)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "30",
                            "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", f"{OUT}/c{i}_clean.mp4"], stdin=subprocess.PIPE)
    Hp = np.eye(3)
    for n, fr in enumerate(allf):
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        k1, d1 = orb.detectAndCompute(g, None)
        if d1 is not None and len(k1) > 20:
            ms = sorted(bf.match(d0, d1), key=lambda x: x.distance)[:800]
            if len(ms) > 30:
                A = np.float32([k0[x.queryIdx].pt for x in ms]); B = np.float32([k1[x.trainIdx].pt for x in ms])
                Hn, inl = cv2.findHomography(A, B, cv2.RANSAC, 3.0)
                if Hn is not None and inl.sum() > 25: Hp = 0.5 * Hp + 0.5 * Hn if n else Hn  # light temporal smoothing
        wp = cv2.warpPerspective(plate, Hp, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        wr = cv2.warpPerspective(ref, Hp, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        ws = cv2.warpPerspective(soft, Hp, (W, H))
        # match exposure of the plate to the current frame locally
        diff = cv2.GaussianBlur(cv2.absdiff(fr, wr).max(axis=2).astype(np.float32), (15, 15), 0)
        occ = np.clip((diff - 28) / 20, 0, 1)            # 1 = something new in front (the speaker)
        occ = cv2.dilate(occ, np.ones((11, 11), np.uint8)); occ = cv2.GaussianBlur(occ, (21, 21), 0)
        gain = cv2.GaussianBlur(fr.astype(np.float32), (61, 61), 0) / (cv2.GaussianBlur(wr.astype(np.float32), (61, 61), 0) + 1)
        gain = np.clip(gain, 0.8, 1.25)
        a = (ws * (1 - occ))[..., None]
        out = fr * (1 - a) + np.clip(wp * gain, 0, 255) * a
        enc.stdin.write(out.astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait(); print("clean", i, len(allf), flush=True)

if __name__ == "__main__":
    dbg = "--debug" in sys.argv
    for i in [int(x) for x in sys.argv[1:] if x.isdigit()] or [1, 2, 3, 4]: main(i, dbg)
