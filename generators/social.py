"""Social buttons: small pill SVGs (dark + light) with brand icons.

Icons are from Simple Icons (CC0). Run manually after editing BUTTONS:
    python generators/social.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theme import ASSETS, FONT, MODES, PALETTES, esc, svg_open, write  # noqa: E402

ICONS = json.loads((Path(__file__).resolve().parent / "icons.json").read_text())
OUT = ASSETS / "social"

# key, label, icon, brand colour
BUTTONS = [
    ("linkedin", "LinkedIn", "linkedin", "#0A66C2"),
    ("email", "Email", "gmail", "#EA4335"),
    ("huggingface", "Hugging Face", "huggingface", "#FFB000"),
    ("npm", "npm", "npm", "#CB3837"),
    ("chrome", "Chrome extension", "googlechrome", "#4285F4"),
    ("portfolio", "Portfolio", "vercel", None),
]


def width_for(label: str) -> int:
    return int(52 + len(label) * 8.4)


def render(label: str, icon: str, brand: str | None, mode: str) -> str:
    p = PALETTES[mode]
    w, h = width_for(label), 44
    color = brand or p["text"]
    s = [svg_open(w, h, label)]
    s.append(
        "<defs><style>.r{transition:none;animation:pulse 3s ease-in-out infinite}"
        "@keyframes pulse{0%,100%{stroke-opacity:.45}50%{stroke-opacity:1}}</style></defs>"
    )
    s.append(
        f'<rect class="r" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="21" fill="{p["bg2"]}" '
        f'stroke="{p["pink"]}" stroke-width="1.5"/>'
    )
    s.append(
        f'<g transform="translate(16 12) scale(0.8333)"><path d="{ICONS[icon]}" fill="{color}"/></g>'
    )
    s.append(
        f'<text x="44" y="27.5" font-family="{FONT}" font-size="14" font-weight="600" fill="{p["text"]}">{esc(label)}</text>'
    )
    s.append("</svg>")
    return "".join(s)


def render_all() -> dict[str, int]:
    sizes = {}
    for key, label, icon, brand in BUTTONS:
        for mode in MODES:
            write(OUT / f"{key}-{mode}.svg", render(label, icon, brand, mode))
        sizes[key] = width_for(label)
    return sizes


if __name__ == "__main__":
    print(render_all())
