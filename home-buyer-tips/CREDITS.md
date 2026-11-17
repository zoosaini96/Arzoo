# "4 things every home buyer should know" explainer: edit notes and credits

**Output:** `home-buyer-tips-explainer.mp4` is 1080x1920 (9:16), 30 fps, about 52.2 s, H.264/AAC, about -15 LUFS.

The 8 source clips are joined in upload order: intro, tip 1 (2 clips), tip 2, tip 3, tip 4, outro (2 clips).

## Edits
- Dead air at clip heads is trimmed. Two long pauses in tip 3 are tightened, and each cut is hidden by a change of framing.
- Presenter relit: warmer white balance, lifted shadows on face and hands, black outfit kept deep.
  The person is separated using the MediaPipe selfie-multiclass segmenter (Apache 2.0).
- Background: golden-hour grade, blue sky replacement, soft portrait-style depth blur, vignette and warm glow.
- Framing is knee-up instead of full body, with punch-ins on key lines.
- Motion graphics: hook title, TIP 01-04 banners with a progress tracker, budget meter, warning cards,
  a checklist synced to the speech, a "speak with your mortgage professional" card, and a recap end card.
- Captions are word-synced (Whisper transcript) with the active word highlighted and keywords in amber.

## Third-party media (Mixkit Free License: free for commercial use, no attribution required)
B-roll (mixkit.co video IDs): 24945 (aerial suburb), 14977 (couple with advisor), 23476 (car dealership),
23420 (furniture store), 46977 (documents and magnifying glass), 5660 (job interview), 33357 (couple with house keys).

Music: Mixkit track 474 ("Motivating Mornings").

Sound effects (Mixkit SFX IDs): 3005, 166, 1490, 2870, 2354, 2357, 951, 938.

All graphics are drawn programmatically (Inter font, SIL Open Font License).

## Rebuild
The scripts expect the workspace layout `src/c1..c8.mov` plus `src/words.json`, `dl/broll`, `dl/music`, `dl/sfx` and `dl/mc.tflite` next to `edit/`.
Run them in this order: `prep.py`, then `enhance.py` (in chunks), then `build.py`, then `mix.py`.
