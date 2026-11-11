"""Clip 6 ending, v3: natural-speed, pitch-matched 'reach out to me'.
Pieces: 'reach' (clip 6) + 'out' (clip 6, without its t-release) + 'to' (clip 1, 'need to budget')
+ 'me' (clip 6). 'out', 'to', 'me' are pitch-shifted onto a smooth falling contour and joined
with short crossfades (no gaps), so 'out to' shares one 't' as in natural speech.
Usage: splice6_v3.py [me_stretch,out_pitch,to_pitch,me_pitch,pause] [out.wav]"""
import numpy as np, soundfile as sf, subprocess, os, sys, tempfile
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
def load(src):
    p = f"out/{os.path.basename(src)}_48k.wav"
    if not os.path.exists(p):
        subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-vn","-ar",str(SR),"-ac","2",p],check=True)
    return sf.read(p)[0]
c6 = load("work/c6.mov"); c1 = load("work/c1.mov")
def seg(y, a, b): return y[int(a*SR):int(b*SR)].copy()
def rms(x): return np.sqrt(np.mean(x**2) + 1e-12)
def rb(x, tempo=1.0, pitch=1.0):
    if tempo == 1.0 and pitch == 1.0: return x
    d = tempfile.mkdtemp(); sf.write(d+"/i.wav", x, SR)
    subprocess.run(["ffmpeg","-v","error","-y","-i",d+"/i.wav","-af",
                    f"rubberband=tempo={tempo}:pitch={pitch}:formant=preserved:pitchq=quality:window=short",d+"/o.wav"],check=True)
    return sf.read(d+"/o.wav")[0][:int(len(x)/tempo)]
def fade(x, fi=0.0, fo=0.0):
    x = x.copy()
    if fi: k=int(fi*SR); x[:k] *= np.linspace(0,1,k)[:,None]
    if fo: k=int(fo*SR); x[-k:] *= np.linspace(1,0,k)[:,None]
    return x
def xjoin(a, b, xf):
    k = int(xf*SR)
    if k <= 0: return np.concatenate([a, b])
    r = np.sin(np.linspace(0, np.pi/2, k))[:,None]**2      # equal-power-ish crossfade
    return np.concatenate([a[:-k], a[-k:]*(1-r) + b[:k]*r, b[k:]])

def build(me_stretch=0.75, out_pitch=1.077, to_pitch=0.84, me_pitch=0.89, pause=0.05):
    pre   = seg(c6, 0.000, 4.445)                         # "... please feel free to reach"
    out_  = rb(seg(c6, 4.612, 4.790), pitch=out_pitch)    # "ou(t)" - t-release dropped, 'to' supplies it
    to    = rb(seg(c1, 8.560, 8.700), pitch=to_pitch)     # "to"
    m     = seg(c6, 4.445, 4.500)
    ee    = rb(seg(c6, 4.500, 4.572), tempo=me_stretch)
    me    = rb(xjoin(m, ee, 0.006), pitch=me_pitch)       # "me", phrase-final, falling
    ref = rms(seg(c6, 4.17, 4.31))
    out_ *= ref / rms(out_) * 0.95; to *= ref / rms(to) * 0.85; me *= ref / rms(me) * 0.9
    out_ = fade(out_, 0.010, 0.012); to = fade(to, 0.0, 0.010); me = fade(me, 0.0, 0.070)
    y = xjoin(pre, out_, 0.008)          # reach -> out (after the 'ch' closure)
    y = np.concatenate([y, np.zeros((int(0.025*SR),2))])  # stop closure before the 't' of 'to'
    y = xjoin(y, to, 0.004)
    y = xjoin(y, me, 0.012)
    y = np.concatenate([y, np.zeros((int(pause*SR),2)), seg(c6, 4.880, len(c6)/SR)])
    return y
if __name__ == "__main__":
    a = [float(v) for v in sys.argv[1].split(",")] if len(sys.argv) > 1 and sys.argv[1] else []
    y = build(*a); out = sys.argv[2] if len(sys.argv) > 2 else "work/c6_fixed.wav"
    sf.write(out, y, SR); print("len", round(len(y)/SR, 3), "(original clip 5.528)")
