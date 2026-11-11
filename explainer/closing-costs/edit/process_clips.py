import os,sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import cv2, numpy as np, subprocess
from housenum import detect_number, remove_number
from trousers import masks, waist_row, recolor
i=int(sys.argv[1])
cap=cv2.VideoCapture(f"work/c{i}.mov"); fr=[]
while True:
    ok,f=cap.read()
    if not ok: break
    fr.append(f)
cms=[masks(f) for f in fr]
w=np.array([waist_row(f,c[4]) or np.nan for f,c in zip(fr,cms)],float)
w=np.where(np.isnan(w),np.nanmedian(w),w)
ws=np.array([np.median(w[max(0,k-7):k+8]) for k in range(len(w))])
p=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s","720x1280","-r","30","-i","-","-c:v","libx264","-crf","12","-preset","fast","-pix_fmt","yuv420p",f"work/clean{i}.mp4"],stdin=subprocess.PIPE)
dets=[detect_number(f) for f in fr]
bb=np.array([d[1] if d else (np.nan,)*4 for d in dets],float)
# outlier rejection vs. rolling median, then fill + smooth
med=np.array([np.nanmedian(bb[max(0,k-6):k+7],axis=0) for k in range(len(bb))])
bad=np.any(np.abs(bb-med)>14,axis=1)|np.isnan(bb).any(1)
bb[bad]=np.nan
for j in range(4):
    v=bb[:,j]; idx=np.arange(len(v)); ok=~np.isnan(v)
    bb[:,j]=np.interp(idx,idx[ok],v[ok])
sm=np.array([np.median(bb[max(0,k-2):k+3],axis=0) for k in range(len(bb))])
print('bad frames',int(bad.sum()))
prev=None
for f,cm,wy,b in zip(fr,cms,ws,sm):
    x0,y0,x1,y1=[int(round(v)) for v in b]
    if x0<15: x0=0
    g=remove_number(f,(None,(x0,y0-2,x1+2,y1+2)))
    out,prev=recolor(g,cm,int(wy),prev)
    p.stdin.write(out.tobytes())
p.stdin.close(); p.wait(); print(i,len(fr),'done')
