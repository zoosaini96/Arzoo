"""Shared timeline: source segments (clip, in, out) joined in upload order."""
import os, json
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
SEGS = [  # (clip, src_in, src_out)
    (1, 0.45, 7.87),
    (2, 0.00, 5.673),
    (3, 0.00, 2.145),
    (4, 0.25, 9.21),
    (5, 0.50, 0.98), (5, 1.20, 3.80), (5, 4.10, 10.33),   # tighten two long pauses in tip 3
    (6, 0.00, 7.867),
    (7, 0.00, 3.47),
    (8, 0.20, 3.99),
]
def _frames(d): return int(round(d * FPS))
STARTS, t = [], 0
for c, a, b in SEGS:
    STARTS.append(t); t += _frames(b - a) / FPS
SPEECH_END = t
def g(clip, ts):
    """source time in clip -> output time"""
    best = None
    for (c, a, b), s0 in zip(SEGS, STARTS):
        if c != clip: continue
        if a - 1e-3 <= ts <= b + 1e-3: return s0 + ts - a
        if ts < a and best is None: return s0      # inside a removed gap -> snap to next segment start
        best = s0 + b - a
    return best
def seg_bounds():
    return [(s0, s0 + _frames(b - a) / FPS, c) for (c, a, b), s0 in zip(SEGS, STARTS)]
