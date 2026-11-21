"""Commit skyline: my GitHub history drawn as a Chicago skyline on the lake.

One tower per month, from my first public commit to today. Tower height grows
with activity on a log scale; lit windows show how busy the month was; quiet
months stay as low dark buildings. The busiest month gets a spire and twin
antennas, a nod to the tallest tower on the skyline. The city reflects in
Lake Michigan below, and the windows twinkle.

Data lives in history.json: seeded from my public git history, then refreshed
nightly by a workflow from GitHub's contribution calendar.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import ASSETS, FONT, MODES, PALETTES, esc, gradient, svg_open, write  # noqa: E402

HERE = Path(__file__).resolve().parent
HISTORY = HERE / "history.json"
OUT = ASSETS / "skyline"
LOGIN = os.environ.get("PROFILE_LOGIN", "bhargavirengarajan21")


def load() -> dict:
    return json.loads(HISTORY.read_text(encoding="utf-8"))


def months_between(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def refresh(token: str) -> dict:
    """Pull contributions per month from GitHub's GraphQL contribution calendar."""

    def gql(query: str, variables: dict) -> dict:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query, "variables": variables}).encode(),
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
        if "errors" in body:
            raise RuntimeError(body["errors"])
        return body["data"]

    created = gql("query($l:String!){user(login:$l){createdAt}}", {"l": LOGIN})["user"]["createdAt"]
    start_year = int(created[:4])
    months: dict[str, dict] = {}
    q = (
        "query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){contributionsCollection(from:$f,to:$t)"
        "{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"
    )
    for year in range(start_year, date.today().year + 1):
        data = gql(q, {"l": LOGIN, "f": f"{year}-01-01T00:00:00Z", "t": f"{year}-12-31T23:59:59Z"})
        weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for w in weeks:
            for d in w["contributionDays"]:
                if d["contributionCount"]:
                    key = d["date"][:7]
                    months.setdefault(key, {"commits": 0})
                    months[key]["commits"] += d["contributionCount"]
    old = load() if HISTORY.exists() else {"months": {}}
    # keep the larger of seed and calendar for each month, never lose history
    for k, v in old.get("months", {}).items():
        if v["commits"] > months.get(k, {"commits": 0})["commits"]:
            months[k] = {"commits": v["commits"]}
    out = {
        "source": "GitHub contribution calendar, merged with public git history",
        "refreshed": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "months": dict(sorted(months.items())),
    }
    HISTORY.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def render(hist: dict, mode: str) -> str:
    p = PALETTES[mode]
    data = hist["months"]
    today = date.today().strftime("%Y-%m")
    keys = months_between(min(data), max(max(data), today))
    counts = [data.get(k, {}).get("commits", 0) for k in keys]
    peak = max(counts) or 1
    W, H = 960, 420
    ground = 292
    left, right = 34, W - 34
    n = len(keys)
    slot = (right - left) / n
    rng = random.Random(7)
    s = [svg_open(W, H, "Commit skyline: one Chicago tower per month of GitHub activity, reflected in the lake")]
    sky_top, sky_bottom = (p["bg"], p["bg2"]) if mode == "dark" else ("#ffe9f4", "#fff7fb")
    s.append(
        "<defs>"
        + gradient("g", p, vertical=True)
        + f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky_top}"/>'
        f'<stop offset="1" stop-color="{sky_bottom}"/></linearGradient>'
        + f'<linearGradient id="fadeout" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["water"]}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{p["water"]}" stop-opacity="1"/></linearGradient>'
        + """<style>
        .tw{animation:tw 3.2s ease-in-out infinite}
        @keyframes tw{0%,100%{opacity:1}50%{opacity:.25}}
        .bk{animation:bk 1.6s steps(1) infinite}
        @keyframes bk{0%{opacity:1}50%{opacity:.15}}
        .wv{animation:wv 6s ease-in-out infinite alternate}
        @keyframes wv{from{transform:translateX(-14px)}to{transform:translateX(14px)}}
        </style></defs>"""
    )
    s.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#sky)"/>')
    # moon or sun
    if mode == "dark":
        s.append(f'<circle cx="{W - 120}" cy="70" r="26" fill="{p["gold"]}" opacity=".9"/>')
        s.append(f'<circle cx="{W - 108}" cy="62" r="24" fill="{sky_top}"/>')
        for _ in range(40):
            x, y = rng.uniform(20, W - 20), rng.uniform(16, 150)
            s.append(
                f'<circle class="tw" style="animation-delay:{rng.uniform(0, 3):.2f}s" cx="{x:.0f}" cy="{y:.0f}" '
                f'r="{rng.choice([0.8, 1.1, 1.4])}" fill="{p["text"]}" opacity=".7"/>'
            )
    else:
        s.append(f'<circle cx="{W - 120}" cy="72" r="30" fill="{p["gold"]}" opacity=".55"/>')

    towers = []
    peak_i = counts.index(peak)
    for i, (k, c) in enumerate(zip(keys, counts)):
        h = 14 + (math.log1p(c) / math.log1p(peak)) * 196 if c else rng.uniform(8, 18)
        w = slot * rng.uniform(1.05, 1.5) if c else slot * rng.uniform(0.9, 1.2)
        x = left + i * slot + (slot - w) / 2
        towers.append((x, w, h, c, k))

    # a dim far-off skyline behind the towers, for depth
    backdrop = []
    bx = left - 10
    while bx < right:
        bw = rng.uniform(14, 34)
        bh = rng.uniform(24, 84)
        backdrop.append((bx, bw, bh))
        bx += bw * rng.uniform(0.7, 1.0)
    back_fill = p["grid"] if mode == "dark" else "#f1dcec"

    # quiet months first, busy months last, so busy towers sit in front
    order = sorted(range(len(towers)), key=lambda i: towers[i][3])

    def city(flip: bool) -> list[str]:
        out = []
        wr = random.Random(11)
        for bx, bw, bh in backdrop:
            out.append(
                f'<rect x="{bx:.1f}" y="{ground - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{back_fill}" opacity=".55"/>'
            )
        for i in order:
            x, w, h, c, k = towers[i]
            y = ground - h
            if mode == "dark":
                body = p["panel"] if c else p["window_off"]
            else:
                body = "#4a3470" if c else "#d9c4e4"
            fill = "url(#g)" if (c and i == peak_i) else body
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"/>')
            if c and h > 30:
                cols = max(1, int(w // 4))
                rows = int((h - 8) // 7)
                lit = min(1.0, 0.25 + c / peak)
                for r in range(rows):
                    for col in range(cols):
                        if wr.random() > lit:
                            continue
                        wx = x + 1.5 + col * (w - 3) / cols
                        wy = y + 5 + r * 7
                        color = wr.choice([p["gold"], p["pink"], p["cyan"]]) if mode == "dark" else wr.choice(["#ffd36e", "#ff9fd8", "#ffffff"])
                        tw_roll = wr.random()
                        cls = ' class="tw"' if (tw_roll < 0.08 and not flip) else ""
                        d = wr.uniform(0, 3)
                        delay = f' style="animation-delay:{d:.2f}s"' if cls else ""
                        out.append(
                            f'<rect{cls}{delay} x="{wx:.1f}" y="{wy:.1f}" width="{max(1.2, (w - 3) / cols - 1.5):.1f}" '
                            f'height="3" fill="{color}" opacity=".85"/>'
                        )
            if i == peak_i and c:
                cx = x + w / 2
                out.append(f'<rect x="{cx - 5:.1f}" y="{y - 26:.1f}" width="2" height="26" fill="{p["text"]}" opacity=".8"/>')
                out.append(f'<rect x="{cx + 3:.1f}" y="{y - 20:.1f}" width="2" height="20" fill="{p["text"]}" opacity=".8"/>')
                if not flip:
                    out.append(f'<circle class="bk" cx="{cx - 4:.1f}" cy="{y - 28:.1f}" r="2.4" fill="#ff4d6d"/>')
        return out

    s.extend(city(False))
    # lake + reflection
    s.append(f'<rect x="0" y="{ground}" width="{W}" height="{H - ground}" fill="{p["water"]}"/>')
    s.append(f'<g transform="translate(0 {2 * ground}) scale(1 -1)" opacity=".35">')
    s.extend(city(True))
    s.append("</g>")
    s.append(f'<rect x="0" y="{ground}" width="{W}" height="{H - ground}" fill="url(#fadeout)"/>')
    for j in range(5):
        y = ground + 14 + j * 16
        s.append(
            f'<g class="wv" style="animation-delay:{j * 0.7:.1f}s"><line x1="{60 + j * 40}" y1="{y}" x2="{W - 60 - j * 50}" '
            f'y2="{y}" stroke="{p["muted"]}" stroke-width="1" stroke-dasharray="2 14" opacity=".45"/></g>'
        )
    s.append(f'<line x1="0" y1="{ground}" x2="{W}" y2="{ground}" stroke="{p["pink"]}" stroke-opacity=".5"/>')
    # year labels
    seen = set()
    for x, w, h, c, k in towers:
        y = k[:4]
        if y not in seen:
            seen.add(y)
            s.append(
                f'<text x="{x:.0f}" y="{H - 16}" font-family="{FONT}" font-size="12" fill="{p["muted"]}">{y}</text>'
            )
    total = sum(counts)
    busiest = keys[peak_i]
    label = datetime.strptime(busiest, "%Y-%m").strftime("%b %Y")
    s.append(
        f'<text x="30" y="40" font-family="{FONT}" font-size="15" font-weight="600" fill="{p["text"]}">'
        f"{total:,} contributions · {len(keys)} months</text>"
    )
    s.append(
        f'<text x="30" y="62" font-family="{FONT}" font-size="13" fill="{p["muted"]}">'
        f"tallest tower: {esc(label)}</text>"
    )
    s.append("</svg>")
    return "".join(s)


def credits(hist: dict) -> str:
    data = hist["months"]
    total = sum(v["commits"] for v in data.values())
    first, last = min(data)[:4], max(data)[:4]
    return (
        f"<strong>{total:,} contributions · {first}–{last}</strong><br>"
        "<sub>one tower per month · built from my GitHub history · rebuilt nightly</sub>"
    )


def render_all(hist: dict) -> None:
    for mode in MODES:
        write(OUT / f"skyline-{mode}.svg", render(hist, mode))
