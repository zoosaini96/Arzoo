import cv2, numpy as np
ROI_W, ROI_H = 260, 260
def detect_number(img):
    """Return mask (full-size uint8) of house-number digits in top-left ROI."""
    g = cv2.cvtColor(img[:ROI_H,:ROI_W], cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img[:ROI_H,:ROI_W], cv2.COLOR_BGR2HSV)
    bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT,(25,25)))
    m = ((bh > 35) & (hsv[...,1] < 60)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    comps = [i for i in range(1,n) if 12 <= st[i,3] <= 45 and st[i,2] <= 40 and st[i,4] >= 25]
    if not comps: return None
    # cluster by vertical center: keep largest group of comps whose centers lie within 12px
    best=[]
    for i in comps:
        grp=[j for j in comps if abs(cen[j][1]-cen[i][1])<12 and abs(st[j,3]-st[i,3])<14]
        if len(grp)>len(best): best=grp
    out = np.zeros(img.shape[:2], np.uint8)
    for j in best: out[:ROI_H,:ROI_W][lab==j]=255
    x0=min(st[j,0] for j in best); x1=max(st[j,0]+st[j,2] for j in best)
    y0=min(st[j,1] for j in best); y1=max(st[j,1]+st[j,3] for j in best)
    return out, (x0,y0,x1,y1)
def remove_number(img, det, pad=10):
    if det is None: return img
    mask,(x0,y0,x1,y1) = det
    out = img.copy().astype(np.float32)
    H,W = img.shape[:2]
    bx0=max(0,x0-pad); bx1=min(W,x1+pad); by0=max(0,y0-6); by1=min(H,y1+7)
    sx0=bx1+4; sx1=min(W,sx0+50)
    strip = img[by0:by1, sx0:sx1].astype(np.float32)
    med = np.median(strip, axis=1)                      # (h,3) per-row background
    w = bx1-bx0
    # take real texture from the strip (tiled) minus its row median -> grain
    reps = int(np.ceil(w/strip.shape[1]))
    grain = np.tile(strip - med[:,None,:], (1,reps,1))[:, :w]
    fill = med[:,None,:] + grain*0.8
    # feather: alpha 1 inside, ramps over 8px on left/right edges (left edge only if not at frame edge)
    a = np.ones(w, np.float32)
    ramp=8
    a[-ramp:] = np.linspace(1,0,ramp)
    if bx0>0: a[:ramp] = np.linspace(0,1,ramp)
    a = a[None,:,None]
    out[by0:by1,bx0:bx1] = fill*a + out[by0:by1,bx0:bx1]*(1-a)
    return np.clip(out,0,255).astype(np.uint8)
if __name__=="__main__":
    import sys
    tiles=[]
    for i in range(1,7):
        cap=cv2.VideoCapture(f"work/c{i}.mov"); n=int(cap.get(7))
        for k in [0, n//2, n-8]:
            cap.set(1,k); ok,f=cap.read()
            d=detect_number(f); r=remove_number(f,d)
            print(i,k, d[1] if d else None)
            tiles.append(np.hstack([f[:220,:260], r[:220,:260]]))
    rows=[np.hstack(tiles[j:j+3]) for j in range(0,len(tiles),3)]
    cv2.imwrite("frames/hn_test.png", np.vstack(rows))
