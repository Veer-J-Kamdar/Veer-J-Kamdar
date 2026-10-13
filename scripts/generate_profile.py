#!/usr/bin/env python3
"""Generate custom profile SVGs from GitHub's GraphQL API.

Required environment:
  GITHUB_TOKEN: token provided by GitHub Actions
  GH_LOGIN: GitHub username (defaults to Veer-J-Kamdar)

Outputs:
  contribution-heatmap.svg, stats.svg, streak.svg, languages.svg,
  section-about.svg, section-projects.svg, section-stack.svg,
  section-activity.svg, section-now.svg

No external statistics-card service is used.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape

LOGIN = os.environ.get("GH_LOGIN", "Veer-J-Kamdar")
TOKEN = os.environ.get("GITHUB_TOKEN")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG = "#0d1117"
INK = "#c9d1d9"
MUTED = "#8b949e"
GREEN = "#39ff88"
GRID = "#21262d"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionCount date weekday }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

def write(name, body):
    path = os.path.join(ROOT, name)
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != body:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        print("updated", name)
    else:
        print("unchanged", name)

def fetch():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is missing.")
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    variables = {
        "login": LOGIN,
        "from": start.isoformat() + "T00:00:00Z",
        "to": today.isoformat() + "T23:59:59Z",
    }
    payload = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": LOGIN + "-profile-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + json.dumps(result["errors"]))
    user = (result.get("data") or {}).get("user")
    if not user:
        raise RuntimeError("GitHub user not found: " + LOGIN)
    return user

def svg_open(width, height, extra_style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<style>text{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}'
        f'.ink{{fill:{INK}}}.muted{{fill:{MUTED}}}.green{{fill:{GREEN}}}'
        f'.line{{stroke:{GRID}}}{extra_style}</style>'
    )

def heading(label):
    label = escape(label.upper())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="28" viewBox="0 0 620 28">'
        f'<style>text{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}</style>'
        f'<text x="0" y="19" fill="{INK}" font-size="15" font-weight="600">{label}</text>'
        f'<line x1="{len(label)*9.2+16:.1f}" y1="14" x2="620" y2="14" stroke="{GRID}"/>'
        f'</svg>'
    )

def heatmap(weeks, total):
    cell, gap, left, top = 11, 3, 34, 30
    n = len(weeks)
    width = left + n * (cell + gap) + 10
    height = top + 7 * (cell + gap) + 38
    rects, months = [], []
    last_month = None
    for wi, week in enumerate(weeks):
        if week:
            month = week[0]["date"][5:7]
            if month != last_month:
                months.append(
                    f'<text x="{left+wi*(cell+gap)}" y="17" class="muted" font-size="10">'
                    f'{datetime.strptime(month, "%m").strftime("%b")}</text>'
                )
                last_month = month
        for day in week:
            row = int(day["weekday"])
            x = left + wi * (cell + gap)
            y = top + row * (cell + gap)
            count = int(day["contributionCount"])
            level = 0 if count == 0 else 1 if count < 3 else 2 if count < 6 else 3 if count < 10 else 4
            date = escape(day["date"])
            rects.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{PALETTE[level]}"><title>{date}: {count} contributions</title>'
                f'<animate attributeName="opacity" values="0.25;1;1" '
                f'keyTimes="0;0.55;1" dur="1.2s" begin="{min(wi*0.018, 1.8):.2f}s" fill="freeze"/>'
                f'</rect>'
            )
    labels = "".join(
        f'<text x="2" y="{top+r*(cell+gap)+9}" class="muted" font-size="9">{name}</text>'
        for r, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]
    )
    legend = "".join(
        f'<rect x="{width-112+i*15}" y="{height-16}" width="10" height="10" rx="2" fill="{color}"/>'
        for i, color in enumerate(PALETTE)
    )
    body = svg_open(width, height)
    body += "".join(months) + labels + "".join(rects)
    body += f'<text x="{left}" y="{height-5}" class="ink" font-size="12">{total:,} contributions in the last year</text>'
    body += legend + "</svg>"
    return body

def calc_streaks(days):
    best, run, run_start = (0, None, None), 0, None
    for day in days:
        if day["contributionCount"] > 0:
            if run == 0:
                run_start = day["date"]
            run += 1
            if run > best[0]:
                best = (run, run_start, day["date"])
        else:
            run, run_start = 0, None
    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    current = 0
    for day in reversed(tail):
        if day["contributionCount"] == 0:
            break
        current += 1
    return current, best

def stats_svg(total, active, weekly):
    w, h = 620, 118
    peak = max(weekly) if weekly and max(weekly) else 1
    left, right, top, bottom = 2, 618, 73, 108
    pts = []
    for i, val in enumerate(weekly):
        x = left + i * (right-left) / max(1, len(weekly)-1)
        y = bottom - (val/peak)*(bottom-top)
        pts.append((x, y))
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i,(x,y) in enumerate(pts))
    body = svg_open(w, h)
    body += f'<text x="2" y="48" class="ink" font-size="38" font-weight="700">{total:,}</text>'
    body += f'<text x="3" y="65" class="muted" font-size="11">CONTRIBUTIONS / LAST 365 DAYS</text>'
    body += f'<text x="618" y="28" text-anchor="end" class="green" font-size="21">{active}</text>'
    body += '<text x="618" y="44" text-anchor="end" class="muted" font-size="10">ACTIVE DAYS</text>'
    body += f'<path d="{path}" fill="none" stroke="{GREEN}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
    body += "</svg>"
    return body

def streak_svg(current, best):
    body = svg_open(620, 100)
    body += f'<line x1="310" y1="12" x2="310" y2="88" stroke="{GRID}"/>'
    body += f'<text x="2" y="43" class="green" font-size="32" font-weight="700">{current}</text>'
    body += '<text x="2" y="62" class="muted" font-size="11">CURRENT STREAK / DAYS</text>'
    body += f'<text x="330" y="43" class="ink" font-size="32" font-weight="700">{best[0]}</text>'
    body += '<text x="330" y="62" class="muted" font-size="11">LONGEST STREAK / DAYS</text>'
    body += "</svg>"
    return body

def languages_svg(repos):
    totals, repo_counts = {}, {}
    for repo in repos:
        edges = ((repo.get("languages") or {}).get("edges") or [])
        for edge in edges:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + int(edge["size"])
        if edges:
            name = edges[0]["node"]["name"]
            repo_counts[name] = repo_counts.get(name, 0) + 1
    top = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:6]
    width, height = 620, 35 + max(1, len(top))*24
    body = svg_open(width, height)
    total_bytes = sum(totals.values()) or 1
    max_bytes = max([v for _,v in top] or [1])
    for i,(name,val) in enumerate(top):
        y = 20 + i*24
        pct = val/total_bytes*100
        body += f'<text x="2" y="{y+9}" class="ink" font-size="11">{escape(name)}</text>'
        body += f'<rect x="125" y="{y}" width="365" height="9" rx="2" fill="{GRID}"/>'
        body += f'<rect x="125" y="{y}" width="{365*val/max_bytes:.1f}" height="9" rx="2" fill="{GREEN}"/>'
        body += f'<text x="610" y="{y+9}" text-anchor="end" class="muted" font-size="10">{pct:.1f}%</text>'
    body += "</svg>"
    return body

def main():
    user = fetch()
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    days = [d for week in weeks for d in week["contributionDays"]]
    total = int(calendar["totalContributions"])
    active = sum(1 for d in days if d["contributionCount"] > 0)
    weekly = [sum(d["contributionCount"] for d in week["contributionDays"]) for week in weeks]
    current, best = calc_streaks(days)
    repos = user["repositories"]["nodes"]

    write("contribution-heatmap.svg", heatmap([w["contributionDays"] for w in weeks], total))
    write("stats.svg", stats_svg(total, active, weekly))
    write("streak.svg", streak_svg(current, best))
    write("languages.svg", languages_svg(repos))

    for filename, label in [
        ("section-about.svg", "about"),
        ("section-projects.svg", "selected projects"),
        ("section-stack.svg", "technology stack"),
        ("section-activity.svg", "contribution activity"),
        ("section-now.svg", "currently exploring"),
    ]:
        write(filename, heading(label))

    print(f"Generated profile graphics for {LOGIN}: {total:,} contributions, {active} active days.")

if __name__ == "__main__":
    main()
