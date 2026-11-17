"""Mix cleaned speech + ducked music + SFX, then mux with the rendered video."""
import json, subprocess
from timeline import S
OUT, SFX = f"{S}/out", f"{S}/dl/sfx"
e = json.load(open(f"{OUT}/events.json")); T, E = e["TOTAL"], e["SPEECH_END"]
ev = [(e["TITLE_K"], "3005", 0.5), (e["TITLE_4"] - 0.1, "1490", 0.45), (e["TITLE_4"] + 0.1, "2354", 0.55)]
for t in e["TIPS"]: ev += [(t - 0.08, "1490", 0.45), (t + 0.05, "2870", 0.4)]
for t in e["BROLL"]: ev.append((t - 0.05, "166", 0.4))
ev += [(e["BUDGET"], "2354", 0.45), (e["PRO"], "2354", 0.45)] + [(t, "951", 0.35) for t in e["WARN"]]
ev += [(e["CHECK"][0], "2354", 0.4)] + [(t, "2357", 0.6) for t in e["CHECK"][1:]]
ev.append((E, "938", 0.45))
inputs = ["-i", f"{OUT}/speech.wav", "-i", f"{S}/dl/music/m474.mp3"]
fc = [f"[0:a]apad=whole_dur={T}[sp]",
      f"[1:a]atrim=0:{T},asetpts=PTS-STARTPTS,aresample=48000,volume='if(lt(t,{E}),0.12,0.12+0.24*min(1,(t-{E})/0.6))':eval=frame,"
      f"afade=t=in:d=0.6,afade=t=out:st={T-1.6}:d=1.6[mu]"]
labs = ["[sp]", "[mu]"]
for i, (t, f, v) in enumerate(ev):
    inputs += ["-i", f"{SFX}/s{f}.mp3"]
    fc.append(f"[{i+2}:a]aresample=48000,volume={v},adelay={int(max(0, t) * 1000)}:all=1[x{i}]"); labs.append(f"[x{i}]")
fc.append("".join(labs) + f"amix=inputs={len(labs)}:normalize=0:duration=first,alimiter=limit=0.95,atrim=0:{T}[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[a]", "-c:a", "pcm_s16le", f"{OUT}/mix.wav"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/video_noaudio.mp4", "-i", f"{OUT}/mix.wav", "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", f"{OUT}/final.mp4"], check=True)
print("done")
