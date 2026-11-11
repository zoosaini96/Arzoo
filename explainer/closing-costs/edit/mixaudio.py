import json, subprocess, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
tl=json.load(open("out/timeline.json")); total=tl["total"]
ins=[]; fc=[]
# voice pieces
for k,(c,a,b) in enumerate(tl["segs"]):
    ins += ["-i", "work/c6_fixed.wav" if c == 6 else f"work/c{c}.mov"]  # clip 6: "reach out to me" splice
    d=b-a
    fc.append(f"[{k}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:d=0.015,afade=t=out:st={d-0.02:.3f}:d=0.02[v{k}]")
n=len(tl["segs"])
fc.append("".join(f"[v{k}]" for k in range(n))+f"concat=n={n}:v=0:a=1,highpass=f=90,afftdn=nr=10:nf=-45,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.4:g=3.5,equalizer=f=6500:t=q:w=1:g=-1.5,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=3,apad=whole_dur={total}[voice]")
fc.append("[voice]asplit=2[vmix][vkey]")
# music
mi=n; ins += ["-i","assets/mu_34.mp3"]
fc.append(f"[{mi}:a]atrim=0:{total},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,volume=0.24,afade=t=in:d=0.8,afade=t=out:st={total-1.6:.2f}:d=1.6[mus]")
fc.append("[mus][vkey]sidechaincompress=threshold=0.05:ratio=3:attack=30:release=400:makeup=1[mduck]")
# sfx
labels=[]
for j,s in enumerate(tl["sfx"]):
    ii=n+1+j; ins += ["-i", f"assets/sfx_{s['f']}.mp3"]
    ms=int(s["t"]*1000)
    fc.append(f"[{ii}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s['v']},adelay={ms}|{ms}[s{j}]")
    labels.append(f"[s{j}]")
fc.append(f"[vmix][mduck]{''.join(labels)}amix=inputs={2+len(labels)}:normalize=0:duration=first,alimiter=limit=0.95[pre]")
fc.append("[pre]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]")
cmd=["ffmpeg","-v","error","-y"]+ins+["-filter_complex",";".join(fc),"-map","[out]","-t",f"{total}","-c:a","pcm_s16le","out/audio.wav"]
subprocess.run(cmd,check=True)
print("ok")
