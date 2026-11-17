# "4 things every home buyer should know" explainer: edit notes and credits

**Output:** `home-buyer-tips-explainer.mp4` is 1080x1920 (9:16), 30 fps, 51.9 s, H.264/AAC, about -15 LUFS.

The 8 source clips are joined in the order they were provided (intro, tip 1, tip 1 continued, tip 2, tip 3, tip 4, closing, thank you).

## Picture fixes
- The iPhone footage is HDR (HLG). It is tone-mapped to standard SDR (hable) so it does not look washed out on normal screens.
- The sagging cable in the sky behind the speaker is tracked frame by frame and painted out (`edit/wire.py`).

## Speech edit
In clip 4 an "or" is inserted between "car" and "furniture" (0.2 s). The sound is the "-ore" of "before closing" from the same clip (5.075–5.245 s, flat ~210 Hz). It is used at original speed, raised to match her level, and laid over clip-4 room tone. The video holds for those frames behind the B-roll card.

## Third-party media (Mixkit Free License: free for commercial use, no attribution required)
B-roll (mixkit.co video IDs): 24945 (aerial of modern suburban homes), 6021 (couple viewing a house), 4533 (calculator),
23989 (luxury car showroom), 4046 (elegant furnished room), 21373 (meeting with an advisor), 36136 (couple with house keys).

Music: "Motivating Mornings" (Mixkit track 33).

Sound effects (Mixkit SFX IDs): 3005, 166, 1490, 2870, 2354, 2357, 938.

All motion graphics, icons and captions are drawn in code (Inter font, SIL Open Font License).

## Rebuild
`edit/wire.py <n> clean` removes the cable from `sdr/c<n>.mp4`. `edit/build.py` composites the video and `edit/mix.py` mixes speech, music and SFX.
