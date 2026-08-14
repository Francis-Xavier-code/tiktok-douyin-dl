#!/usr/bin/env python3
"""Self-hosted star history chart.

Fetches the current stargazers count from the GitHub API, appends it to
assets/star-history.json, and regenerates assets/star-history.svg so the
README can embed a chart that never depends on a flaky third-party service.

Run manually:
    python3 scripts/update-star-history.py

Or let .github/workflows/star-history.yml run it daily (cron) and commit
the result back to main.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.request

REPO = "Francis-Xavier-code/tiktok-douyin-dl"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(ROOT, "assets", "star-history.json")
SVG = os.path.join(ROOT, "assets", "star-history.svg")

MAX_POINTS = 365  # keep the chart JSON small (daily -> ~1 year)


def fetch_stars() -> int:
    url = f"https://api.github.com/repos/{REPO}"
    req = urllib.request.Request(url, headers={"User-Agent": "star-history-updater"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    stars = data.get("stargazers_count")
    if not isinstance(stars, int):
        raise RuntimeError(f"unexpected API response: {data}")
    return stars


def load_history() -> list[dict]:
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def write_svg(points: list[dict]) -> None:
    """Render a clean line chart. Single point -> just a dot + label."""
    width, height, pad_l, pad_r, pad_t, pad_b = 800, 240, 60, 24, 36, 48
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    if not points:
        with open(SVG, "w", encoding="utf-8") as fh:
            fh.write('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"></svg>' % (width, height))
        return

    stars = [p["stars"] for p in points]
    dates = [p["date"] for p in points]
    max_stars = max(stars)
    y_max = max(max_stars + 2, 10)  # headroom so the line never touches the top

    def x(i: int) -> float:
        if len(points) == 1:
            return pad_l + plot_w / 2
        return pad_l + plot_w * i / (len(points) - 1)

    def y(v: int) -> float:
        return pad_t + plot_h * (1 - v / y_max)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{pad_l}" y="24" font-size="16" font-weight="600" fill="#24292f">⭐ Star History · {REPO}</text>',
    ]

    # Y grid lines + labels
    for gy in range(0, y_max + 1, max(1, y_max // 4)):
        yy = y(gy)
        parts.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width - pad_r}" y2="{yy:.1f}" stroke="#eaeef2" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{yy + 4:.1f}" font-size="11" fill="#8c959f" text-anchor="end">{gy}</text>')

    # X labels (first / middle / last)
    for idx in sorted({0, len(points) // 2, len(points) - 1}):
        parts.append(
            f'<text x="{x(idx):.1f}" y="{height - pad_b + 20}" font-size="11" fill="#8c959f" text-anchor="middle">{dates[idx]}</text>'
        )

    # Polyline + dots
    if len(points) >= 2:
        poly = " ".join(f"{x(i):.1f},{y(p['stars']):.1f}" for i, p in enumerate(points))
        parts.append(f'<polyline points="{poly}" fill="none" stroke="#0969da" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, p in enumerate(points):
            parts.append(f'<circle cx="{x(i):.1f}" cy="{y(p["stars"]):.1f}" r="3" fill="#0969da"/>')

    # Latest point label
    last = points[-1]
    lx, ly = x(len(points) - 1), y(last["stars"])
    parts.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="#fd8c73"/>')
    parts.append(
        f'<text x="{lx:.1f}" y="{ly - 12:.1f}" font-size="13" font-weight="700" fill="#24292f" text-anchor="middle">'
        f'{last["stars"]} ★ · {last["date"]}</text>'
    )

    parts.append("</svg>")
    with open(SVG, "w", encoding="utf-8") as fh:
        fh.write("".join(parts))


def main() -> int:
    try:
        stars = fetch_stars()
    except Exception as exc:
        print(f"fetch failed: {exc}", file=sys.stderr)
        return 1

    today = datetime.date.today().isoformat()
    hist = load_history()
    if hist and hist[-1]["date"] == today:
        hist[-1] = {"date": today, "stars": stars}
    else:
        hist.append({"date": today, "stars": stars})
    hist = hist[-MAX_POINTS:]
    with open(HISTORY, "w", encoding="utf-8") as fh:
        json.dump(hist, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    write_svg(hist)
    print(f"ok: {stars} stars, {len(hist)} data point(s) -> {os.path.relpath(SVG, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
