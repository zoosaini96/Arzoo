"""Join the source clips (trimmed) into one A-roll + cleaned speech track."""
import subprocess
from timeline import S, SEGS, FPS, _frames
v, a, n = [], [], len(SEGS)
inputs = []
for i in range(1, 9): inputs += ["-i", f"{S}/src/c{i}.mov"]
for k, (c, s, e) in enumerate(SEGS):
    d = _frames(e - s) / FPS
    v.append(f"[{c-1}:v]trim=start={s}:duration={d:.4f},setpts=PTS-STARTPTS,fps={FPS}[v{k}]")
    a.append(f"[{c-1}:a]atrim=start={s}:duration={d:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,afade=t=out:st={d-0.008:.4f}:d=0.008[a{k}]")
fc = ";".join(v + a) + ";" + "".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0,scale=1080:1920:flags=lanczos,format=yuv420p[v];" \
     + "".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1,highpass=f=80,afftdn=nf=-25,equalizer=f=3500:t=q:w=1.2:g=2," \
     "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000[s]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "10",
                "-preset", "fast", f"{S}/out/aroll_raw.mp4", "-map", "[s]", "-ac", "2", f"{S}/out/speech.wav"], check=True)
print("prep done")
