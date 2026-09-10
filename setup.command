#!/bin/bash
# One-time setup for the Robotic Manipulation (MIT 6.4210/6.4212) local notebook
# environment.  Double-click in Finder, or run it from a terminal.
#
# Safe to re-run: it skips work that is already done.

set -u

# The venv MUST live on a path with no spaces or parentheses -- see README.
VENV="${MANIPULATION_VENV:-$HOME/.venvs/manipulation}"
PYVER="3.13"
UPSTREAM="https://github.com/RussTedrake/manipulation.git"

cd "$(dirname "$0")" || exit 1
REPO_DIR="$(pwd)"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
err()  { printf '\033[31m%s\033[0m\n' "$*"; }
fail() { echo; err "$@"; echo; read -r -p "Press Return to close..."; exit 1; }
ask()  { read -r -p "$1 [y/N] " a; [[ "$a" =~ ^[Yy] ]]; }

bold "Robotic Manipulation — local setup"
echo

# ---------------------------------------------------------------- 1. platform
[ "$(uname -s)" = "Darwin" ] || fail "This installer is macOS-only.
On Windows use WSL2 with Ubuntu; on Linux follow Drake's own install docs."

OS_MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
ARCH="$(uname -m)"
echo "macOS $(sw_vers -productVersion) ($ARCH)"

if [ "$ARCH" != "arm64" ]; then
  fail "Drake publishes macOS wheels for Apple Silicon (arm64) only -- there is no
Intel macOS wheel. On an Intel Mac, use Ubuntu (or WSL2) instead."
fi
if [ "$OS_MAJOR" -lt 15 ]; then
  fail "Drake's macOS wheels require macOS 15 or newer (yours: $(sw_vers -productVersion)).
Update macOS, or use Ubuntu."
fi

# ---------------------------------------------------------------- 2. python
# Drake ships macOS wheels for 3.13 and 3.14, but the `triangle` dependency has
# no 3.14 wheel and cannot compile there -- so 3.13 is the only version that
# satisfies the whole dependency set.  See README.
PY=""
for cand in "$(brew --prefix 2>/dev/null)/opt/python@$PYVER/bin/python$PYVER" \
            "/opt/homebrew/opt/python@$PYVER/bin/python$PYVER" \
            "/usr/local/opt/python@$PYVER/bin/python$PYVER" \
            "$(command -v python$PYVER 2>/dev/null)"; do
  [ -n "$cand" ] && [ -x "$cand" ] && PY="$cand" && break
done

if [ -z "$PY" ]; then
  warn "Python $PYVER not found (it is required -- see README for why)."
  command -v brew >/dev/null || fail "Homebrew is not installed. Install it from https://brew.sh
then re-run this script."
  if ask "Install python@$PYVER with Homebrew now?"; then
    brew install "python@$PYVER" || fail "brew install python@$PYVER failed."
    PY="$(brew --prefix)/opt/python@$PYVER/bin/python$PYVER"
  else
    fail "Cannot continue without Python $PYVER."
  fi
fi
echo "python  $PY ($("$PY" --version 2>&1 | cut -d' ' -f2))"

# ---------------------------------------------------------------- 2b. graphviz
# Notebooks that draw system diagrams (RenderDiagram / plot_system_graphviz) call
# pydot, which shells out to the `dot` binary. That is a system package, not a
# pip one, so it has to be installed separately -- 18 notebooks fail without it
# with: FileNotFoundError: [Errno 2] "dot" not found in path.
if command -v dot >/dev/null 2>&1; then
  echo "dot     $(command -v dot)"
else
  warn "Graphviz ('dot') is not installed. Notebooks that render system diagrams"
  warn "will fail without it (18 of them, including several in Chapter 2)."
  if command -v brew >/dev/null 2>&1 && ask "Install graphviz with Homebrew now?"; then
    brew install graphviz || warn "brew install graphviz failed; diagram cells will error."
  else
    warn "Skipping. Install it later with: brew install graphviz"
  fi
fi

# ---------------------------------------------------------------- 3. venv
case "$VENV" in
  *[\ \(\)]*) fail "The virtualenv path must not contain spaces or parentheses:
  $VENV
Drake builds a shell command from its own install path without quoting it, so
such a path breaks model downloads. Set MANIPULATION_VENV to a clean path." ;;
esac

if [ -f "$VENV/bin/activate" ]; then
  echo "venv    $VENV (exists, reusing)"
else
  echo "venv    creating $VENV"
  mkdir -p "$(dirname "$VENV")"
  "$PY" -m venv "$VENV" || fail "Could not create the virtualenv at $VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate" || fail "Could not activate $VENV"

# ---------------------------------------------------------------- 4. packages
bold "Installing packages (this pulls Drake and takes a few minutes)..."
python -m pip install --upgrade pip -q
python -m pip install "manipulation[all]" jupyterlab || fail "pip install failed -- see the output above."

# ---------------------------------------------------------------- 5. notebooks
if [ -d "$REPO_DIR/manipulation/.git" ]; then
  bold "Updating the notebook repo..."
  git -C "$REPO_DIR/manipulation" pull --ff-only || warn "Could not fast-forward; leaving the checkout as-is."
else
  bold "Cloning the notebook repo..."
  git clone "$UPSTREAM" "$REPO_DIR/manipulation" || fail "git clone failed."
fi

# ---------------------------------------------------------------- 6. schedule
bold "Fetching the course schedule..."
python "$REPO_DIR/launcher/fetch_schedule.py" || \
  warn "Could not fetch the schedule (offline?). The launcher will still build once this succeeds."

# ---------------------------------------------------------------- 7. prefetch
echo
echo "Drake downloads robot/mesh assets (~1.3 GB) the first time a notebook needs"
echo "them. Prefetching now makes every notebook start instantly, including offline."
if ask "Prefetch model assets now?"; then
  python "$REPO_DIR/manipulation/setup/prefetch_remotes.py" || \
    warn "Prefetch failed; notebooks will download assets on demand instead."
fi

# ---------------------------------------------------------------- 8. verify
echo
bold "Verifying..."
python - <<'PY' || fail "Verification failed -- the install is not usable."
import platform
from importlib.metadata import version
import pydrake  # noqa: F401
import manipulation  # noqa: F401
from pydrake.all import RobotDiagramBuilder

b = RobotDiagramBuilder()
b.parser().AddModelsFromUrl(
    "package://drake_models/iiwa_description/sdf/iiwa14_no_collision.sdf")
b.Build()
print(f"  python       {platform.python_version()}")
print(f"  drake        {version('drake')}")
print(f"  manipulation {version('manipulation')}")
print("  model load   OK")
import shutil
print(f"  graphviz     {'OK' if shutil.which('dot') else 'MISSING (diagram cells will fail)'}")
PY

echo
bold "Setup complete."
echo "Launch it any time by double-clicking start.command in this folder."
echo
read -r -p "Press Return to close..."
