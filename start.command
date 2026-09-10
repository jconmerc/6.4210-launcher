#!/bin/bash
# Launch Jupyter Lab + the quick-select launcher page for Robotic Manipulation
# (MIT 6.4210/6.4212, Fall 2026).  Double-click in Finder, or run in a terminal.
#
# Run setup.command first (once). See README.md.
#
# NOTE: the virtualenv deliberately lives OUTSIDE this folder.  Drake shells out
# to a model downloader without quoting its own path, so a venv on a path with
# spaces or parentheses breaks. Keep the venv on a clean path.

VENV="${MANIPULATION_VENV:-$HOME/.venvs/manipulation}"

cd "$(dirname "$0")" || exit 1
COURSE_DIR="$(pwd)"

fail() { echo; echo "$@"; echo; read -r -p "Press Return to close..."; exit 1; }

[ -f "$VENV/bin/activate" ] || fail "ERROR: no virtualenv at $VENV
Run setup.command in this folder first."

# shellcheck disable=SC1091
source "$VENV/bin/activate"

[ -d "manipulation/book" ] || fail "ERROR: notebook repo missing at $COURSE_DIR/manipulation
Run setup.command in this folder first."

# Pick a free port and our own token, so the launcher's links are deterministic.
PORT="$(python -c '
import socket
def free(p):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p)); return True
    except OSError:
        return False
    finally:
        s.close()
for p in range(8888, 8900):      # prefer the familiar range
    if free(p): print(p); break
else:                            # fall back to whatever the OS gives us
    s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()
')"
TOKEN="$(python -c 'import secrets;print(secrets.token_hex(24))')"

cleanup() {
  echo
  echo "Shutting down Jupyter..."
  [ -n "$JPID" ] && kill "$JPID" 2>/dev/null
  wait "$JPID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

echo "Robotic Manipulation  ·  MIT 6.4210/6.4212  ·  Fall 2026"
echo "python $(python --version 2>&1 | cut -d' ' -f2)  |  drake $(python -c 'from importlib.metadata import version; print(version("drake"))' 2>/dev/null)  |  $(find manipulation/book -name '*.ipynb' -not -path '*/.ipynb_checkpoints/*' | wc -l | tr -d ' ') notebooks"
echo

cd manipulation/book || exit 1
jupyter lab --no-browser --port="$PORT" --IdentityProvider.token="$TOKEN" \
  > "$COURSE_DIR/launcher/jupyter.log" 2>&1 &
JPID=$!
cd "$COURSE_DIR" || exit 1

printf "Starting Jupyter on port %s" "$PORT"
for _ in $(seq 1 60); do
  if curl -s -o /dev/null "http://localhost:$PORT/api?token=$TOKEN"; then break; fi
  kill -0 "$JPID" 2>/dev/null || fail "ERROR: Jupyter exited on startup. Last lines of launcher/jupyter.log:
$(tail -15 "$COURSE_DIR/launcher/jupyter.log")"
  printf "."
  sleep 0.5
done
echo " ready."

# Rebuild the launcher page against this run's port/token.
if [ ! -f launcher/schedule.json ]; then
  echo "No schedule yet -- fetching it..."
  python launcher/fetch_schedule.py || echo "WARNING: schedule fetch failed (offline?)."
fi
if [ -f launcher/build_index.py ] && [ -f launcher/schedule.json ]; then
  python launcher/build_index.py --port="$PORT" --token="$TOKEN" || \
    echo "WARNING: could not rebuild launcher page; opening Jupyter directly."
fi

if [ -f launcher/index.html ]; then
  open "$COURSE_DIR/launcher/index.html"
  echo "Launcher page opened. Jupyter: http://localhost:$PORT/lab?token=$TOKEN"
else
  open "http://localhost:$PORT/lab?token=$TOKEN"
fi

echo
echo "Press Ctrl-C here to shut Jupyter down."
wait "$JPID"
