# Robotic Manipulation — local notebook launcher

A one-command local setup for the notebooks that accompany **MIT 6.4210 / 6.4212
(Robotic Manipulation)**, plus a quick-select page for opening any notebook by
week or by chapter.

Everything runs locally — no Deepnote, no Colab, no per-notebook asset downloads
once you've prefetched.

## What you get

**`setup.command`** — run once. Checks your Mac is supported, installs the right
Python, builds a virtualenv, installs `manipulation[all]` + JupyterLab, clones
the upstream notebook repo, fetches the course schedule, and optionally
prefetches ~1.3 GB of robot/mesh assets so notebooks start instantly (and work
offline). Safe to re-run; it skips what's already done.

**`start.command`** — run whenever you want to work. Starts JupyterLab on a free
port with a fresh token, rebuilds the launcher page against that server, and
opens it. Ctrl-C shuts everything down.

**The launcher page** — three views over the semester and all ~95 notebooks:

- **By week** — the full semester, with **the current week highlighted** and
  scrolled to automatically. Each day shows its lecture, readings, problem sets,
  quizzes, project deadlines and recitations, with one-click chips that open the
  relevant notebooks straight into Jupyter.
- **By chapter** — every chapter in textbook order, notebooks and exercises
  separated.
- **Due dates** — every problem set, quiz and project deadline in one
  chronological list, each with the date it was handed out and a live
  countdown ("in 6 days"). The next thing due is highlighted and also shown in
  the page header; past items are dimmed.

Problem sets appear twice in the week view — on the Wednesday they're handed
out and on the Thursday they're due — each cross-referencing the other date.

Plus a filter box across all three views.

## Requirements

- **Apple Silicon Mac (arm64), macOS 15 or newer.** Drake publishes macOS wheels
  for `arm64` + `macosx_15_0` only — there is no Intel macOS wheel. On an Intel
  Mac or on Windows, use Ubuntu / WSL2 and follow Drake's own install docs.
- **Homebrew** ([brew.sh](https://brew.sh)) — used to install Python 3.13 and Graphviz.
- **Graphviz** — installed by `setup.command`. Notebooks that draw system
  diagrams shell out to the `dot` binary; it is a system package, not a pip one,
  so it is easy to miss. 18 notebooks fail without it.
- ~4 GB of disk (packages + prefetched models).

## Quickstart

```bash
git clone <this-repo> manipulation-launcher
cd manipulation-launcher
./setup.command      # once, ~10 min
./start.command      # every time
```

Or just double-click `setup.command` then `start.command` in Finder.

### Prefer an editor over JupyterLab?

You don't have to use Jupyter at all. Cursor and VS Code open `.ipynb` files
natively — point the kernel picker at `~/.venvs/manipulation/bin/python` and run
cells there. The launcher page has an **Open in: Jupyter | Cursor** toggle: in
Cursor mode every notebook chip becomes a `cursor://` link that opens the file
straight in the editor (and works whether or not a Jupyter server is running).
Your choice is remembered per browser.

## Two things that will bite you if you deviate

These are the non-obvious constraints this repo exists to encode. Both are
upstream quirks, not choices.

### 1. Python 3.13 specifically — not 3.14, not 3.12

| Package | macOS arm64 wheels |
|---|---|
| `drake` | 3.13, 3.14 |
| `triangle` (pulled in by `manipulation[all]`) | ≤ 3.13 |

Homebrew's default `python3` is 3.14, where `triangle` has no wheel and fails to
compile (`fatal error: 'longintrepr.h' file not found` — that header went private
after CPython 3.11). Drake publishes no macOS 3.12 wheel. The intersection is
3.13, so `setup.command` installs and uses `python@3.13` explicitly, regardless
of your default `python3`.

### 2. The virtualenv must live on a path with no spaces or parentheses

Drake's model downloader builds a shell command from its own install path
**without quoting it**. If the venv sits under, say,
`~/Classes/6.4210 (Robotic Manipulation)/venv`, every model download dies with:

```
sh: -c: line 0: syntax error near unexpected token `('
```

So the venv defaults to `~/.venvs/manipulation`, deliberately outside this repo.
Only the *venv* path matters — this repo, and your notebooks, can live anywhere,
including a folder with spaces. Override with:

```bash
MANIPULATION_VENV=/some/clean/path ./setup.command
```

## Keeping it current

The schedule is parsed from the course website; the notebooks come from the
upstream repo. Refresh both by re-running `./setup.command`, or individually:

```bash
source ~/.venvs/manipulation/bin/activate
python launcher/fetch_schedule.py     # re-read the published schedule
git -C manipulation pull              # update notebooks
```

If staff post new notebooks that need new assets, re-run the prefetch:

```bash
python manipulation/setup/prefetch_remotes.py
```

## How the schedule is built

The course site renders its calendar in JavaScript rather than static HTML, so
`launcher/fetch_schedule.py` parses the `lectures[]` / `events[][]` data out of
the page and replays the site's own day-by-day loop to number lectures, problem
sets and recitations. That reproduces the irregularities faithfully — a Tuesday
that runs on a Monday schedule, quizzes that replace a lecture, holidays.

Output lands in `launcher/schedule.json`. `launcher/build_index.py` combines it
with a scan of the cloned notebooks and `launcher/template.html` to produce
`launcher/index.html`.

The page is regenerated on every launch because Jupyter's token changes each
run. The "current week" is computed in the browser at page load, so the
highlight stays correct without rebuilding.

## Layout

```
setup.command            one-time installer
start.command            daily launcher
launcher/
  fetch_schedule.py      course site  -> schedule.json
  build_index.py         schedule.json + notebooks -> index.html
  template.html          page shell (styles, tabs, current-week logic)
manipulation/            upstream notebooks (cloned by setup, gitignored)
```

## Troubleshooting

**"no virtualenv at …"** — run `setup.command` first.

**Model downloads fail with a `sh: syntax error`** — your venv is on a path with
spaces or parentheses. See constraint 2 above.

**Jupyter won't start** — check `launcher/jupyter.log`.

**Launcher page shows greyed-out notebook chips** — it was generated while no
Jupyter server was running. Re-run `start.command`.

**A notebook stalls on first run** — it's downloading models. Run the prefetch.

**`FileNotFoundError: [Errno 2] "dot" not found in path`** — Graphviz is missing:
`brew install graphviz`. Affects any cell calling `RenderDiagram(...)`.

**`gymnasium_robotics.ipynb` fails with a checksum mismatch** — an upstream
issue, not a local one: Drake pins a SHA256 for the Gymnasium-Robotics tarball
that GitHub's generated archive no longer matches. Skip that notebook.

## Credits

The notebooks, textbook and course are by **Russ Tedrake** and the Robot
Locomotion Group at MIT CSAIL:

- Textbook — <https://manipulation.mit.edu/>
- Notebooks — <https://github.com/RussTedrake/manipulation>
- Course — <http://manipulation.csail.mit.edu/>

This repo only packages a local setup and launcher around them; it vendors no
course content. Problem sets are distributed separately by the course staff.

Licensed under the MIT License — see [LICENSE](LICENSE).
