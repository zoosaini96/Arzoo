# Maternity-leave mortgage explainer: edit notes and credits

**Output:** `maternity-leave-mortgage-explainer.mp4` is 1080x1920 (9:16), 30 fps, about 43.2 s, H.264/AAC, -15.5 LUFS.

The three source clips are joined in upload order: hook, return-to-work letter, how lenders decide and advice.

## Third-party media (Mixkit Free License: free for commercial use, no attribution required)
B-roll (mixkit.co video IDs): 24945 (aerial view of suburban homes), 17051 (signing a document), 49970 (mother and baby), 33357 (couple with house keys).

Music: "Happy Home" (Mixkit track 801).

Sound effects (Mixkit SFX IDs): 3005 light pop whoosh, 166 fast sweep, 1490 fast whoosh, 2870 correct-answer tone,
2354 message pop, 2357 bubble pop, 951 positive notification, 938 uplifting bells.

All motion graphics, icons and captions were drawn programmatically (Inter font, SIL Open Font License).

## Rebuild
`edit/build.py` composites the A-roll, B-roll cards, graphics and captions. `edit/mix.py` mixes the speech, ducked music and SFX.
Both scripts expect the workspace layout `src/c1..c3.mov`, `dl/broll`, `dl/music` and `dl/sfx` next to the `edit/` folder.

## Speech edits
In clip 2, 5.933–6.267 s of the source is removed so "current position" becomes "position".
In clip 3, about 0.13 s (10.567–10.700 s of the source) is removed from the spoken word "debits", so it is heard as "debts".
Each cut is hidden behind a punch-in zoom.
