#!/usr/bin/env python3
"""Generate a pixel-art "contribution garden" SVG from real GitHub activity.

The garden mirrors GitHub's weekly contribution grid (columns = weeks, rows =
Sunday..Saturday) but renders each day as a pixel-art plant whose growth stage
reflects that day's contribution intensity:

    level 0  empty soil        level 3  small flower
    level 1  tiny sprout        level 4  full flower
    level 2  leafy sprout       level 5  rare golden flower

Contribution intensity comes straight from GitHub's own ``contributionLevel``
quartiles (see ``normalize_contribution_levels``) so the distribution stays
sensible without inventing raw-count thresholds.

Usage
-----
    # real data (needs a token that can read public contributions)
    export GITHUB_TOKEN="ghp_..."
    python scripts/generate_contribution_garden.py

    # representative fake data, no network / no token required
    python scripts/generate_contribution_garden.py --mock

    # (re)write the standalone reference sprites in assets/garden/
    python scripts/generate_contribution_garden.py --emit-sprites

The output is written to ``assets/contribution-garden.svg`` by default.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_USER = "Jeeya7"
GRAPHQL_URL = "https://api.github.com/graphql"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "assets" / "contribution-garden.svg"
SPRITE_DIR = REPO_ROOT / "assets" / "garden"

# Layout (all values are integer SVG units -> crisp pixel edges).
TILE = 12          # width/height of one day tile
GAP = 4            # space between tiles
PITCH = TILE + GAP  # distance from one tile to the next
ROWS = 7           # Sunday .. Saturday

PAD = 14           # panel inner padding
DAY_LABEL_W = 24   # gutter reserved for MON/WED/FRI labels
HEADER_H = 36      # space above the month labels (title + legend live here)
MONTH_H = 14       # space for month labels, between header and grid
FOOTER_H = 24      # space below the grid for the caption

FONT = "'Courier New', ui-monospace, monospace"

# ---------------------------------------------------------------------------
# Palette  (cohesive with the profile's navy / cream pixel-farm theme)
# ---------------------------------------------------------------------------

C_PANEL = "#0F1A2E"       # dark navy card background
C_PANEL_EDGE = "#2A3B58"  # subtle card border
C_INK = "#F8FAFC"         # warm cream text
C_INK_SHADOW = "#0F172A"  # navy text outline
C_MUTED = "#64748B"       # slate muted labels

C_SOIL = "#33241A"        # tilled earth
C_SOIL_TOP = "#4E3A26"    # sunlit soil edge
C_SOIL_DARK = "#241810"   # soil speckle

C_STEM = "#4F7E3B"        # plant stem
C_STEM_HI = "#6FB050"     # stem highlight
C_LEAF = "#6FB050"        # leaf
C_LEAF_HI = "#8ACB6A"     # leaf highlight

C_PINK = "#EA8FC0"        # flower petal
C_PINK_HI = "#F6B3D6"     # petal highlight
C_PINK_CTR = "#C86AA0"    # petal shadow / center
C_PURPLE = "#B389D8"      # lavender accent
C_GOLD = "#F3C64B"        # rare bloom
C_GOLD_HI = "#FFDE7A"     # rare highlight
C_GOLD_CTR = "#E0A828"    # rare center
C_CREAM = "#F8FAFC"       # sparkle

C_STEEL = "#8FA6BE"       # watering can body
C_STEEL_HI = "#C7D4E2"    # watering can highlight

# ---------------------------------------------------------------------------
# Sprite pixel data  (single source of truth for both the inline <defs>
# used in the garden and the standalone files in assets/garden/)
#
# Each rect is (x, y, w, h, color) in a 12x12 local grid, y pointing down.
# Soil occupies the bottom band; plants rise from the soil line at y == 8.
# ---------------------------------------------------------------------------

SOIL = [
    (0, 8, 12, 4, C_SOIL),      # earth body
    (0, 8, 12, 1, C_SOIL_TOP),  # sunlit top edge
    (2, 10, 1, 1, C_SOIL_DARK),
    (7, 9, 1, 1, C_SOIL_DARK),
    (10, 11, 1, 1, C_SOIL_DARK),
]

PLANTS = {
    # level 1 -- tiny sprout
    1: [
        (5, 5, 2, 3, C_STEM),
        (3, 5, 2, 2, C_LEAF),
        (7, 5, 2, 2, C_LEAF),
        (5, 4, 2, 1, C_LEAF_HI),
    ],
    # level 2 -- leafy sprout
    2: [
        (5, 3, 2, 5, C_STEM),
        (5, 3, 1, 5, C_STEM_HI),
        (2, 5, 3, 2, C_LEAF),
        (7, 5, 3, 2, C_LEAF),
        (3, 3, 2, 2, C_LEAF_HI),
        (7, 3, 2, 2, C_LEAF_HI),
        (5, 2, 2, 1, C_LEAF_HI),
    ],
    # level 3 -- small flower (pink bud)
    3: [
        (5, 4, 2, 4, C_STEM),
        (2, 5, 3, 2, C_LEAF),
        (7, 5, 3, 2, C_LEAF),
        (4, 2, 4, 3, C_PINK),
        (4, 2, 4, 1, C_PINK_HI),
        (5, 3, 2, 1, C_PINK_CTR),
    ],
    # level 4 -- full flower (pink + lavender, gold center)
    4: [
        (5, 6, 2, 2, C_STEM),
        (2, 6, 3, 2, C_LEAF),
        (7, 6, 3, 2, C_LEAF),
        (3, 2, 6, 4, C_PINK),
        (4, 1, 4, 1, C_PINK_HI),
        (3, 2, 6, 1, C_PINK_HI),
        (2, 3, 1, 2, C_PURPLE),
        (9, 3, 1, 2, C_PURPLE),
        (5, 3, 2, 2, C_GOLD),
    ],
    # level 5 -- rare golden bloom (+ sparkles)
    5: [
        (5, 6, 2, 2, C_STEM),
        (2, 6, 3, 2, C_LEAF),
        (7, 6, 3, 2, C_LEAF),
        (2, 2, 8, 4, C_GOLD),
        (4, 0, 4, 2, C_GOLD),
        (2, 2, 8, 1, C_GOLD_HI),
        (5, 3, 2, 2, C_GOLD_CTR),
        (10, 1, 1, 1, C_CREAM),
        (0, 4, 1, 1, C_CREAM),
    ],
}

SPRITE_IDS = {
    0: "soil",
    1: "sprout-1",
    2: "sprout-2",
    3: "flower-small",
    4: "flower-full",
    5: "flower-rare",
}

# A small watering can -- the single decorative object (drawn ~16x11).
WATERING_CAN = [
    (4, 4, 7, 5, C_STEEL),
    (4, 4, 7, 1, C_STEEL_HI),
    (5, 3, 4, 1, C_STEEL),
    (11, 2, 2, 2, C_STEEL),      # handle
    (0, 5, 4, 2, C_STEEL),       # spout
    (0, 4, 1, 1, C_STEEL_HI),
    (0, 7, 1, 1, C_CREAM),       # water drop
    (0, 9, 1, 1, C_CREAM),
]


# ---------------------------------------------------------------------------
# Data acquisition
# ---------------------------------------------------------------------------

def _fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    """Print a readable error and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def _contribution_window() -> tuple[str, str]:
    """Return an ISO8601 (from, to) window of ~52 aligned weeks.

    The window is snapped forward to a Sunday so every returned week is
    complete, and kept strictly under one year (GitHub rejects wider ranges).
    """
    today = datetime.now(timezone.utc)
    start = today - timedelta(days=364)
    # move forward to the next Sunday (weekday(): Mon=0 .. Sun=6)
    start += timedelta(days=(6 - start.weekday()) % 7)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), today.isoformat()


def get_contribution_data(login: str, token: str) -> dict:
    """Fetch the contribution calendar for ``login`` via the GraphQL API.

    Returns a dict: ``{"total": int, "weeks": [[day, ...], ...]}`` where each
    day is ``{"date", "count", "level", "weekday"}`` and ``level`` is one of
    GitHub's contributionLevel enum values.
    """
    try:
        import requests  # lazy import so --mock works without the dependency
    except ImportError:  # pragma: no cover
        _fail("the 'requests' package is required for live data (pip install requests)")

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
                weekday
              }
            }
          }
        }
      }
    }
    """
    frm, to = _contribution_window()
    variables = {"login": login, "from": frm, "to": to}

    try:
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": f"{login}-contribution-garden",
            },
            timeout=30,
        )
    except Exception as exc:  # network layer
        _fail(f"GitHub API request failed: {exc}")

    if resp.status_code == 401:
        _fail("GitHub rejected the token (401). Check GITHUB_TOKEN is valid.")
    if resp.status_code != 200:
        _fail(f"GitHub API returned HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        payload = resp.json()
    except ValueError:
        _fail("GitHub API returned a non-JSON response")

    if "errors" in payload:
        messages = "; ".join(e.get("message", "?") for e in payload["errors"])
        _fail(f"GraphQL error(s): {messages}")

    try:
        user = payload["data"]["user"]
    except (KeyError, TypeError):
        _fail("unexpected API response structure (no data.user)")

    if user is None:
        _fail(f"GitHub user '{login}' was not found")

    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [
            {
                "date": d["date"],
                "count": d["contributionCount"],
                "level": d["contributionLevel"],
                "weekday": d["weekday"],
            }
            for d in week["contributionDays"]
        ]
        for week in calendar["weeks"]
    ]
    if not weeks:
        _fail("API returned an empty contribution calendar")

    return {"total": calendar["totalContributions"], "weeks": weeks}


def build_mock_data(seed: int = 7) -> dict:
    """Build a representative 53-week calendar exercising every level.

    No network or token required -- used for visual iteration via --mock.
    """
    rng = random.Random(seed)
    levels = [
        "NONE", "NONE", "NONE",
        "FIRST_QUARTILE", "FIRST_QUARTILE",
        "SECOND_QUARTILE", "SECOND_QUARTILE",
        "THIRD_QUARTILE",
        "FOURTH_QUARTILE",
    ]
    count_for = {
        "NONE": 0, "FIRST_QUARTILE": 2, "SECOND_QUARTILE": 5,
        "THIRD_QUARTILE": 9, "FOURTH_QUARTILE": 16,
    }

    today = date.today()
    # snap back to the most recent Sunday, then rewind 52 weeks
    start = today - timedelta(days=(today.weekday() + 1) % 7) - timedelta(weeks=52)

    weeks, total = [], 0
    for w in range(53):
        days = []
        for d in range(7):
            day_date = start + timedelta(weeks=w, days=d)
            if day_date > today:
                continue  # no future days, mirrors the real API
            level = rng.choice(levels)
            # spread the top tier so only a genuine minority hits the rare
            # (~90th percentile) cutoff, mirroring real activity distributions
            spread = rng.randint(0, 22) if level == "FOURTH_QUARTILE" else rng.randint(0, 1)
            count = count_for[level] + spread
            total += count
            days.append({
                "date": day_date.isoformat(),
                "count": count,
                "level": level,
                "weekday": d,
            })
        if days:
            weeks.append(days)
    return {"total": total, "weeks": weeks}


# ---------------------------------------------------------------------------
# Level normalization
# ---------------------------------------------------------------------------

_QUARTILE_TO_LEVEL = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def normalize_contribution_levels(weeks: list) -> None:
    """Assign a final garden level (0-5) to every day, in place as ``lvl``.

    Levels 0-4 come directly from GitHub's contributionLevel quartiles. The
    rare level 5 is reserved for the busiest days: FOURTH_QUARTILE days whose
    raw count reaches the ~95th percentile of all active days (roughly the top
    5% of days you contributed on). Using a percentile rather than a fixed
    count keeps "rare" genuinely rare regardless of how active the account is.
    """
    active_counts = sorted(
        d["count"] for week in weeks for d in week if d["count"] > 0
    )
    rare_threshold = None
    if active_counts:
        idx = int(len(active_counts) * 0.95)
        idx = min(idx, len(active_counts) - 1)
        rare_threshold = active_counts[idx]

    for week in weeks:
        for day in week:
            level = _QUARTILE_TO_LEVEL.get(day["level"], 0)
            if (
                level == 4
                and rare_threshold is not None
                and day["count"] >= rare_threshold
            ):
                level = 5
            day["lvl"] = level


def map_level_to_sprite(level: int) -> str:
    """Return the sprite id for a normalized level."""
    return SPRITE_IDS.get(level, "soil")


# ---------------------------------------------------------------------------
# SVG building blocks
# ---------------------------------------------------------------------------

def _rects_svg(rects: list, indent: str = "  ") -> str:
    return "\n".join(
        f'{indent}<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>'
        for (x, y, w, h, c) in rects
    )


def build_defs() -> str:
    """Build the reusable <defs> sprite groups (Option A: inline + <use>)."""
    parts = ['  <defs>']
    for level, sprite_id in SPRITE_IDS.items():
        rects = SOIL + PLANTS.get(level, [])
        parts.append(f'    <g id="{sprite_id}" shape-rendering="crispEdges">')
        parts.append(_rects_svg(rects, indent="      "))
        parts.append("    </g>")
    parts.append('    <g id="watering-can" shape-rendering="crispEdges">')
    parts.append(_rects_svg(WATERING_CAN, indent="      "))
    parts.append("    </g>")
    parts.append("  </defs>")
    return "\n".join(parts)


def generate_month_labels(weeks: list, grid_x: int, base_y: int) -> str:
    """Emit a month abbreviation the first time each new month appears."""
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    out, last_month, last_label_col = [], None, -3
    for col, week in enumerate(weeks):
        month = int(week[0]["date"][5:7])
        if month != last_month and (col - last_label_col) >= 3:
            x = grid_x + col * PITCH
            out.append(
                f'  <text x="{x}" y="{base_y}" fill="{C_MUTED}" '
                f'font-family="{FONT}" font-size="9" letter-spacing="1">'
                f'{names[month - 1].upper()}</text>'
            )
            last_label_col = col
        last_month = month
    return "\n".join(out)


def generate_day_labels(grid_x: int, grid_y: int) -> str:
    """Emit MON / WED / FRI labels only (rows 1, 3, 5)."""
    labels = {1: "MON", 3: "WED", 5: "FRI"}
    out = []
    for row, text in labels.items():
        y = grid_y + row * PITCH + TILE - 2
        x = grid_x - 6
        out.append(
            f'  <text x="{x}" y="{y}" text-anchor="end" fill="{C_MUTED}" '
            f'font-family="{FONT}" font-size="8" letter-spacing="1">{text}</text>'
        )
    return "\n".join(out)


def generate_svg_grid(weeks: list, grid_x: int, grid_y: int, today_iso: str):
    """Emit all day sprites plus the subtle current-day indicator.

    Returns ``(grid_markup, indicator_markup)``.
    """
    cells, indicator = [], ""
    for col, week in enumerate(weeks):
        for day in week:
            row = day["weekday"]
            x = grid_x + col * PITCH
            y = grid_y + row * PITCH
            cells.append(f'    <use href="#{map_level_to_sprite(day["lvl"])}" x="{x}" y="{y}"/>')
            if day["date"] == today_iso:
                indicator = (
                    f'  <rect x="{x - 1}" y="{y - 1}" width="{TILE + 2}" '
                    f'height="{TILE + 2}" fill="none" stroke="{C_INK}" '
                    f'stroke-width="1" opacity="0.75" shape-rendering="crispEdges"/>\n'
                    f'  <rect x="{x + TILE - 1}" y="{y - 3}" width="1" height="1" '
                    f'fill="{C_CREAM}"/>'
                )
    grid = '  <g shape-rendering="crispEdges">\n' + "\n".join(cells) + "\n  </g>"
    return grid, indicator


def generate_legend(right_x: int, y: int) -> str:
    """Compact 'less -> more' legend showing the growth stages."""
    out = [
        f'  <text x="{right_x - 6 * PITCH - 30}" y="{y + 10}" text-anchor="end" '
        f'fill="{C_MUTED}" font-family="{FONT}" font-size="8">less</text>'
    ]
    x = right_x - 6 * PITCH - 22
    for level in range(6):
        out.append(f'  <use href="#{SPRITE_IDS[level]}" x="{x}" y="{y}"/>')
        x += PITCH
    out.append(
        f'  <text x="{x}" y="{y + 10}" fill="{C_MUTED}" '
        f'font-family="{FONT}" font-size="8">more</text>'
    )
    return "\n".join(out)


def generate_accessibility_metadata(total: int) -> str:
    return (
        f'  <title>Jeeya7 GitHub contribution garden</title>\n'
        f'  <desc>A pixel-art garden representing Jeeya7\'s GitHub contribution '
        f'activity over the last year ({total} contributions), where each day is '
        f'a plant that grows with that day\'s activity.</desc>'
    )


def _heading_text(x: int, y: int, text: str, size: int) -> str:
    """Cream text with a navy drop-shadow, matching the profile headings."""
    return (
        f'  <text x="{x + 1}" y="{y + 2}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="900" letter-spacing="2" fill="{C_INK_SHADOW}" opacity="0.6">{text}</text>\n'
        f'  <text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="900" letter-spacing="2" fill="{C_INK}">{text}</text>'
    )


def generate_svg(data: dict, today_iso: str) -> str:
    """Assemble the complete garden SVG string."""
    weeks = data["weeks"]
    normalize_contribution_levels(weeks)

    cols = len(weeks)
    grid_x = PAD + DAY_LABEL_W
    grid_y = HEADER_H + MONTH_H
    grid_w = cols * PITCH - GAP
    grid_h = ROWS * PITCH - GAP

    width = grid_x + grid_w + PAD
    height = grid_y + grid_h + FOOTER_H + PAD
    right_x = width - PAD

    grid_markup, indicator = generate_svg_grid(weeks, grid_x, grid_y, today_iso)

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Jeeya7 GitHub contribution garden">'
    )
    svg.append(generate_accessibility_metadata(data["total"]))
    svg.append(build_defs())

    # panel
    svg.append(
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        f'fill="{C_PANEL}" stroke="{C_PANEL_EDGE}" stroke-width="1"/>'
    )

    # header: title + legend
    svg.append(_heading_text(PAD + 2, HEADER_H - 12, "ACTIVITY LOG", 16))
    svg.append(generate_legend(right_x, 12))

    # labels
    svg.append(generate_month_labels(weeks, grid_x, grid_y - 5))
    svg.append(generate_day_labels(grid_x, grid_y))

    # garden
    svg.append(grid_markup)
    if indicator:
        svg.append(indicator)

    # footer: decorative watering can + caption
    svg.append(f'  <use href="#watering-can" x="{PAD + 2}" y="{height - FOOTER_H + 2}"/>')
    svg.append(
        f'  <text x="{width / 2:.0f}" y="{height - 9}" text-anchor="middle" '
        f'fill="{C_MUTED}" font-family="{FONT}" font-size="9" letter-spacing="2">'
        f'contribution garden</text>'
    )

    svg.append("</svg>")
    return "\n".join(svg) + "\n"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def emit_sprites(directory: Path) -> None:
    """Write standalone reference sprites to ``directory`` (for customization)."""
    directory.mkdir(parents=True, exist_ok=True)
    scale = 6  # render the 12x12 sprites at 72px for easy inspection
    for level, sprite_id in SPRITE_IDS.items():
        rects = SOIL + PLANTS.get(level, [])
        body = _rects_svg(rects, indent="  ")
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{12 * scale}" '
            f'height="{12 * scale}" viewBox="0 0 12 12" '
            f'shape-rendering="crispEdges" role="img" aria-label="{sprite_id}">\n'
            f'{body}\n</svg>\n'
        )
        (directory / f"{sprite_id}.svg").write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {len(SPRITE_IDS)} sprites to {directory}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mock", action="store_true",
                        help="use representative fake data (no token/network)")
    parser.add_argument("--emit-sprites", action="store_true",
                        help="(re)write standalone sprites in assets/garden/ and exit")
    parser.add_argument("--user", default=GITHUB_USER,
                        help=f"GitHub username to render (default: {GITHUB_USER})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="output SVG path")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.emit_sprites:
        emit_sprites(SPRITE_DIR)
        return 0

    if args.mock:
        data = build_mock_data()
        print("using mock contribution data")
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            _fail("GITHUB_TOKEN is not set. Export a token, or use --mock for a preview.")
        data = get_contribution_data(args.user, token)
        print(f"fetched {data['total']} contributions for {args.user}")

    # UTC to match the API's contribution dates (and the CI runner clock)
    today_iso = datetime.now(timezone.utc).date().isoformat()
    svg = generate_svg(data, today_iso)
    write_svg(args.output, svg)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
