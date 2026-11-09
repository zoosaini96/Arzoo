# Mortgage pre-approval explainer: edit notes and credits

**Output:** `mortgage-preapproval-explainer.mp4` is 1080x1920 (9:16), 30 fps, 41.3 s, H.264/AAC, about -15 LUFS.

The four uploaded clips are joined in the order they were provided and used in full: no speech is cut.
Clips 2-4 are iPhone HDR (HLG, BT.2020); they are tone-mapped to SDR BT.709 (hable, with brightness and saturation matched to clip 1) so skin tones look natural.

## Background clean-up (`edit/clean.py`)
Removed from every shot: the wooden pallets and the black polythene bag on the left, the grey plastic box on the grass,
the black covered object behind the speaker's shoulder, the bench by the fence, the AC unit and the dustbin edge on the right.
Each object is painted out once on a reference frame (inpainting + gravel and stucco textures), then tracked onto every frame
with a background homography. Pixels where the speaker moves in front are kept. The frame is then reframed (1.2x crop) so the yard edges drop out.

## Third-party media (Mixkit Free License: free for commercial use, no attribution required)
B-roll (mixkit.co video IDs): 24945 aerial suburban homes, 46994 calculating expenses, 4713 woman researching on the computer,
12946 realtor closes sale with young couple, 6021 couple viewing a new house.

Music: "Happy Home" (Mixkit track 801).

Sound effects (Mixkit SFX IDs): 3005, 166, 1490, 2870, 2869, 2354, 2357, 938.

Motion graphics, icons and captions are drawn programmatically (Inter and Noto Sans Gurmukhi fonts, SIL Open Font License).

## Rebuild
Workspace layout: `src/c1..c4.mov`, `dl/broll`, `dl/music`, `dl/sfx` next to `edit/`. Run `clean.py`, then `build.py`, then `mix.py`.

## Speech edit
In clip 1 the spoken order "sab ton ik zaruri step" is changed to "ik sab ton zaruri step" by swapping
4.30–4.62 s ("sab ton") and 4.62–4.845 s ("ik") of the source audio (4 ms crossfades, total length unchanged).
This happens under the aerial B-roll, so lip sync is not visible. Clip 1 captions are English translations of the Punjabi.
