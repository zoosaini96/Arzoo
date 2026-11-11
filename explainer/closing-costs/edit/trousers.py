import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
_seg=None
def seg():
    global _seg
    if _seg is None:
        o=vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path="models/selfie_multiclass.tflite"),output_category_mask=False,output_confidence_masks=True)
        _seg=vision.ImageSegmenter.create_from_options(o)
    return _seg
def masks(img):
    r=seg().segment(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)))
    c=[m.numpy_view().squeeze().astype(np.float32) for m in r.confidence_masks]
    return c  # 0 bg,1 hair,2 body-skin,3 face-skin,4 clothes,5 others
def waist_row(img, clothes):
    b=img[...,0].astype(np.float32); rr=img[...,2].astype(np.float32); blu=b-rr
    H=img.shape[0]; ys=[]; vals=[]
    for y in range(int(H*0.3), int(H*0.8)):
        m=clothes[y]>0.5
        if m.sum()>60: ys.append(y); vals.append(np.median(blu[y][m]))
    ys=np.array(ys); vals=np.array(vals)
    trou = vals < -3
    for i in range(len(ys)-30):
        if trou[i:i+30].mean()>0.9: return int(ys[i])
    return None
BEIGE=np.array([160,196,226],np.float32)  # BGR, warm beige
def recolor(img, cm, wy, prev_alpha=None):
    H,W=img.shape[:2]
    clothes=cm[4]; shoes=cm[5]
    yy=np.arange(H)[:,None].astype(np.float32)
    below=np.clip((yy-(wy-4))/8.0,0,1)            # soft waistline
    a=clothes*below
    # refine with darkness: trousers are dark; background lighter
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY).astype(np.float32)
    dark=np.clip((95-g)/30.0,0,1)
    a=a*dark
    # grow alpha 3px outward onto dark fringe pixels
    grow=cv2.dilate(a,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
    bl=img[...,0].astype(np.float32)-img[...,2].astype(np.float32)
    fringe=np.clip((115-g)/35.0,0,1)*below*(bl<12)
    a=np.maximum(a, grow*fringe)
    a=a*(1-np.clip(shoes*1.5,0,1))
    a=cv2.GaussianBlur(a,(0,0),1.2)
    if prev_alpha is not None: a=0.6*a+0.4*prev_alpha
    # shading: luminance relative to trouser median
    sel=a>0.6
    if sel.sum()<500: return img,a
    gs=cv2.bilateralFilter(g,5,12,5)
    med=np.median(gs[sel])
    rel=np.clip(gs/med,0.35,2.2)
    shade=rel**0.85
    new=BEIGE[None,None,:]*shade[...,None]
    # keep a little original texture (detail) on top
    detail=(g-cv2.GaussianBlur(g,(0,0),2))[...,None]*1.6
    new=np.clip(new+detail,0,255)
    out=img.astype(np.float32)*(1-a[...,None])+new*a[...,None]
    return np.clip(out,0,255).astype(np.uint8), a
