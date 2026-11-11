"""Re-time clean6.mp4 to match the spliced audio (work/c6_fixed.wav)."""
import cv2, numpy as np, subprocess, os, soundfile as sf
os.chdir(os.path.dirname(os.path.abspath(__file__)))
cap=cv2.VideoCapture("work/clean6.mp4"); fr=[]
while True:
    ok,f=cap.read()
    if not ok: break
    fr.append(f)
newlen=sf.info("work/c6_fixed.wav").duration
A0,A1=4.445,4.870                        # source span whose words were re-ordered
N1=4.445+(4.870-4.590)+(4.168-4.055)+(4.578-4.445)+0.07   # its end in the new audio
def src(u):
    if u<A0: return u
    if u<N1: return A0+(u-A0)*(A1-A0)/(N1-A0)
    return A1+(u-N1)
p=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s","720x1280","-r","30","-i","-","-c:v","libx264","-crf","12","-preset","fast","-pix_fmt","yuv420p","work/clean6_fixed.mp4"],stdin=subprocess.PIPE)
n=int(newlen*30)
for i in range(n):
    p.stdin.write(fr[min(len(fr)-1,int(round(src(i/30)*30)))].tobytes())
p.stdin.close(); p.wait(); print("frames",n,"N1",round(N1,3))
