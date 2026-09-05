"""
Generates assets/banner.gif -- the README hero.

ASCII rain condenses into a two-line wordmark, holds with a glitch shimmer,
then dissolves back into rain. The loop is seamless: every column's fall is
periodic over exactly the frame count, so the last frame flows into the first.

The wordmark is stacked on two lines on purpose. On one line, 13 characters
across an 800px canvas leaves each letter only about four grid rows tall, and
the letterforms turn to mush. Two lines roughly doubles the vertical
resolution per letter. Both lines share one font size (fitted to the longer
word) so they read as a single logotype.

Palette comes from the README itself (#0d0b14 ground, violet accents), and
frames are quantised to a small palette to keep the GIF small.

Rerun:  python3 scripts/gen_banner_gif.py
"""
import random
from PIL import Image, ImageDraw, ImageFont

random.seed(7)

COLS, ROWS = 118, 30
CELL_W, CELL_H = 7, 13
W, H = COLS * CELL_W, ROWS * CELL_H

FRAMES = 52
FRAME_MS = 70

BG = (13, 11, 20)
RAIN = [(26, 20, 46), (46, 30, 92), (78, 46, 158), (123, 64, 255), (185, 150, 255), (233, 222, 255)]
MARK = [(92, 48, 175), (140, 66, 240), (178, 110, 255), (219, 186, 255), (246, 241, 255)]
CAPTION = (116, 96, 172)

GLYPHS = "01<>[]{}()/\\|=+-*#%$&@?!:;._^~"

MONO_PATHS = ["/System/Library/Fonts/Menlo.ttc"]
BOLD_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def load(paths, size, index=0):
    for p in paths:
        try:
            return ImageFont.truetype(p, size, index=index)
        except Exception:
            continue
    raise SystemExit("no usable font found")


MONO = load(MONO_PATHS, 12)

LINE1, LINE2 = "SAKSHAM", "ARORA"
TRACK = 0.30          # extra advance per letter, in cells
BAND_ROWS = 11
L1_TOP, L2_TOP = 3, 14
CAP_ROW = 27


def advance(text, font, draw):
    return draw.textlength(text, font=font) + TRACK * CELL_W * max(0, len(text) - 1)


def fit_font():
    """One size for both lines, fitted to the longer word so the two lines
    share a cap height and read as one logotype."""
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    max_w, max_h = W * 0.80, BAND_ROWS * CELL_H * 0.92
    chosen, size = None, 10
    while size < 460:
        f = load(BOLD_PATHS, size)
        bb = f.getbbox(LINE1)
        if advance(LINE1, f, probe) > max_w or (bb[3] - bb[1]) > max_h:
            break
        chosen, size = f, size + 2
    return chosen or load(BOLD_PATHS, 12)


FONT = fit_font()


def band_mask(text, top):
    """Render one word at full canvas resolution, then downsample so each grid
    cell carries a 0..1 coverage value. Rendering large first is what keeps
    letterforms correct despite cells being about twice as tall as wide."""
    band_h = BAND_ROWS * CELL_H
    img = Image.new("L", (W, band_h), 0)
    d = ImageDraw.Draw(img)
    bb = FONT.getbbox(text)
    x = (W - advance(text, FONT, d)) / 2
    y = (band_h - (bb[3] - bb[1])) / 2 - bb[1]
    for ch in text:
        d.text((x, y), ch, font=FONT, fill=255)
        x += d.textlength(ch, font=FONT) + TRACK * CELL_W
    small = img.resize((COLS, BAND_ROWS), Image.LANCZOS)
    px = small.load()
    return {(top + r, c): px[c, r] / 255.0
            for r in range(BAND_ROWS) for c in range(COLS) if px[c, r] > 74}


NAME = {}
NAME.update(band_mask(LINE1, L1_TOP))
NAME.update(band_mask(LINE2, L2_TOP))

# reveal order: a left-to-right wipe, roughened per cell so the wordmark
# materialises instead of sliding in like a curtain
ORDER = {k: min(1.0, (k[1] / COLS) * 0.78 + random.random() * 0.3) for k in NAME}

CAPTION_TEXT = "data science  ·  quant research"
CAP_COL = (COLS - len(CAPTION_TEXT)) // 2

# Each column falls a whole number of cycles across the loop, so the last
# frame hands off cleanly to the first.
PERIOD = ROWS + 14
COLUMNS = [{"start": random.uniform(0, PERIOD),
            "cycles": random.choice([1, 1, 2, 2, 3]),
            "tail": random.randint(7, 17)} for _ in range(COLS)]
JITTER = [[random.random() for _ in range(ROWS)] for _ in range(COLS)]


def envelope(t):
    """rain -> reveal -> hold -> dissolve, back to rain."""
    if t < 0.20:
        return 0.0
    if t < 0.40:
        return (t - 0.20) / 0.20
    if t < 0.72:
        return 1.0
    if t < 0.90:
        return 1.0 - (t - 0.72) / 0.18
    return 0.0


frames = []
for f in range(FRAMES):
    t = f / FRAMES
    reveal = envelope(t)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    locked = {c for c, thr in ORDER.items() if reveal >= thr} if reveal > 0 else set()

    for c, col in enumerate(COLUMNS):
        head = (col["start"] + col["cycles"] * PERIOD * t) % PERIOD
        for r in range(ROWS):
            if (r, c) in locked:
                continue
            dist = (head - r) % PERIOD
            if dist >= col["tail"]:
                continue
            k = 1.0 - dist / col["tail"]
            idx = min(len(RAIN) - 1, int(k * (len(RAIN) - 0.01)))
            # rain thins while the wordmark holds, so the name stays readable
            if reveal > 0 and idx > 0 and JITTER[c][r] < reveal * 0.55:
                idx -= 1
            if idx == 0 and reveal > 0.5:
                continue
            g = GLYPHS[int((JITTER[c][r] * 977 + f * (1 + c % 3)) % len(GLYPHS))]
            d.text((c * CELL_W, r * CELL_H), g, font=MONO, fill=RAIN[idx])

    for (r, c) in locked:
        cov = NAME[(r, c)]
        # a few cells flicker while holding, so it reads as alive, not static
        flick = reveal >= 1.0 and ((f * 7 + c * 13 + r * 31) % 191) < 3
        idx = min(len(MARK) - 1, int(cov * (len(MARK) - 0.01)))
        if flick:
            idx = max(0, idx - 2)
        d.text((c * CELL_W, r * CELL_H), "█" if cov >= 0.55 else "▓",
               font=MONO, fill=MARK[idx])

    if reveal >= 1.0:
        d.rectangle([(CAP_COL - 2) * CELL_W, (CAP_ROW - 1) * CELL_H + 3,
                     (CAP_COL + len(CAPTION_TEXT) + 2) * CELL_W, (CAP_ROW + 1) * CELL_H + 1],
                    fill=BG)
        for i, ch in enumerate(CAPTION_TEXT):
            if ch != " ":
                d.text(((CAP_COL + i) * CELL_W, CAP_ROW * CELL_H), ch, font=MONO, fill=CAPTION)

    frames.append(img.quantize(colors=16, method=Image.MEDIANCUT, dither=Image.NONE))

frames[0].save("assets/banner.gif", save_all=True, append_images=frames[1:],
               duration=FRAME_MS, loop=0, optimize=True)
print(f"assets/banner.gif  {W}x{H}  {FRAMES} frames  font={FONT.size}pt")
