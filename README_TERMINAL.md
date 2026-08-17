# Profile Terminal GIF

The small retro shell window under the **USER FILE** icon. It types `whoami`,
reveals a short profile line-by-line, ends on `status: building...`, and loops
with a blinking cursor (~7s).

- **Script:** `scripts/generate_profile_terminal.py`
- **Output:** `assets/profile-terminal.gif` (320&nbsp;px wide, committed to the repo)
- **Runtime dependency:** Pillow only — no FFmpeg, no external service, no token.

## Why Pillow instead of gifos

This was inspired by [x0rzavi/github-readme-terminal](https://github.com/x0rzavi/github-readme-terminal)
(the `gifos` library). `gifos` requires **FFmpeg** as a system dependency. To keep
the profile fully self-contained — and consistent with the repo's other
generators, which produce assets with plain Python — the frames are rendered
directly with Pillow and written to a looping GIF. Same result, one pip
dependency, nothing to install system-wide.

## Install & regenerate

```bash
pip install -r requirements.txt        # just Pillow for this script
python scripts/generate_profile_terminal.py
```

The GIF is written to `assets/profile-terminal.gif`. It is static content, so
there is **no scheduled workflow** — regenerate manually and commit the result
when you change the text or colors.

Requirements: Python 3.9+ and Pillow. On non-Windows machines the script falls
back to a bundled monospace font (DejaVu / Liberation / Menlo); override with
`--font /path/to/mono.ttf` if needed.

## Edit the terminal content

Open `scripts/generate_profile_terminal.py`:

- **`COMMAND`** — the typed command (default `whoami`).
- **`OUTPUT`** — the revealed lines. Each row is a list of `(text, color)`
  segments; an empty list `[]` is a blank spacer line. Example:

  ```python
  [("> ", GREEN), ("Applied AI", CREAM)]
  ```

- **`PROMPT`** — the `jeeya7@github:~$` prompt segments.

Keep the longest line under ~32 characters so it fits the 320&nbsp;px width.

## Change the colors / theme

All colors are constants near the top of the script, chosen to match the
profile (navy background, warm cream text, lavender prompt, garden-green status,
soft-pink accent):

| Constant | Role | Default |
| --- | --- | --- |
| `BG` | terminal background | `#0d1117` |
| `EDGE` | window border | `#2a3b58` |
| `CREAM` | body text | `#ede4d3` |
| `LAV` | prompt / labels | `#b7a8e0` |
| `GREEN` | prompt symbol, bullets, status | `#8fce7f` |
| `PINK` | name + cursor | `#f2a7ce` |

Edit those values (or the `FS`, `LINE_H`, `W` geometry constants) and rerun the
script. Timing lives in `build_frames()` — per-frame durations are in
milliseconds and the loop is infinite (`loop=0`).
