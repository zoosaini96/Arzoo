"""Speech + quiet music bed + one soft whoosh per B-roll."""
import json, subprocess
from timeline import S
OUT, SFX = f"{S}/out", f"{S}/dl/sfx"
e = json.load(open(f"{OUT}/events2.json")); T = e["TOTAL"]
inputs = ["-i", f"{OUT}/speech.wav", "-i", f"{S}/dl/music/m474.mp3"]
fc = [f"[0:a]apad=whole_dur={T}[sp]",
      f"[1:a]atrim=0:{T},asetpts=PTS-STARTPTS,aresample=48000,volume=0.09,afade=t=in:d=1.0,afade=t=out:st={T-1.5}:d=1.5[mu]"]
labs = ["[sp]", "[mu]"]
for i, t in enumerate(e["BROLL"]):
    inputs += ["-i", f"{SFX}/s166.mp3"]
    fc.append(f"[{i+2}:a]aresample=48000,volume=0.18,adelay={int(max(0, t - 0.12) * 1000)}:all=1[x{i}]"); labs.append(f"[x{i}]")
fc.append("".join(labs) + f"amix=inputs={len(labs)}:normalize=0:duration=first,alimiter=limit=0.95,atrim=0:{T}[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[a]", "-c:a", "pcm_s16le", f"{OUT}/mix2.wav"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/v2_noaudio.mp4", "-i", f"{OUT}/mix2.wav", "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", f"{OUT}/final2.mp4"], check=True)
print("done")
