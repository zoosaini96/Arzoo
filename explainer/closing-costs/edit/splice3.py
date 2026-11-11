"""Clip 3: 'like lender fees' -> 'like lawyer fees'. 'lawyer' is taken from clip 5 ('or lawyer'),
pitch-matched to the original word, time-fitted into the same slot (so clip length is unchanged),
loudness-matched and crossfaded. Usage: splice3.py [law_start,law_end,pitch] [out.wav]"""
import numpy as np, soundfile as sf, subprocess, os, sys, tempfile
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
def load(src):
    p = f"out/{os.path.basename(src)}_48k.wav"
    if not os.path.exists(p):
        subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-vn","-ar",str(SR),"-ac","2",p],check=True)
    return sf.read(p)[0]
c3 = load("work/c3.mov"); c5 = load("work/c5.mov")
def seg(y, a, b): return y[int(a*SR):int(b*SR)].copy()
def rms(x): return np.sqrt(np.mean(x**2) + 1e-12)
def rb(x, tempo=1.0, pitch=1.0):
    d = tempfile.mkdtemp(); sf.write(d+"/i.wav", x, SR)
    subprocess.run(["ffmpeg","-v","error","-y","-i",d+"/i.wav","-af",
                    f"rubberband=tempo={tempo}:pitch={pitch}:formant=preserved:pitchq=quality:window=short",d+"/o.wav"],check=True)
    return sf.read(d+"/o.wav")[0]
SLOT = (0.655, 1.045)     # 'lender' in clip 3 (from the 'l' onset to the end of '-er')
def build(law_start=2.21, law_end=2.53, pitch=1.063, fit=1.0, lead=0.0):
    law = seg(c5, law_start, law_end)
    slot = SLOT[1] - SLOT[0]
    # fit=1 squeezes/stretches into the slot; fit=0 keeps natural length (rest of the slot stays silent)
    tempo = 1.0 + fit * (len(law)/SR/slot - 1.0)
    law = rb(law, tempo=tempo, pitch=pitch)
    if lead > 0: law = np.concatenate([np.zeros((int(lead*SR),2)), law])
    n = int(slot*SR); law = law[:n] if len(law) >= n else np.concatenate([law, np.zeros((n-len(law),2))])
    nzv = law[np.abs(law).sum(1) > 1e-6]; law *= rms(seg(c3, *SLOT)) / rms(nzv)
    k = int(0.012*SR); r = np.linspace(0,1,k)[:,None]
    nz = np.nonzero(np.abs(law).sum(1) > 1e-6)[0]; s0, s1 = nz[0], nz[-1] + 1
    law[s0:s0+k] *= r; law[s1-k:s1] *= r[::-1]
    y = c3.copy(); a = int(SLOT[0]*SR)
    y[a:a+n] = law            # the slot edges are near-silent (gap after 'like', closure before 'fees')
    return y
if __name__ == "__main__":
    a = [float(v) for v in sys.argv[1].split(",")] if len(sys.argv) > 1 and sys.argv[1] else []
    y = build(*a); out = sys.argv[2] if len(sys.argv) > 2 else "work/c3_fixed.wav"
    sf.write(out, y, SR); print("len", round(len(y)/SR, 3))
