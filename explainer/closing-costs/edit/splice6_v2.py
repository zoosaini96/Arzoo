"""Clip 6 ending, v2: 'reach me out' -> 'reach out to me' with clearer joins.
'to' comes from clip 1 ('need to budget'), 'me' gets a natural phrase-final length,
pieces are loudness-matched and crossfaded. Usage: splice6_v2.py OUT_START ME_STRETCH GAP OUTWAV"""
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
def stretch(x, tempo):
    d = tempfile.mkdtemp(); sf.write(d+"/i.wav", x, SR)
    subprocess.run(["ffmpeg","-v","error","-y","-i",d+"/i.wav","-af",f"rubberband=tempo={tempo}:formant=preserved:pitch=1",d+"/o.wav"],check=True)
    return sf.read(d+"/o.wav")[0]
def fade(x, fi=0.0, fo=0.0):
    x = x.copy()
    if fi: k=int(fi*SR); x[:k] *= np.linspace(0,1,k)[:,None]
    if fo: k=int(fo*SR); x[-k:] *= np.linspace(1,0,k)[:,None]
    return x
def join(a, b, xf=0.010):
    k = int(xf*SR)
    if k == 0 or len(a) < k or len(b) < k: return np.concatenate([a, b])
    r = np.linspace(0,1,k)[:,None]
    return np.concatenate([a[:-k], a[-k:]*(1-r) + b[:k]*r, b[k:]])
def silence(s): return np.zeros((int(s*SR), 2))

def build(out_start=0.605, me_stretch=0.55, gap=0.05):
    head  = seg(c6, 0.000, 4.445)                      # "... please feel free to reach"
    out_  = fade(seg(c6, 4.0 + out_start, 4.865), 0.012, 0.015)   # "out" incl. t-release
    to    = fade(seg(c1, 8.555, 8.705), 0.006, 0.020)    # "to" from clip 1 ("need to budget")
    m     = seg(c6, 4.445, 4.500)                      # "m"
    ee    = stretch(seg(c6, 4.500, 4.572), me_stretch)  # "ee", lengthened, pitch kept
    me    = fade(join(m, ee, 0.006), 0.006, 0.060)
    tail  = seg(c6, 4.865, len(c6)/SR)                 # pause + "thank you"
    ref = rms(seg(c6, 4.17, 4.31))                     # loudness of "rea(ch)"
    to *= ref / rms(to) * 0.9; me *= ref / rms(me) * 0.95; out_ *= ref / rms(out_) * 0.95
    y = join(head, silence(0.03), 0.0); y = join(y, out_, 0.0)
    y = join(y, silence(gap), 0.0); y = join(y, to, 0.0); y = join(y, me, 0.008)
    y = join(y, silence(0.10), 0.0); y = join(y, tail, 0.0)
    return y
if __name__ == "__main__":
    a = [float(v) for v in sys.argv[1:4]] if len(sys.argv) > 3 else []
    y = build(*a); sf.write(sys.argv[4] if len(sys.argv) > 4 else "work/c6_fixed.wav", y, SR)
    print("len", len(y)/SR)
