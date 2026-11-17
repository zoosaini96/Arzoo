# "4 things every home buyer should know" explainer: edit notes and credits

**Output:** `home-buyer-tips-explainer.mp4` is 1080x1920 (9:16), 30 fps, about 49.4 s, H.264/AAC, about -15.5 LUFS.

The 8 source clips are joined in upload order: intro, tip 1 (2 clips), tip 2, tip 3, tip 4, outro (2 clips).

## Edit (minimal, natural version)
- Dead air at clip heads is trimmed, and two long pauses in tip 3 are tightened.
- One colour grade on the whole frame (no cut-out, no background blur): softer shadows, gentle warmth in the shadows and midtones, cleaner blue in the highlights, more natural colour in the grass and wood, and light sharpening.
- Gentle push-in within each shot.
- Full-screen B-roll, used only on the matching words, with quick dissolves.
- Clean captions: white text with a soft shadow and the spoken word in yellow, kept in the lower part of the frame.
- Quiet music bed and one soft whoosh per B-roll. The video fades in and out.

## Third-party media (Mixkit Free License: free for commercial use, no attribution required)
B-roll (mixkit.co video IDs, 720p): 6021 (agent showing a home, "house hunt"), 23476 (car dealership, "financing a car"),
23420 (furniture store, "furniture"), 46977 (documents and magnifying glass, "review your terms"),
5660 (job interview, "switching your job"), 14977 (advisor with clients, "mortgage professional"),
33357 (couple with house keys, "before buying a home").

Music: Mixkit track 474 ("Motivating Mornings"). Sound effect: Mixkit SFX 166.

Captions use the Inter font (SIL Open Font License).

## Rebuild
The scripts expect the workspace layout `src/c1..c8.mov` plus `src/words.json`, `dl/broll`, `dl/music` and `dl/sfx` next to `edit/`.
Run them in this order: `prep.py`, then `build2.py`, then `mix2.py`.
`enhance.py` and `mix.py` belong to the earlier heavy-effects version and are not used.
