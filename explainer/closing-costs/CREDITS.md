# Closing-costs explainer: edit notes and credits

**Output:** `closing-costs-explainer.mp4` is 1080x1920 (9:16), 30 fps, 40.9 s, H.264/AAC, -14 LUFS.

The six source clips are joined in upload order. Clip 1 ends with the line "down payment to ilava... closing costs kehnde han",
and clip 2 is a retake of that same line, so clip 1's copy (11.6–16.3 s) is dropped and clip 2's take is used.
The silent pause between the hook and "Wait..." in clip 1 (5.95–6.62 s) is also removed.

## Clean-up on the presenter footage
- **House number "1105" removed** on every frame. The digits are detected per frame (handheld camera, so the position drifts),
  the box is smoothed over time, and the area is refilled with the trim band's own texture.
- The trousers keep their original colour. `edit/trousers.py` (beige recolour) is kept but switched off with `RECOLOR = False`
  in `edit/process_clips.py`.

## Layout
The opening headline sits at the very top of the frame, clear of the presenter's head. "WAIT!", "CLOSING COSTS", the questions card and
"THANK YOU!" sit over the lower body, so no graphic covers her face.

## Third-party media (Mixkit free licences: free for commercial use, no attribution required)
Only items marked with Mixkit's *Free* licence were used (no "Restricted" items).

B-roll (mixkit.co video IDs): 4009 (houses under a blue sky), 18263 (counting coins), 1717715134 (writing a list in a notebook),
4809 (business meeting), 241 (signing a contract).

Music: "Raising Me Higher" by Ahjay Stelino (Mixkit track 34, Mixkit Stock Music Free License). It sits about 9 dB under the voice and rises in pauses and the outro.

Sound effects (Mixkit SFX IDs): 1490 fast whoosh, 1492 cinematic fast whoosh, 1489 air woosh, 2903 movie whoosh impact,
2354 message pop, 2357 bubble pop, 1993 clinking coins, 1120 box-check click, 938 uplifting bells.

Captions are English translations of the Punjabi/English speech. All motion graphics, icons and captions were drawn
programmatically (Montserrat font, SIL Open Font License).

## Rebuild
1. `edit/process_clips.py N` removes the house number and recolours the trousers for clip N (`work/cN.mov` to `work/cleanN.mp4`).
2. `edit/compose.py` renders the layouts, B-roll, graphics and captions to `out/video.mp4`.
3. `edit/mixaudio.py` mixes the speech, ducked music and SFX to `out/audio.wav`; mux both with ffmpeg.

The scripts expect `work/`, `broll/`, `assets/` and `models/selfie_multiclass.tflite` next to them.
