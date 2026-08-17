#!/usr/bin/env python3
"""Generate the compact retro-terminal profile GIF (assets/profile-terminal.gif).

The animation mimics a small shell window: it types `whoami`, reveals a short
personal profile line-by-line, ends on `status: building...`, and leaves a
blinking cursor before looping (~7s).

Inspired by x0rzavi/github-readme-terminal (gifos). gifos itself needs FFmpeg,
so to keep this fully self-contained (no system dependencies, no external
hosting) the frames are rendered with Pillow and written straight to a looping
GIF -- matching the profile's existing "Python generates the asset" pattern.

    python scripts/generate_profile_terminal.py
    python scripts/generate_profile_terminal.py --output assets/profile-terminal.gif

Only dependency: Pillow.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "assets" / "profile-terminal.gif"

# --- geometry --------------------------------------------------------------
W = 320
FS = 14            # font size (px)
LINE_H = 20        # row pitch
PAD_X = 14
TOP_BAR = 22       # minimal retro title strip
PAD_TOP = 10
PAD_BOTTOM = 12

# --- palette (cohesive with headings / garden / badges) --------------------
BG = "#0d1117"     # terminal interior (blends with GitHub dark)
BAR = "#131c2b"    # title strip
EDGE = "#2a3b58"   # subtle border (same edge used across the profile assets)
CREAM = "#ede4d3"  # warm off-white body text
BRIGHT = "#f8fafc" # entered command
LAV = "#b7a8e0"    # muted lavender prompt / labels
GREEN = "#8fce7f"  # muted green: prompt symbol, bullets, status (garden green)
PINK = "#f2a7ce"   # soft pink accent (name + cursor)
DIM = "#6b7a95"    # dim host / chrome text

FONT_CANDIDATES = [
    "C:/Windows/Fonts/courbd.ttf",                         # Courier New Bold (Windows)
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/System/Library/Fonts/Menlo.ttc",                     # macOS
]

# --- terminal content ------------------------------------------------------
PROMPT = [("jeeya7", LAV), ("@github", DIM), (":~$ ", GREEN)]
COMMAND = "whoami"

# each output row is a list of (text, color) segments; [] is a blank line
OUTPUT = [
    [],
    [("Jiya Pradhan", PINK)],
    [("Senior @ Oregon State University", CREAM)],
    [("Computer Science", CREAM)],
    [],
    [("focus:", LAV)],
    [("> ", GREEN), ("Applied AI", CREAM)],
    [("> ", GREEN), ("chai 24/7", CREAM)],
    [("> ", GREEN), ("graduate school", CREAM)],
    [("> ", GREEN), ("human-centered tools", CREAM)],
    [],
    [("status: ", CREAM), ("building...", GREEN)],
]
FINAL_ROW = len(OUTPUT) + 1  # blank line separates output from the next prompt


def load_font(override: str | None) -> ImageFont.FreeTypeFont:
    for path in ([override] if override else []) + FONT_CANDIDATES:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, FS)
    sys.exit("error: no monospace font found; pass --font <path to a .ttf>")


def _row_center(row: int) -> float:
    return TOP_BAR + PAD_TOP + row * LINE_H + LINE_H / 2


def _draw_segments(draw, font, row, segments):
    """Draw colored segments left-to-right; return the x where text ends."""
    x = PAD_X
    y = _row_center(row)
    for text, color in segments:
        draw.text((x, y), text, font=font, fill=color, anchor="lm")
        x += draw.textlength(text, font=font)
    return x


def render(font, *, cmd: str, n_out: int, final: bool, cursor):
    """Render one full screen. ``cursor`` is None or (target, on)."""
    cell = font.getlength("M")
    img = Image.new("RGB", (W, TOTAL_H), BG)
    d = ImageDraw.Draw(img)

    # window chrome: border + minimal title strip with three pixel dots
    d.rectangle([0, 0, W - 1, TOTAL_H - 1], outline=EDGE, width=1)
    d.rectangle([1, 1, W - 2, TOP_BAR], fill=BAR)
    d.line([1, TOP_BAR + 1, W - 2, TOP_BAR + 1], fill=EDGE)
    for i, color in enumerate((PINK, LAV, GREEN)):
        dx = PAD_X + i * 12
        d.rectangle([dx, TOP_BAR // 2 - 3, dx + 6, TOP_BAR // 2 + 3], fill=color)
    d.text((W - PAD_X, TOP_BAR / 2), "bash", font=font, fill=DIM, anchor="rm")

    def block_cursor(x, row):
        cy = _row_center(row)
        d.rectangle([x + 1, cy - FS / 2, x + 1 + cell, cy + FS / 2], fill=PINK)

    # prompt + (partial) command
    x = _draw_segments(d, font, 0, PROMPT + [(cmd, BRIGHT)])
    if cursor and cursor[0] == "cmd" and cursor[1]:
        block_cursor(x, 0)

    # revealed output
    for row in range(1, n_out + 1):
        _draw_segments(d, font, row, OUTPUT[row - 1])

    # trailing prompt with blinking cursor
    if final:
        x = _draw_segments(d, font, FINAL_ROW, PROMPT)
        if cursor and cursor[0] == "final" and cursor[1]:
            block_cursor(x, FINAL_ROW)

    return img


def build_frames(font):
    frames, durations = [], []

    def add(img, ms):
        frames.append(img)
        durations.append(ms)

    # 1. window + prompt, cursor waiting
    add(render(font, cmd="", n_out=0, final=False, cursor=("cmd", True)), 550)

    # 2. type the command
    for i in range(1, len(COMMAND) + 1):
        add(render(font, cmd=COMMAND[:i], n_out=0, final=False, cursor=("cmd", True)), 85)

    # 3. brief pause after "pressing enter"
    add(render(font, cmd=COMMAND, n_out=0, final=False, cursor=("cmd", True)), 450)

    # 4. reveal the profile line-by-line
    for k in range(1, len(OUTPUT) + 1):
        add(render(font, cmd=COMMAND, n_out=k, final=False, cursor=None), 175)

    # 5. next prompt with a blinking cursor
    for on, ms in [(True, 550), (False, 380), (True, 550), (False, 380), (True, 550)]:
        add(render(font, cmd=COMMAND, n_out=len(OUTPUT), final=True, cursor=("final", on)), ms)

    # 6. hold before looping
    add(render(font, cmd=COMMAND, n_out=len(OUTPUT), final=True, cursor=("final", True)), 1000)

    return frames, durations


def save_gif(path: Path, frames, durations):
    # build a stable palette from a fully-populated frame so colors don't flicker
    palette_src = frames[-1].convert("P", palette=Image.ADAPTIVE, colors=64)
    quantized = [f.quantize(palette=palette_src, dither=Image.Dither.NONE) for f in frames]
    path.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        path, save_all=True, append_images=quantized[1:],
        duration=durations, loop=0, disposal=2, optimize=True,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--font", default=None, help="override path to a monospace .ttf")
    args = parser.parse_args(argv)

    font = load_font(args.font)
    frames, durations = build_frames(font)
    save_gif(args.output, frames, durations)
    print(f"wrote {args.output}  ({len(frames)} frames, {sum(durations)/1000:.1f}s loop, "
          f"{args.output.stat().st_size // 1024} KB, {W}x{TOTAL_H})")
    return 0


TOTAL_H = TOP_BAR + PAD_TOP + (FINAL_ROW + 1) * LINE_H + PAD_BOTTOM

if __name__ == "__main__":
    raise SystemExit(main())
