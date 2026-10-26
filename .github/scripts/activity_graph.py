"""Render the last 31 days of GitHub contributions as an SVG line graph.

Usage: GITHUB_TOKEN=... python activity_graph.py <username> <output.svg>
"""

import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from html import escape

DAYS = 31
WIDTH, HEIGHT = 1200, 420
PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 80, 40, 70, 70

BG = "#0d1117"
LINE = "#58a6ff"
POINT = "#ffffff"
TEXT = "#58a6ff"
GRID = "#30363d"
AXIS_TEXT = "#8b949e"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_counts(login, token):
    today = date.today()
    start = today - timedelta(days=DAYS - 1)
    body = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{today.isoformat()}T23:59:59Z",
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])

    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    by_date = {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}
    days = [start + timedelta(days=i) for i in range(DAYS)]
    return [(d, by_date.get(d.isoformat(), 0)) for d in days]


def nice_max(value):
    if value <= 5:
        return 5
    step = 10 ** (len(str(int(value))) - 1)
    return ((value + step - 1) // step) * step


def render(login, counts):
    plot_w = WIDTH - PAD_LEFT - PAD_RIGHT
    plot_h = HEIGHT - PAD_TOP - PAD_BOTTOM
    y_max = nice_max(max(c for _, c in counts))

    def x(i):
        return PAD_LEFT + plot_w * i / (len(counts) - 1)

    def y(c):
        return PAD_TOP + plot_h * (1 - c / y_max)

    points = [(x(i), y(c)) for i, (_, c) in enumerate(counts)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    area = f"{PAD_LEFT},{PAD_TOP + plot_h} {line} {PAD_LEFT + plot_w},{PAD_TOP + plot_h}"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
        f'<title>{escape(login)}\'s contributions over the last {DAYS} days</title>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="6" fill="{BG}"/>',
        f'<text x="{WIDTH / 2}" y="40" text-anchor="middle" font-size="22" font-weight="600" '
        f'fill="{TEXT}">{escape(login)}\'s Contributions</text>',
    ]

    for k in range(5):
        val = y_max * k / 4
        gy = y(val)
        out.append(f'<line x1="{PAD_LEFT}" y1="{gy:.1f}" x2="{PAD_LEFT + plot_w}" y2="{gy:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{PAD_LEFT - 12}" y="{gy + 4:.1f}" text-anchor="end" font-size="12" '
                   f'fill="{AXIS_TEXT}">{val:g}</text>')

    for i, (d, _) in enumerate(counts):
        out.append(f'<text x="{x(i):.1f}" y="{PAD_TOP + plot_h + 22}" text-anchor="middle" '
                   f'font-size="12" fill="{AXIS_TEXT}">{d.day}</text>')

    out += [
        f'<text x="{WIDTH / 2}" y="{HEIGHT - 16}" text-anchor="middle" font-size="14" fill="{TEXT}">Days</text>',
        f'<text x="24" y="{PAD_TOP + plot_h / 2}" text-anchor="middle" font-size="14" fill="{TEXT}" '
        f'transform="rotate(-90 24 {PAD_TOP + plot_h / 2})">Contributions</text>',
        f'<polygon points="{area}" fill="{LINE}" fill-opacity="0.25"/>',
        f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>',
    ]
    for (px, py), (d, c) in zip(points, counts):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{POINT}">'
                   f'<title>{d.isoformat()}: {c}</title></circle>')

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    login, output = sys.argv[1], sys.argv[2]
    counts = fetch_counts(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w") as f:
        f.write(render(login, counts))


if __name__ == "__main__":
    main()
