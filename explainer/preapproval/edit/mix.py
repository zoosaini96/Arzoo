"""Mixes cleaned speech, ducked background music and timed sound effects, then muxes the final MP4."""
import json, subprocess, os
S = os.environ.get("WS") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{S}/out"; SFX = f"{S}/dl/sfx"
tl = json.load(open(f"{OUT}/timeline.json")); T = tl["TOTAL"]; E = tl["SPEECH_END"]
ev = [(0.05, "3005", 0.7), (tl["STAMP"], "2870", 0.5)]
ev += [(b[0] - 0.08, "166" if i % 2 == 0 else "1490", 0.4) for i, b in enumerate(tl["BROLL"])]
ev += [(t, "2354", 0.45) for t in tl["REASONS"]]
ev += [(t, "2357", 0.6) for t in tl["CL1"] + tl["CL2"]]
ev += [(tl["NEQ"], "2869", 0.35), (E, "938", 0.45)]
ins = ["-i", f"{OUT}/speech.wav", "-i", f"{S}/dl/music/m801.mp3"]
fc = [f"[0:a]apad=whole_dur={T}[sp]",
      f"[1:a]atrim=0:{T},asetpts=PTS-STARTPTS,aresample=48000,volume='if(lt(t,{E}),0.12,0.12+0.22*min(1,(t-{E})/0.6))':eval=frame,"
      f"afade=t=in:d=0.8,afade=t=out:st={T-1.6}:d=1.6[mu]"]
labs = ["[sp]", "[mu]"]
for i, (t, f, v) in enumerate(ev):
    ins += ["-i", f"{SFX}/s{f}.mp3"]
    fc.append(f"[{i+2}:a]aresample=48000,volume={v},adelay={int(max(0, t)*1000)}:all=1[x{i}]"); labs.append(f"[x{i}]")
fc.append("".join(labs) + f"amix=inputs={len(labs)}:normalize=0:duration=first,alimiter=limit=0.95,atrim=0:{T}[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[a]", "-c:a", "pcm_s16le", f"{OUT}/mix.wav"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/video_noaudio.mp4", "-i", f"{OUT}/mix.wav", "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", f"{OUT}/final.mp4"], check=True)
print("done")
