#!/usr/bin/env python3
"""Generate small pixel-art footer icons as crisp SVGs.

Each icon is a hand-drawn 16x16 pixel map. A dark outline is added automatically
around every shape (any transparent cell touching the art becomes the outline
colour), so the whole set shares one cohesive "pixel sticker" treatment. Output
is SVG with shape-rendering="crispEdges" -- it scales to any inline size on
GitHub without blurring, matching the profile's other pixel assets.

    python scripts/generate_footer_icons.py

Outputs: assets/footer-icon-{portfolio,linkedin,email,heart}.svg
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

# --- palette (cohesive with headings / garden / terminal) ------------------
COLORS = {
    "K": "#0f172a",  # dark outline (added automatically)
    "P": "#f2a7ce",  # pink
    "p": "#f9c6de",  # light pink highlight
    "C": "#ede4d3",  # warm cream
    "B": "#2e7bc4",  # soft blue (linkedin)
    "W": "#f8fafc",  # white
    "L": "#b7a8e0",  # lavender
    "G": "#8fce7f",  # muted green
    "D": "#1b2433",  # dark window bar
}
OUTLINE = "K"

# 16x16 pixel maps ('.' = transparent). Art is kept within the inner 14x14 so
# the auto-outline has room. Every icon fills a similar area so that, displayed
# at one height, the pixels read at a consistent size across the set.
ICONS = {
    # tiny browser / portfolio window: dark title bar + pink/green/lavender
    # dots, cream screen with two lavender "content" lines
    "portfolio": [
        "................",
        "................",
        ".DDDDDDDDDDDDDD.",
        ".DPDGDLDDDDDDDD.",
        ".DDDDDDDDDDDDDD.",
        ".CCCCCCCCCCCCCC.",
        ".CLLLLLLLCCCCCC.",
        ".CCCCCCCCCCCCCC.",
        ".CLLLLLLLLLLCCC.",
        ".CCCCCCCCCCCCCC.",
        ".CCCCCCCCCCCCCC.",
        ".DDDDDDDDDDDDDD.",
        "................",
        "................",
        "................",
        "................",
    ],
    # linkedin "in" badge: soft-blue square with a white "in"
    "linkedin": [
        "................",
        "................",
        "..BBBBBBBBBBBB..",
        "..BBBBBBBBBBBB..",
        "..BBWBBBBBBBBB..",
        "..BBBBBBBBBBBB..",
        "..BBWBBWWWWBBB..",
        "..BBWBBWBBWBBB..",
        "..BBWBBWBBWBBB..",
        "..BBWBBWBBWBBB..",
        "..BBWBBWBBWBBB..",
        "..BBBBBBBBBBBB..",
        "..BBBBBBBBBBBB..",
        "................",
        "................",
        "................",
    ],
    # envelope: cream body with a dark flap "V"
    "email": [
        "................",
        "................",
        "................",
        ".CCCCCCCCCCCCCC.",
        ".CKCCCCCCCCCCKC.",
        ".CCKCCCCCCCCKCC.",
        ".CCCKCCCCCCKCCC.",
        ".CCCCKCCCCKCCCC.",
        ".CCCCCKCCKCCCCC.",
        ".CCCCCCKKCCCCCC.",
        ".CCCCCCCCCCCCCC.",
        ".CCCCCCCCCCCCCC.",
        ".CCCCCCCCCCCCCC.",
        "................",
        "................",
        "................",
    ],
    # pixel heart
    "heart": [
        "................",
        "................",
        "....PP....PP....",
        "...PpPP..PPPP...",
        "..PpPPPPPPPPPP..",
        "..PPPPPPPPPPPP..",
        "..PPPPPPPPPPPP..",
        "...PPPPPPPPPP...",
        "....PPPPPPPP....",
        ".....PPPPPP.....",
        "......PPPP......",
        ".......PP.......",
        "................",
        "................",
        "................",
        "................",
    ],
}


def add_outline(grid):
    """Return a new grid with OUTLINE added on transparent cells touching art."""
    h, w = len(grid), len(grid[0])
    out = [list(row) for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] != ".":
                continue
            touches = any(
                0 <= y + dy < h and 0 <= x + dx < w and grid[y + dy][x + dx] != "."
                for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx or dy)
            )
            if touches:
                out[y][x] = OUTLINE
    return out


def crop(grid):
    """Trim fully-transparent border rows/cols; return (grid, x0, y0)."""
    ys = [y for y, row in enumerate(grid) if any(c != "." for c in row)]
    xs = [x for x in range(len(grid[0])) if any(row[x] != "." for row in grid)]
    y0, y1, x0, x1 = ys[0], ys[-1], xs[0], xs[-1]
    return [row[x0:x1 + 1] for row in grid[y0:y1 + 1]], x0, y0


def to_svg(name, grid):
    grid = add_outline([list(r) for r in grid])
    grid, _, _ = crop(grid)
    h, w = len(grid), len(grid[0])
    rects = []
    for y, row in enumerate(grid):
        x = 0
        while x < w:
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            run = 1
            while x + run < w and row[x + run] == ch:
                run += 1
            rects.append(f'<rect x="{x}" y="{y}" width="{run}" height="1" fill="{COLORS[ch]}"/>')
            x += run
    body = "".join(rects)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" shape-rendering="crispEdges" role="img" '
        f'aria-label="{name} icon">{body}</svg>\n'
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, grid in ICONS.items():
        (OUT / f"footer-icon-{name}.svg").write_text(to_svg(name, grid), encoding="utf-8", newline="\n")
    print(f"wrote {len(ICONS)} footer icons to {OUT}")


if __name__ == "__main__":
    main()
