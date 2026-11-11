# Closing-costs explainer: edit notes and credits

**Output:** `closing-costs-explainer.mp4` is 1080x1920 (9:16), 30 fps, 40.9 s, H.264/AAC, -14 LUFS.

The six source clips are joined in upload order. Clip 1 ends with the line "down payment to ilava... closing costs kehnde han",
and clip 2 is a retake of that same line, so clip 1's copy (11.6–16.3 s) is dropped and clip 2's take is used.
The silent pause between the hook and "Wait..." in clip 1 (5.95–6.62 s) is also removed.

## Clean-up on the presenter footage
- **House number "1105" removed** on every frame. The digits are detected per frame (handheld camera, so the position drifts),
  the box is smoothed over time, and the area is refilled with the trim band's own texture.
- **Trousers recoloured to beige**. A MediaPipe multiclass segmentation mask (clothes class) is split at the waistline
  (navy shirt vs. black trousers), and the fabric is remapped to beige while keeping the folds and shading. The shoes are excluded.

## Third-party media (Mixkit free licences: free for commercial use, no attribution required)
Only items marked with Mixkit's *Free* licence were used (no "Restricted" items).

B-roll (mixkit.co video IDs): 4009 (houses under a blue sky), 18263 (counting coins), 1717715134 (writing a list in a notebook),
4809 (business meeting), 241 (signing a contract).

Music: "Motivating Mornings" by Ahjay Stelino (Mixkit track 33, Mixkit Stock Music Free License).

Sound effects (Mixkit SFX IDs): 1490 fast whoosh, 1492 cinematic fast whoosh, 1489 air woosh, 2903 movie whoosh impact,
2354 message pop, 2357 bubble pop, 1993 clinking coins, 1120 box-check click, 938 uplifting bells.

Captions are English translations of the Punjabi/English speech. All motion graphics, icons and captions were drawn
programmatically (Montserrat font, SIL Open Font License).

## Rebuild
1. `edit/process_clips.py N` removes the house number and recolours the trousers for clip N (`work/cN.mov` to `work/cleanN.mp4`).
2. `edit/compose.py` renders the layouts, B-roll, graphics and captions to `out/video.mp4`.
3. `edit/mixaudio.py` mixes the speech, ducked music and SFX to `out/audio.wav`; mux both with ffmpeg.

The scripts expect `work/`, `broll/`, `assets/` and `models/selfie_multiclass.tflite` next to them.
