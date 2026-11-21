"""'What should I build next?' poll.

Visitors vote by opening an issue titled "vote: <key>" (the README links are
pre-filled). One vote per GitHub account; voting again moves your vote.
The workflow records it in votes.json, re-renders the results chart and
closes the issue with a thank-you.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import ASSETS, FONT, MODES, PALETTES, esc, gradient, svg_open, write  # noqa: E402

HERE = Path(__file__).resolve().parent
VOTES = HERE / "votes.json"
OUT = ASSETS / "poll"
REPO = "bhargavirengarajan21/bhargavirengarajan21"


def config() -> dict:
    return yaml.safe_load((HERE / "poll.yaml").read_text(encoding="utf-8"))


def load_votes() -> dict:
    if not VOTES.exists():
        return {"votes": {}, "log": []}
    return json.loads(VOTES.read_text(encoding="utf-8"))


def save_votes(data: dict) -> None:
    VOTES.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_title(title: str, keys: list[str]) -> str | None:
    m = re.match(r"^\s*vote\s*:\s*([a-z0-9-]+)\s*$", (title or "").strip().lower())
    return m.group(1) if m and m.group(1) in keys else None


def cast(data: dict, user: str, key: str) -> str | None:
    """Record a vote; returns the user's previous choice (None if new)."""
    prev = data["votes"].get(user)
    data["votes"][user] = key
    data.setdefault("log", []).append(
        {"user": user, "vote": key, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    )
    data["log"] = data["log"][-100:]
    return prev


def tally(cfg: dict, data: dict) -> list[tuple[dict, int]]:
    counts = {o["key"]: 0 for o in cfg["options"]}
    for k in data["votes"].values():
        if k in counts:
            counts[k] += 1
    return [(o, counts[o["key"]]) for o in cfg["options"]]


def render(cfg: dict, data: dict, mode: str) -> str:
    p = PALETTES[mode]
    rows = tally(cfg, data)
    total = sum(c for _, c in rows)
    top = max((c for _, c in rows), default=0)
    W = 960
    row_h = 74
    top_pad = 92
    H = top_pad + row_h * len(rows) + 46
    bar_x, bar_w = 400, 360
    s = [svg_open(W, H, f"Poll results: {cfg['question']} " + "; ".join(f"{o['label']}: {c}" for o, c in rows))]
    s.append(
        "<defs>" + gradient("g", p)
        + f"""<style>
        .bar{{transform-box:fill-box;transform-origin:left;animation:grow 1.4s cubic-bezier(.2,.9,.3,1.2) both}}
        @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
        .crown{{animation:bob 2s ease-in-out infinite}}
        @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
        .pulse{{animation:pulse 1.6s ease-in-out infinite}}
        @keyframes pulse{{0%,100%{{opacity:.45}}50%{{opacity:1}}}}
        </style></defs>"""
    )
    s.append(f'<rect width="{W}" height="{H}" rx="18" fill="{p["bg"]}"/>')
    s.append(
        f'<text x="32" y="50" font-family="{FONT}" font-size="24" font-weight="700" fill="{p["text"]}">{esc(cfg["question"])}</text>'
    )
    status = f"{total} vote{'s' if total != 1 else ''} so far" if total else "no votes yet, be the first!"
    s.append(
        f'<text class="{"" if total else "pulse"}" x="{W - 32}" y="50" text-anchor="end" font-family="{FONT}" '
        f'font-size="15" fill="{p["pink"]}">{status}</text>'
    )
    for i, (o, c) in enumerate(rows):
        y = top_pad + i * row_h
        pct = (c / total) if total else 0
        leader = total and c == top
        s.append(f'<rect x="20" y="{y - 6}" width="{W - 40}" height="{row_h - 10}" rx="14" fill="{p["bg2"]}"/>')
        s.append(f'<text x="40" y="{y + 32}" font-size="26">{o["emoji"]}</text>')
        s.append(
            f'<text x="82" y="{y + 24}" font-family="{FONT}" font-size="17" font-weight="600" fill="{p["text"]}">{esc(o["label"])}</text>'
        )
        s.append(
            f'<text x="82" y="{y + 46}" font-family="{FONT}" font-size="12.5" fill="{p["muted"]}">{esc(o["blurb"])}</text>'
        )
        s.append(f'<rect x="{bar_x}" y="{y + 14}" width="{bar_w}" height="22" rx="11" fill="{p["grid"]}"/>')
        if c:
            s.append(
                f'<rect class="bar" style="animation-delay:{i * 0.12:.2f}s" x="{bar_x}" y="{y + 14}" '
                f'width="{max(22, bar_w * pct):.1f}" height="22" rx="11" fill="url(#g)"/>'
            )
        s.append(
            f'<text x="{bar_x + bar_w + 18}" y="{y + 31}" font-family="{FONT}" font-size="16" font-weight="700" '
            f'fill="{p["text"]}">{round(pct * 100)}%</text>'
        )
        s.append(
            f'<text x="{bar_x + bar_w + 70}" y="{y + 31}" font-family="{FONT}" font-size="13" fill="{p["muted"]}">{c} vote{"" if c == 1 else "s"}</text>'
        )
        if leader:
            s.append(f'<text class="crown" x="{W - 58}" y="{y + 33}" font-size="22">👑</text>')
    s.append(
        f'<text x="32" y="{H - 18}" font-family="{FONT}" font-size="12.5" fill="{p["muted"]}">'
        "one vote per GitHub account · vote again to change your pick · updates a minute after you vote</text>"
    )
    s.append("</svg>")
    return "".join(s)


def credits(cfg: dict, data: dict) -> str:
    rows = tally(cfg, data)
    total = sum(c for _, c in rows)
    if not total:
        return "<sub>no votes yet: yours could decide my next project</sub>"
    o, c = max(rows, key=lambda r: r[1])
    recent = []
    for e in reversed(data.get("log", [])):
        if e["user"] not in recent:
            recent.append(e["user"])
        if len(recent) == 5:
            break
    names = ", ".join(f'<a href="https://github.com/{esc(u)}">@{esc(u)}</a>' for u in recent)
    return (
        f"<strong>{total} vote{'s' if total != 1 else ''}</strong> · leading: {o['emoji']} {esc(o['label'])}"
        f"<br><sub>recent voters: {names}</sub>"
    )


def render_all() -> tuple[dict, dict]:
    cfg, data = config(), load_votes()
    for mode in MODES:
        write(OUT / f"poll-{mode}.svg", render(cfg, data, mode))
    return cfg, data
