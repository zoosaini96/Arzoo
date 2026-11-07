import json, subprocess, os
S=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=f"{S}/out"; SFX=f"{S}/dl/sfx"
tl=json.load(open(f"{OUT}/timeline.json")); T=tl["TOTAL"]; E=tl["SPEECH_END"]; O2=tl["O2"]; O3=tl["O3"]; B=tl["BROLL"]
g1=lambda t:t-0.55; g2=lambda t:t+O2-(tl["CUTLEN2"] if t>=tl["CUT2"][1]-0.001 else 0); g3=lambda t:t+O3-(tl["CUTLEN"] if t>=tl["CUT3"][1]-0.001 else 0)
ev=[(g1(0.62),"3005",0.7),(B[0],"166",0.45),(g1(5.25),"2870",0.55),
    (tl["B2"]-0.1,"1490",0.4),(B[1],"166",0.45),(g2(3.05),"2354",0.45),(g2(4.5),"2357",0.6),(g2(6.3),"2357",0.6),(g2(6.85),"2357",0.6),
    (tl["B3"]-0.1,"1490",0.4),(g3(2.9),"2354",0.45),(g3(7.95),"2354",0.45),
    (g3(8.6),"2357",0.6),(g3(9.8),"2357",0.6),(g3(10.9),"2357",0.6),(B[2]-0.1,"1490",0.35),(B[3],"166",0.45),(g3(18.6),"951",0.3),
    (E,"938",0.45)]
inputs=["-i",f"{OUT}/speech.wav","-i",f"{S}/dl/music/m801.mp3"]
fc=[f"[0:a]apad=whole_dur={T}[sp]",
    # music: low under speech, lift on end card, fade out
    f"[1:a]atrim=0:{T},asetpts=PTS-STARTPTS,aresample=48000,volume='if(lt(t,{E}),0.13,0.13+0.22*min(1,(t-{E})/0.6))':eval=frame,afade=t=in:d=0.8,afade=t=out:st={T-1.6}:d=1.6[mu]"]
labs=["[sp]","[mu]"]
for i,(t,f,v) in enumerate(ev):
    inputs+=["-i",f"{SFX}/s{f}.mp3"]; k=i+2
    fc.append(f"[{k}:a]aresample=48000,volume={v},adelay={int(max(0,t)*1000)}:all=1[x{i}]"); labs.append(f"[x{i}]")
fc.append("".join(labs)+f"amix=inputs={len(labs)}:normalize=0:duration=first,alimiter=limit=0.95,atrim=0:{T}[a]")
subprocess.run(["ffmpeg","-v","error","-y",*inputs,"-filter_complex",";".join(fc),"-map","[a]","-c:a","pcm_s16le",f"{OUT}/mix.wav"],check=True)
subprocess.run(["ffmpeg","-v","error","-y","-i",f"{OUT}/video_noaudio.mp4","-i",f"{OUT}/mix.wav","-map","0:v","-map","1:a",
  "-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",f"{OUT}/final.mp4"],check=True)
print("done")
