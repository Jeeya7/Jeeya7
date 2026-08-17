#!/usr/bin/env python3
"""Generate compact pixel-style text badges for technologies that have no
reliable skillicons.dev icon.

skillicons.dev does not support SQL, REST, Dapr, Playwright, Serilog, Zipkin,
Pandas or NumPy, so the inventory used to list them as a disconnected line of
pipe-separated text. These badges replace that line with self-hosted, dark-navy
"chip" tiles that harmonize with the profile's pixel/retro theme (Courier text,
navy tile, a small crisp accent pixel per technology).

Output: assets/badges/<slug>.svg

    python scripts/generate_badges.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "badges"

# --- palette (cohesive with heading + garden assets) -----------------------
BG = "#1B2433"     # dark navy tile
EDGE = "#2A3B58"   # subtle border
INK = "#F8FAFC"    # warm cream text
FONT = "'Courier New', ui-monospace, monospace"

# --- geometry --------------------------------------------------------------
H = 34             # chip height (secondary to the 48px skillicons tiles)
RX = 8             # corner radius (~matches skillicons rounding at this size)
FS = 17            # font-size
CW = FS * 0.6      # Courier is monospace: advance width is exactly 0.6em
LS = 1             # letter-spacing
SQ = 12            # accent pixel square
PAD_L = 11         # left padding before the accent square
GAP = 8            # accent square -> text
PAD_R = 13         # right padding after text
BASELINE = round(H / 2 + FS * 0.34)  # vertical-centered text baseline

# (slug, label, accent) -- accent nods at each tech's brand colour, no logos.
BADGES = [
    ("pandas",     "PANDAS",     "#E70488"),
    ("numpy",      "NUMPY",      "#4DABCF"),
    ("playwright", "PLAYWRIGHT", "#2EAD33"),
    ("sql",        "SQL",        "#38BDF8"),
    ("rest",       "REST",       "#34D399"),
    ("dapr",       "DAPR",       "#3B82F6"),
    ("serilog",    "SERILOG",    "#F59E0B"),
    ("zipkin",     "ZIPKIN",     "#FB923C"),
]


def build(label: str, accent: str) -> str:
    text_w = len(label) * CW + max(0, len(label) - 1) * LS
    tx = PAD_L + SQ + GAP
    w = int(round(tx + text_w + PAD_R))
    sq_y = (H - SQ) // 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" '
        f'viewBox="0 0 {w} {H}" role="img" aria-label="{label}">\n'
        f'  <rect x="0.5" y="0.5" width="{w - 1}" height="{H - 1}" rx="{RX}" '
        f'fill="{BG}" stroke="{EDGE}"/>\n'
        f'  <rect x="{PAD_L}" y="{sq_y}" width="{SQ}" height="{SQ}" '
        f'fill="{accent}" shape-rendering="crispEdges"/>\n'
        f'  <text x="{tx}" y="{BASELINE}" fill="{INK}" font-family="{FONT}" '
        f'font-size="{FS}" font-weight="700" letter-spacing="{LS}">{label}</text>\n'
        f'</svg>\n'
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, label, accent in BADGES:
        (OUT / f"{slug}.svg").write_text(build(label, accent), encoding="utf-8", newline="\n")
    print(f"wrote {len(BADGES)} badges to {OUT}")


if __name__ == "__main__":
    main()
