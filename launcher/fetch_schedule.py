"""Derive schedule.json from the official 6.4210/6.4212 course page.

The course site builds its calendar in JavaScript, so we parse the JS data
structures (lectures[], events[][], extra_lecture_days) out of schedule.html
and replay the same day-by-day loop the site uses to number lectures, psets
and recitations.  Re-run this whenever the staff update the schedule.
"""

import datetime
import json
import pathlib
import re
import sys
import urllib.request

URL = "http://manipulation.csail.mit.edu/Fall2026/schedule.html"
HERE = pathlib.Path(__file__).resolve().parent

YEAR = 2026
FIRST_DAY = datetime.date(2026, 9, 9)    # Wed Sep 9  (first day of classes)
LAST_DAY = datetime.date(2026, 12, 10)   # Thu Dec 10 (last day of classes)
GRID_START = datetime.date(2026, 9, 7)   # grid must start on a Monday

TAG = re.compile(r"<[^>]+>")
HREF = re.compile(r'href="([^"]+)"')


def text(s):
    return TAG.sub("", s).replace("&nbsp;", " ").strip()


def chapter_of(reading_html):
    """Map a reading link like .../force.html -> chapter id 'force'."""
    ids = []
    for href in HREF.findall(reading_html or ""):
        if "manipulation.csail.mit.edu" in href and href.endswith(".html"):
            ids.append(href.rsplit("/", 1)[-1][: -len(".html")])
    return ids


def main():
    src = HERE / "schedule.html"
    if "--offline" in sys.argv and src.exists():
        html = src.read_text()
    else:
        html = urllib.request.urlopen(URL, timeout=30).read().decode()
        src.write_text(html)

    # ---- lectures ------------------------------------------------------
    lectures = []
    for block in re.findall(r"lectures\.push\(\{(.*?)\}\);", html, re.S):
        title = re.search(r"title:\s*'((?:[^']|\\')*)'", block)
        reading = re.search(r"reading:\s*'((?:[^']|\\')*)'", block)
        lectures.append({
            "title": text(title.group(1)) if title else "TBD",
            "reading": text(reading.group(1)) if reading else "",
            "chapters": chapter_of(reading.group(1)) if reading else [],
        })

    # ---- events --------------------------------------------------------
    events = {}
    pattern = re.compile(
        r"events\[(\d+)\]\[(\d+)\]\s*=\s*(?:\(events\[\d+\]\[\d+\]\s*\|\|\s*\[\]\)\.concat\()?\[(.*?)\]\)?;",
        re.S,
    )
    for month, day, body in pattern.findall(html):
        key = f"{int(month):02d}-{int(day):02d}"
        found = re.findall(
            r"\{\s*type:\s*'([^']+)',\s*description:\s*'((?:[^']|\\')*)'", body, re.S
        )
        events.setdefault(key, []).extend(
            {"type": t, "description": text(d)} for t, d in found
        )

    # Problem sets carry a trailing "// out M/D" comment giving the date they
    # are handed out; the events[][] key itself is the due date.
    out_dates = {}
    for mo, dy, omo, ody in re.findall(
            r"events\[(\d+)\]\[(\d+)\]\s*=\s*\[\{\s*type:\s*'assignment'"
            r".*?\}\];\s*//\s*out\s*(\d+)/(\d+)", html):
        due = datetime.date(YEAR, int(mo), int(dy))
        out_dates[due.isoformat()] = datetime.date(YEAR, int(omo), int(ody)).isoformat()

    extra = {}
    m = re.search(r"var extra_lecture_days = \{(.*?)\};", html, re.S)
    if m:
        for mo, dy in re.findall(r"(\d+):\s*\{\s*(\d+):\s*true", m.group(1)):
            extra[f"{int(mo):02d}-{int(dy):02d}"] = True

    handouts = re.search(r"(https://github\.com/[^\s'\"]*handouts)", html)

    # Number problem sets by due date so an "out" marker can name its pset
    # before the due date is reached in the replay below.
    pset_no, pset_due = {}, {}
    due_keys = sorted(
        (k for k, v in events.items()
         if any(e["type"] == "assignment" for e in v)),
        key=lambda k: (int(k.split("-")[0]), int(k.split("-")[1])),
    )
    for i, k in enumerate(due_keys, 1):
        pset_no[k] = i
        mo, dy = (int(x) for x in k.split("-"))
        pset_due[datetime.date(YEAR, mo, dy).isoformat()] = i
    out_marker = {}   # iso date handed out -> pset number
    for due_iso, out_iso in out_dates.items():
        n = pset_due.get(due_iso)
        if n:
            out_marker[out_iso] = n

    # ---- replay the site's calendar loop --------------------------------
    weeks, lec, rec = [], 0, 0
    d = GRID_START
    while d <= LAST_DAY:
        week = {"start": d.isoformat(), "days": []}
        for _ in range(5):
            key = f"{d.month:02d}-{d.day:02d}"
            todays = [dict(e) for e in events.get(key, [])]
            no_lecture = any(
                e["type"] in ("holiday", "quiz", "nolecture") for e in todays
            )
            for e in todays:
                if e["type"] == "assignment":
                    n = pset_no[key]
                    e["label"] = f"Problem Set {n}"
                    e["number"] = n
                    e["due"] = d.isoformat()
                    e["out"] = out_dates.get(d.isoformat())
                elif e["type"] == "recitation":
                    rec += 1
                    e["label"] = f"Recitation {rec}"

            if d.isoformat() in out_marker:
                todays.append({
                    "type": "assignment_out",
                    "label": f"Problem Set {out_marker[d.isoformat()]}",
                    "description": "handed out",
                    "number": out_marker[d.isoformat()],
                })

            day = {"date": d.isoformat(), "events": todays, "lecture": None}
            is_slot = d.weekday() in (0, 2) or key in extra
            if is_slot and not no_lecture and lec < len(lectures) \
                    and FIRST_DAY <= d <= LAST_DAY:
                day["lecture"] = dict(lectures[lec], number=lec + 1)
                lec += 1
            week["days"].append(day)
            d += datetime.timedelta(days=1)
        weeks.append(week)
        d += datetime.timedelta(days=2)

    # Flat, chronological list of everything with a hard date.
    deadlines = []
    for w in weeks:
        for day in w["days"]:
            for e in day["events"]:
                if e["type"] in ("assignment", "deadline", "quiz"):
                    deadlines.append({
                        "date": day["date"],
                        "type": e["type"],
                        "label": e.get("label", ""),
                        "description": e["description"],
                        "out": e.get("out"),
                    })
    deadlines.sort(key=lambda x: x["date"])

    out = {
        "source": URL,
        "deadlines": deadlines,
        "generated": datetime.date.today().isoformat(),
        "first_day": FIRST_DAY.isoformat(),
        "last_day": LAST_DAY.isoformat(),
        "handouts_repo": handouts.group(1) if handouts else None,
        "weeks": weeks,
    }
    (HERE / "schedule.json").write_text(json.dumps(out, indent=2))
    print(f"lectures parsed : {len(lectures)}")
    print(f"event days      : {len(events)}")
    print(f"psets           : {len(pset_no)}")
    print(f"deadlines       : {len(deadlines)}")
    print(f"weeks           : {len(weeks)}")
    print(f"handouts repo   : {out['handouts_repo']}")
    print(f"wrote {HERE / 'schedule.json'}")


if __name__ == "__main__":
    main()
