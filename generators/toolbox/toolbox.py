"""Toolbox: one SVG of skill chips, generated from toolbox.yaml.

One image instead of dozens of badge requests, in the same palette as the
rest of the page, with a dark and a light variant.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import ASSETS, FONT, MODES, PALETTES, esc, svg_open, write  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ASSETS / "toolbox"


def text_width(text: str, size: float) -> float:
    return sum(size * (0.36 if ch in "iljtf.() " else 0.62 if ch.isupper() else 0.54) for ch in text)


def render(cfg: dict, mode: str) -> str:
    p = PALETTES[mode]
    W = 960
    label_w = 250
    pad_x, chip_h, gap = 12, 28, 8
    rows: list[tuple[dict, list[tuple[float, float, str]]]] = []
    y = 26
    for group in cfg["groups"]:
        x = label_w
        placed = []
        for item in group["items"]:
            w = text_width(item, 13) + pad_x * 2
            if x + w > W - 24:
                x = label_w
                y += chip_h + gap
            placed.append((x, y, item))
            x += w + gap
        rows.append((group, placed))
        y += chip_h + 22
    H = y + 4
    s = [svg_open(W, H, "Toolbox: " + "; ".join(f'{g["name"]}: {", ".join(g["items"])}' for g in cfg["groups"]))]
    s.append(
        "<defs><style>.c{animation:in .5s ease-out both}@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}</style></defs>"
    )
    s.append(f'<rect width="{W}" height="{H}" rx="18" fill="{p["bg"]}"/>')
    accents = [p["pink"], p["violet"], p["cyan"], p["gold"]]
    n = 0
    for gi, (group, placed) in enumerate(rows):
        accent = accents[gi % len(accents)]
        first_y = placed[0][1]
        s.append(f'<text x="26" y="{first_y + 19}" font-size="16">{group["icon"]}</text>')
        s.append(
            f'<text x="54" y="{first_y + 19}" font-family="{FONT}" font-size="14" font-weight="700" '
            f'fill="{p["text"]}">{esc(group["name"])}</text>'
        )
        for x, cy, item in placed:
            w = text_width(item, 13) + pad_x * 2
            s.append(
                f'<g class="c" style="animation-delay:{n * 0.02:.2f}s"><rect x="{x:.1f}" y="{cy}" width="{w:.1f}" '
                f'height="{chip_h}" rx="14" fill="{p["bg2"]}" stroke="{accent}" stroke-opacity=".55"/>'
                f'<text x="{x + w / 2:.1f}" y="{cy + 18.5}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="13" fill="{p["text"]}">{esc(item)}</text></g>'
            )
            n += 1
    s.append("</svg>")
    return "".join(s)


def render_all() -> None:
    cfg = yaml.safe_load((HERE / "toolbox.yaml").read_text(encoding="utf-8"))
    for mode in MODES:
        write(OUT / f"toolbox-{mode}.svg", render(cfg, mode))


if __name__ == "__main__":
    render_all()
