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

    extra = {}
    m = re.search(r"var extra_lecture_days = \{(.*?)\};", html, re.S)
    if m:
        for mo, dy in re.findall(r"(\d+):\s*\{\s*(\d+):\s*true", m.group(1)):
            extra[f"{int(mo):02d}-{int(dy):02d}"] = True

    handouts = re.search(r"(https://github\.com/[^\s'\"]*handouts)", html)

    # ---- replay the site's calendar loop --------------------------------
    weeks, lec, pset, rec = [], 0, 0, 0
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
                    pset += 1
                    e["label"] = f"Problem Set {pset}"
                elif e["type"] == "recitation":
                    rec += 1
                    e["label"] = f"Recitation {rec}"

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

    out = {
        "source": URL,
        "generated": datetime.date.today().isoformat(),
        "first_day": FIRST_DAY.isoformat(),
        "last_day": LAST_DAY.isoformat(),
        "handouts_repo": handouts.group(1) if handouts else None,
        "weeks": weeks,
    }
    (HERE / "schedule.json").write_text(json.dumps(out, indent=2))
    print(f"lectures parsed : {len(lectures)}")
    print(f"event days      : {len(events)}")
    print(f"psets           : {pset}")
    print(f"weeks           : {len(weeks)}")
    print(f"handouts repo   : {out['handouts_repo']}")
    print(f"wrote {HERE / 'schedule.json'}")


if __name__ == "__main__":
    main()
