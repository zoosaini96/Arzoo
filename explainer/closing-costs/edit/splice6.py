"""Rebuild clip 6 ending: 'reach me out' -> 'reach out to me'. Writes work/c6_fixed.wav (48k stereo)
and work/c6_map.json: list of (src_start, src_end) pieces in the new order (video follows the same map)."""
import numpy as np, subprocess, json, soundfile as sf, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
subprocess.run(["ffmpeg","-v","error","-y","-i","work/c6.mov","-vn","-ar","48000","-ac","2","out/c6_48k.wav"],check=True)
y,sr=sf.read("out/c6_48k.wav")
PIECES=[(0.000,4.445,"…free to reach"),(4.590,4.870,"out"),(4.055,4.168,"to"),(4.445,4.578,"me"),(None,0.07,"pause"),(4.870,len(y)/sr,"thank you")]
def cut(a,b,fi=0.008,fo=0.012):
    s=y[int(a*sr):int(b*sr)].copy(); n=len(s)
    if fi: k=int(fi*sr); s[:k]*=np.linspace(0,1,k)[:,None]
    if fo: k=int(fo*sr); s[-k:]*=np.linspace(1,0,k)[:,None]
    return s
out=[]; vmap=[]
for a,b,name in PIECES:
    if a is None: out.append(np.zeros((int(b*sr),2))); vmap.append([None,b]); continue
    fi=0 if a==0 else 0.008; fo=0 if name=="thank you" else 0.012
    if name=="me": fo=0.025
    out.append(cut(a,b,fi,fo)); vmap.append([a,b])
z=np.concatenate(out); sf.write("work/c6_fixed.wav",z,sr)
json.dump(vmap,open("work/c6_map.json","w")); print("new len",len(z)/sr,"old",len(y)/sr)
