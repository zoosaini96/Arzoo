# Closing-costs explainer: edit notes and credits

**Output:** `closing-costs-explainer.mp4` is 1080x1920 (9:16), 30 fps, 41.6 s, H.264/AAC, -14 LUFS.

The six source clips are joined in upload order. Clip 1 ends with the line "down payment to ilava... closing costs kehnde han",
and clip 2 is a retake of that same line, so clip 1's copy (11.6–16.3 s) is dropped and clip 2's take is used.
The silent pause between the hook and "Wait..." in clip 1 (5.95–6.62 s) is also removed.

## Speech edit
In clip 6, "please feel free to reach me out" is re-ordered to "please feel free to reach out to me" (`edit/splice6_v2.py`):
- "out" is clip 6, 4.615–4.865 s (starting after the "me" glide).
- "to" is taken from clip 1 ("you need **to** budget", 8.555–8.705 s), because it has a crisp "t" and a full vowel.
- "me" is clip 6, 4.445–4.572 s, with its vowel lengthened (pitch kept) so it sounds phrase-final.
- The pieces are loudness-matched, with short natural pauses, before "thank you".
- The whole phrase "reach out to me" is slowed to 90% (pitch kept) and lifted slightly, so each word is distinct.
  Settings: `splice6_v2.py 0.615,0.5,0.06,0.07,1,1,0,0.9,1.18`.
- Full-screen B-roll (a woman typing a message on her phone) covers "please feel free to reach out to me", so the re-ordered words are never lip-synced on camera.
  The video returns to the presenter for "Thank you!", which is her original take.

The video over that span is gently slowed to stay in sync (`edit/warp6.py`).
The whole voice track also gets light noise reduction and a presence boost for clearer consonants, and the music sits further under it.

## Transitions
Every join between clips is an optical-flow morph cut (0.3 s) instead of a hard cut, and the zoom carries smoothly across each join, so the presenter no longer jumps between takes.

## Hook
The first ~4 s show a hook card aimed at clients: "FIRST-TIME HOME BUYERS / Saved your down payment? / *You're not done yet.*"
It is fully visible on the first frame, so it also works as the thumbnail.

## Clean-up on the presenter footage
- **House number "1105" removed** on every frame. The digits are detected per frame (handheld camera, so the position drifts),
  the box is smoothed over time, and the area is refilled with the trim band's own texture.
- The trousers keep their original colour. `edit/trousers.py` (beige recolour) is kept but switched off with `RECOLOR = False`
  in `edit/process_clips.py`.

## Visual style: warm editorial (`edit/compose_v2.py`)
This style is deliberately different from the navy/gold, all-caps look of the earlier videos.
- Palette: cream, forest green and terracotta, with a warm film grade (lifted blacks, warm balance, soft vignette).
- Type: EB Garamond (serif headlines), Manrope (captions and labels), DM Mono (receipt). All SIL Open Font License.
- Sentence-case captions on cream bars, with key words in terracotta.
- B-roll appears as tilted photo cards over the presenter's body, with a camera-shutter sound. Her face stays visible.
- The fee list is a printed receipt that types out line by line.
- Chapter tags (01 The surprise, 02 What's included, 03 Plan ahead, 04 Questions) and a "Closing Costs 101" series title.
- "Wait." briefly drains the colour from the frame. Headlines and title cards never cover her head.
- `edit/compose.py` (style 1: navy/gold) is kept for reference.

## Third-party media (Mixkit free licences: free for commercial use, no attribution required)
Only items marked with Mixkit's *Free* licence were used (no "Restricted" items).

B-roll (mixkit.co video IDs): 4009 (houses under a blue sky), 18263 (counting coins), 1717715134 (writing a list in a notebook),
4809 (business meeting), 241 (signing a contract), 43270 (woman typing on her phone, vertical 1080x1920).

Music: "Raising Me Higher" by Ahjay Stelino (Mixkit track 34, Mixkit Stock Music Free License). It sits well under the voice and rises in pauses and the outro.

Sound effects (Mixkit SFX IDs): 1133 camera shutter, 1125 typewriter soft click, 2995 stapling paper, 1490 fast whoosh, 1492 cinematic fast whoosh, 1489 air woosh, 2903 movie whoosh impact,
2354 message pop, 2357 bubble pop, 1993 clinking coins, 1120 box-check click, 938 uplifting bells.

Captions are English translations of the Punjabi/English speech. All motion graphics, icons and captions were drawn
programmatically (EB Garamond, Manrope and DM Mono fonts, SIL Open Font License).

## Rebuild
1. `edit/process_clips.py N` removes the house number and recolours the trousers for clip N (`work/cN.mov` to `work/cleanN.mp4`).
2. `edit/compose_v2.py` renders the layouts, B-roll, graphics and captions to `out/video.mp4`.
3. `edit/splice6_v2.py`, then `edit/warp6.py`, rebuild the clip 6 ending.
4. `edit/mixaudio.py` mixes the speech, ducked music and SFX to `out/audio.wav`; mux both with ffmpeg.

The scripts expect `work/`, `broll/`, `assets/` and `models/selfie_multiclass.tflite` next to them.
