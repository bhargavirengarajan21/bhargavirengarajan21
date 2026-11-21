"""Header: my name drawn over the waveform of the current gesture loop.

The bars are the loudness envelope of loop.wav, so the header changes shape
every time a visitor plays a gesture. A playhead sweeps across in time with
the loop and the bars breathe gently, so nothing on the page sits still.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import ASSETS, FONT, MODES, MONO, PALETTES, gradient, svg_open, write  # noqa: E402
from loop import loop as L  # noqa: E402

OUT = ASSETS / "header"
BARS = 96


def envelope(samples: np.ndarray, bars: int = BARS) -> np.ndarray:
    one_loop = int(L.RATE * L.STEP_SECONDS) * L.STEPS
    x = np.abs(samples[:one_loop]) if len(samples) >= one_loop else np.abs(samples)
    chunks = np.array_split(x, bars)
    env = np.array([np.sqrt(np.mean(c**2)) if len(c) else 0.0 for c in chunks])
    env = env / (env.max() or 1.0)
    return np.clip(env, 0.04, 1.0)


def render(samples: np.ndarray, state: dict, mode: str) -> str:
    p = PALETTES[mode]
    W, H = 1200, 340
    env = envelope(samples)
    loop_s = L.STEP_SECONDS * L.STEPS
    x0, x1 = 60, W - 60
    bw = (x1 - x0) / BARS
    mid = 205
    s = [svg_open(W, H, "Bhargavi Rengarajan, Full-Stack and AI Engineer. Header drawn from the gesture loop audio")]
    s.append(
        "<defs>"
        + gradient("g", p)
        + f'<radialGradient id="glow" cx="50%" cy="35%" r="65%"><stop offset="0" stop-color="{p["violet"]}" '
        f'stop-opacity="{0.28 if mode == "dark" else 0.14}"/><stop offset="1" stop-color="{p["bg"]}" stop-opacity="0"/></radialGradient>'
        + f"""<style>
        .b{{transform-box:fill-box;transform-origin:center;animation:breathe 2.6s ease-in-out infinite}}
        @keyframes breathe{{0%,100%{{transform:scaleY(1)}}50%{{transform:scaleY(.72)}}}}
        .ph{{animation:sweep {loop_s:.3f}s linear infinite}}
        @keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({x1 - x0}px)}}}}
        .fade{{animation:fade 1.6s ease-out both}}
        @keyframes fade{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
        </style></defs>"""
    )
    s.append(f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#glow)"/>')
    for i, a in enumerate(env):
        h = 6 + a * 110
        x = x0 + i * bw
        delay = (i % 12) * 0.12
        s.append(
            f'<rect class="b" style="animation-delay:{delay:.2f}s" x="{x + 1:.1f}" y="{mid - h / 2:.1f}" '
            f'width="{max(bw - 3, 2):.1f}" height="{h:.1f}" rx="2" fill="url(#g)" opacity=".85"/>'
        )
    s.append(
        f'<g class="ph"><rect x="{x0}" y="{mid - 70}" width="3" height="140" rx="1.5" fill="{p["cyan"]}"/></g>'
    )
    s.append(
        f'<g class="fade"><text x="{W / 2}" y="96" text-anchor="middle" font-family="{FONT}" font-size="58" '
        f'font-weight="800" letter-spacing="1" fill="{p["text"]}">Bhargavi Rengarajan</text>'
        f'<text x="{W / 2}" y="132" text-anchor="middle" font-family="{FONT}" font-size="20" letter-spacing="3" '
        f'fill="{p["pink"]}">FULL-STACK &amp; AI ENGINEER · CHICAGO</text></g>'
    )
    tune = " ".join(
        (L.GESTURES[g][0] if g in L.GESTURES else (L.REST_EMOJI if g == L.REST else "·")) for g in state["steps"]
    )
    s.append(
        f'<text x="{W / 2}" y="{H - 34}" text-anchor="middle" font-family="{MONO}" font-size="15" '
        f'fill="{p["muted"]}">now playing: {tune}</text>'
    )
    s.append("</svg>")
    return "".join(s)


def render_all(samples: np.ndarray, state: dict) -> None:
    for mode in MODES:
        write(OUT / f"header-{mode}.svg", render(samples, state, mode))
