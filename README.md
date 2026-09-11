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

**The launcher page** — five views over the semester and all ~95 notebooks:

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

- **Examples** — all 88 worked examples from the reading ("Example 2.2
  Simulating the passive iiwa"), numbered as the book numbers them and grouped
  by chapter, each with an **open notebook** chip for the local copy. This is
  the local replacement for the textbook's "Open in Colab" buttons. Colab
  titles every notebook in a chapter with the chapter name ("Robotic
  Manipulation - Let's get you a robot.ipynb" covers four different notebooks),
  so the example number is the reliable way to find the file. Chapter-view chips
  also list the examples that use each notebook ("Inspector · Ex 2.1, 2.5, 5.3").
- **Exercises** — all 60 exercises from the reading, numbered as the textbook
  numbers them (Exercise 1.1, 1.2, …), grouped by chapter and split into
  *notebook* exercises (with an **open notebook** chip) and *written / reading*
  exercises, each with a link to it in the online notes. Every lecture in the
  week view also gets a "Ch. N exercises" chip that jumps straight there.

  Examples and exercises are parsed from the textbook's own HTML, so they track
  upstream. Notebook links follow `book/notebooks.js` exactly: the notebook
  argument is positional, quoting varies, and `notebook_link('intro')` alone
  means `intro/intro.ipynb`. Two upstream quirks are handled: one chapter leaves its last exercise unclosed
  (the parser ends an exercise at the next one or the chapter end), and an
  exercise notebook that no exercise in the reading cites is still listed, under
  "Other exercise notebooks", rather than hidden.

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
natively. `setup.command` registers the venv as a user-level Jupyter kernel, so
pick **"Robotic Manipulation (Drake)"** in the kernel picker the first time you
open a notebook — the editor remembers it per file.

That registration matters: a `cursor://` link opens a *bare file* with no
workspace folder, so `.vscode/settings.json` never loads and the editor will
otherwise offer you the bare Homebrew Python, which has no Drake in it. If you
see *"Running cells requires the ipykernel package"*, you have the wrong
interpreter selected — switch kernels rather than installing ipykernel where it
suggests. The launcher page has an **Open in: Jupyter | Cursor** toggle: in
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

## Problem sets

`setup.command` also clones the course's public handouts repo
([tlpmit/6.4210-2-fall26-handouts](https://github.com/tlpmit/6.4210-2-fall26-handouts))
into `handouts/`, and the launcher links to each pset from both the week view
and the **Due dates** tab: an **open workspace** button, the assignment PDF, and
every `.py` / `.ipynb` file in that pset. Psets appear as staff release them;
`./setup.command` (or `git -C handouts pull`) picks up new ones.

The assignment PDF is served over http by the Jupyter server (whose root is the
course folder, so it can reach `handouts/` as well as the notebooks). A `file://`
link would be simpler but browsers block navigating to one from a page — the
click silently fails and takes the launcher page down with it.

Other pset chips open in Cursor, regardless of the
Jupyter/Cursor toggle — pset work is `.py` files you edit, not notebooks. Use
**open workspace** first: it opens the handouts repo root, which is what carries
`utils/` (imported by pset code) and the editor settings that select the right
interpreter.

**This tooling never modifies pset content** — it only clones and links. The
`handouts/` clone is gitignored here, so nothing of the course's is republished.

A note on environments: the handouts README suggests a `uv`-managed `.venv`
inside its own clone. Reusing this repo's venv works and is safer — a `.venv`
inside a course folder whose name has spaces or parentheses hits the very Drake
path bug that README itself warns about. Verified by running `ps1` against it.
Two things it asks for that this repo already handles: Graphviz, and keeping the
venv on a clean path. Do read its §2 if you want a private GitHub backup of your
work — and note its warning **not to fork** the public repo.

## Why Drake is pinned

`manipulation` requires only `drake>=1.45.0`, so a plain install grabs the
newest release — and **drake 1.57.0 (released 2026-09-10) breaks the notebooks**.
Anything that builds a diagram, `book/intro/intro.ipynb` included, dies with:

```
Failure at systems/framework/diagram_builder.cc:490 in ThrowIfInputAlreadyWired()
```

The same notebooks pass on **1.56.0**, which is what `setup.command` installs.
This is upstream timing, not a local misconfiguration: the notebook repo simply
hasn't caught up with a Drake released days later.

Once upstream catches up, take the pin off:

```bash
DRAKE_PIN=drake ./setup.command     # track the newest release again
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
