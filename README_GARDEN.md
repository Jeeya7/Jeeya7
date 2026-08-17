# Contribution Garden

A self-contained pixel-art replacement for the default GitHub contribution
graph. It keeps the familiar weekly grid (columns = weeks, rows = Sunday →
Saturday) but renders each day as a plant whose growth stage reflects that
day's real contribution intensity.

No backend, no hosted service, no database — a single Python script generates
one static SVG that GitHub Actions refreshes once a day.

```
level 0  empty soil      ·   level 3  small flower
level 1  tiny sprout     ·   level 4  full flower
level 2  leafy sprout    ·   level 5  rare golden flower
```

---

## Architecture

Everything lives in three places:

| Path | Role |
| --- | --- |
| `scripts/generate_contribution_garden.py` | Fetches data and writes the SVG. |
| `.github/workflows/contribution-garden.yml` | Runs the script daily and commits changes. |
| `assets/contribution-garden.svg` | The generated image the README embeds. |
| `assets/garden/*.svg` | Standalone reference copies of each plant sprite. |

The generator is a plain pipeline of small functions:

```
get_contribution_data()          # GraphQL call -> weeks of daily activity
        │  (or build_mock_data() for --mock)
        ▼
normalize_contribution_levels()  # quartiles -> final levels 0..5
        ▼
generate_svg()                   # layout + assembly, which calls:
    build_defs()                 #   reusable <g> sprite groups (<use>d below)
    generate_month_labels()      #   month text where the month changes
    generate_day_labels()        #   MON / WED / FRI
    generate_svg_grid()          #   one <use> per day + current-day marker
    generate_accessibility_metadata()
        ▼
write_svg()                      # assets/contribution-garden.svg
```

**Sprites are inlined.** The SVG defines each plant once inside `<defs>` and
places it with `<use href="#sprout-1" x=… y=…>`. This keeps the file small and
fully portable — the standalone files in `assets/garden/` are reference copies
for editing, not runtime dependencies.

**Pixel-art integrity.** All coordinates are integers, sprite groups carry
`shape-rendering="crispEdges"`, and colours come from a fixed palette that
matches the profile's navy / cream / soft-green / lavender-pink theme. No
gradients, no anti-aliasing, no fractional pixels.

---

## Local execution

Requires Python 3.9+ and, for live data, two small packages:

```bash
pip install requests python-dateutil
```

**Preview with fake data** (no token, no network — the fastest way to iterate
on the visuals):

```bash
python scripts/generate_contribution_garden.py --mock
```

Mock mode produces a representative 53-week grid that exercises every level, so
you can see all six plant stages at once.

**Generate from real activity:**

```bash
export GITHUB_TOKEN="your_token"      # PowerShell: $env:GITHUB_TOKEN="your_token"
python scripts/generate_contribution_garden.py
```

Either way the result is written to `assets/contribution-garden.svg`.

Other flags:

```bash
python scripts/generate_contribution_garden.py --user someone   # render a different account
python scripts/generate_contribution_garden.py --emit-sprites   # rewrite assets/garden/*.svg
python scripts/generate_contribution_garden.py --output path.svg
```

---

## GitHub token usage

The script reads its token **only** from the `GITHUB_TOKEN` environment
variable — nothing is ever hard-coded or committed.

- **In CI:** the workflow passes the automatically provided
  `${{ secrets.GITHUB_TOKEN }}`. That default token is enough to read *public*
  contribution data for any user, so no personal access token or repository
  secret is required for the standard setup.
- **Locally:** export any token that can read public contributions (a
  classic PAT with no scopes, or a fine-grained token with read access to your
  profile, both work).
- **Private contributions:** to include private activity, run with a personal
  access token that has the `read:user` scope for your own account, stored as a
  repository secret, and reference it in the workflow instead of the default
  token.

If the token is missing or rejected, the script exits with a clear error rather
than silently producing an empty garden.

---

## Contribution-level mapping

Levels come straight from GitHub's own `contributionLevel` quartiles, so the
distribution stays sensible without inventing raw-count thresholds:

| GitHub `contributionLevel` | Garden level | Sprite |
| --- | --- | --- |
| `NONE` | 0 | `soil` |
| `FIRST_QUARTILE` | 1 | `sprout-1` |
| `SECOND_QUARTILE` | 2 | `sprout-2` |
| `THIRD_QUARTILE` | 3 | `flower-small` |
| `FOURTH_QUARTILE` | 4 | `flower-full` |
| `FOURTH_QUARTILE` **and** in the top ~5% of active days | 5 | `flower-rare` |

Level 5 (the rare golden bloom) is deliberately scarce: a `FOURTH_QUARTILE` day
is only promoted to it when its raw count reaches the ~95th percentile of all
days that had any activity. Because this is a *percentile*, "rare" stays rare
whether you commit twice a week or fifty times a day. The rule lives in
`normalize_contribution_levels()`.

---

## Sprite customization

Each plant is defined once as a list of rectangles in
`scripts/generate_contribution_garden.py`:

```python
PLANTS = {
    1: [ (x, y, w, h, colour), ... ],   # tiny sprout
    2: [ ... ],                         # leafy sprout
    ...
}
```

Rectangles use a **12×12 local grid** with `y` pointing down; soil occupies the
bottom band and plants rise from the soil line at `y == 8`. To recolour the
garden, edit the palette constants near the top of the file (`C_LEAF`,
`C_PINK`, `C_GOLD`, …). To reshape a plant, edit its rectangle list.

After changing sprites, regenerate the reference files and a preview:

```bash
python scripts/generate_contribution_garden.py --emit-sprites
python scripts/generate_contribution_garden.py --mock
```

Layout constants (`TILE`, `GAP`, `ROWS`, paddings) sit just below the palette if
you want to resize the grid; the overall SVG dimensions are computed from them.

---

## Workflow behaviour

`.github/workflows/contribution-garden.yml`:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Installs only `requests` and `python-dateutil`.
4. Runs the generator with the default `GITHUB_TOKEN`.
5. Diffs `assets/contribution-garden.svg`; if nothing changed, it stops.
6. Otherwise commits as `chore: update contribution garden` and pushes.

It runs on `schedule` (`cron: "17 3 * * *"`, daily at 03:17 UTC) and via
`workflow_dispatch` so you can trigger it manually from the **Actions** tab. The
job uses `permissions: contents: write` and commits under the
`github-actions[bot]` identity. Because the commit step is guarded by a diff, an
unchanged garden never creates an empty commit.
