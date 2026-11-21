"""Now playing: a Chicago house equalizer strip for the top of the README.

Chicago is the home of house music, so this strip pulses to a classic house
groove: 125 BPM, a kick on every beat (four on the floor), claps on 2 and 4,
open hi-hats on the off-beats. One bar is 1.92 s and every animation loops on
that bar, so the motion stays locked to the groove.

Outputs an animated SVG (dark + light) and a GIF. A GIF has no sound; the
motion is the music.

    python generators/beat/beat.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import ASSETS, FONT, MODES, PALETTES, gradient, svg_open, write  # noqa: E402

OUT = ASSETS / "beat"
BPM = 125
BEAT = 60 / BPM          # 0.48 s
BAR = BEAT * 4           # 1.92 s
STEPS = 16               # sixteenth notes per bar
BARS = 56
W, H = 1200, 150
FLOOR = 112


def groove(step: int) -> dict[str, float]:
    """Drum hits on a 16-step house pattern."""
    return {
        "kick": 1.0 if step % 4 == 0 else 0.0,
        "clap": 1.0 if step in (4, 12) else 0.0,
        "hat": 1.0 if step % 4 == 2 else 0.35 if step % 2 else 0.0,
        "bass": 0.8 if step in (2, 3, 6, 10, 11, 14) else 0.0,
    }


def level(bar: int, step: int) -> float:
    """Height 0..1 of equalizer bar `bar` at sixteenth `step`, with a short decay."""
    pos = bar / (BARS - 1)                       # 0 = lows (left) .. 1 = highs (right)
    weights = {
        "kick": max(0.0, 1 - pos * 2.2),
        "bass": max(0.0, 1 - abs(pos - 0.3) * 3),
        "clap": max(0.0, 1 - abs(pos - 0.55) * 2.6),
        "hat": max(0.0, (pos - 0.45) * 1.8),
    }
    v = 0.0
    for back in range(4):                        # decay over the previous three sixteenths
        g = groove((step - back) % STEPS)
        hit = sum(g[k] * weights[k] for k in g)
        v = max(v, hit * (0.55 ** back))
    shimmer = 0.12 + 0.1 * math.sin(bar * 1.7 + step * 0.9) ** 2
    return min(1.0, 0.1 + v * 0.85 + shimmer)


def render_svg(mode: str) -> str:
    p = PALETTES[mode]
    x0, x1 = 40, W - 40
    slot = (x1 - x0) / BARS
    s = [svg_open(W, H, "Now playing: a Chicago house equalizer pulsing at 125 BPM")]
    css = [
        f".kick{{animation:kick {BEAT:.2f}s ease-out infinite}}",
        "@keyframes kick{0%{opacity:.95;transform:scale(1.08)}60%,100%{opacity:.35;transform:scale(1)}}",
        f".dot{{animation:dot {BEAT:.2f}s steps(1) infinite}}",
        "@keyframes dot{0%{opacity:1}50%{opacity:.2}}",
        ".b{transform-box:fill-box;transform-origin:bottom}",
    ]
    bars = []
    for i in range(BARS):
        frames = [level(i, st) for st in range(STEPS)]
        kf = "".join(
            f"{st * 100 / STEPS:.2f}%{{transform:scaleY({v:.2f})}}" for st, v in enumerate(frames)
        ) + f"100%{{transform:scaleY({frames[0]:.2f})}}"
        css.append(f"@keyframes e{i}{{{kf}}}.e{i}{{animation:e{i} {BAR:.2f}s linear infinite}}")
        x = x0 + i * slot
        bars.append(
            f'<rect class="b e{i}" x="{x + 2:.1f}" y="{FLOOR - 84}" width="{slot - 4:.1f}" height="84" rx="3" fill="url(#g)"/>'
        )
    s.append("<defs>" + gradient("g", p, vertical=True) + "<style>" + "".join(css) + "</style></defs>")
    s.append(f'<rect width="{W}" height="{H}" rx="16" fill="{p["bg"]}"/>')
    s.append(
        f'<circle class="kick" style="transform-box:fill-box;transform-origin:center" cx="{W / 2}" cy="{FLOOR - 48}" r="52" '
        f'fill="{p["violet"]}" opacity=".35" filter="blur(0)"/>'
    )
    s.extend(bars)
    # reflection line + labels
    s.append(f'<line x1="{x0}" y1="{FLOOR + 1}" x2="{x1}" y2="{FLOOR + 1}" stroke="{p["pink"]}" stroke-opacity=".6"/>')
    s.append(
        f'<circle class="dot" cx="{x0 + 6}" cy="{FLOOR + 21}" r="4" fill="#ff4d6d"/>'
        f'<text x="{x0 + 18}" y="{FLOOR + 26}" font-family="{FONT}" font-size="13" letter-spacing="2" fill="{p["muted"]}">'
        f"NOW PLAYING · CHICAGO HOUSE · {BPM} BPM · FOUR ON THE FLOOR</text>"
    )
    s.append(
        f'<text x="{x1}" y="{FLOOR + 26}" text-anchor="end" font-family="{FONT}" font-size="13" letter-spacing="2" '
        f'fill="{p["pink"]}">♫ made in chicago</text>'
    )
    s.append("</svg>")
    return "".join(s)


def render_gif() -> None:
    from PIL import Image, ImageDraw, ImageFont

    p = PALETTES["dark"]
    scale = 2
    w, h = W // 2, H // 2
    frames = []
    fps_ms = 40                       # 48 frames x 40 ms = 1.92 s = one bar at 125 BPM
    n = round(BAR * 1000 / fps_ms)

    def rgb(hexcolor: str) -> tuple[int, int, int]:
        hexcolor = hexcolor.lstrip("#")
        return tuple(int(hexcolor[i : i + 2], 16) for i in (0, 2, 4))

    pink, violet, bg = rgb(p["pink"]), rgb(p["violet"]), rgb(p["bg"])
    try:
        fnt = ImageFont.truetype(str(Path(__file__).resolve().parent.parent / "intro" / "fonts" / "Inter-Medium.otf"), 7 * scale)
    except OSError:
        fnt = ImageFont.load_default()
    for f in range(n):
        t = f * fps_ms / 1000
        step_f = (t / BAR) * STEPS
        st = int(step_f) % STEPS
        img = Image.new("RGB", (w * scale, h * scale), bg)
        d = ImageDraw.Draw(img)
        since_kick = (t % BEAT) / BEAT
        glow = max(0.0, 1 - since_kick * 1.6)
        r = int((24 + 5 * glow) * scale)
        cx, cy = w * scale // 2, int((FLOOR / 2 - 26) * scale)
        gc = tuple(int(bg[k] + (violet[k] - bg[k]) * (0.25 + 0.45 * glow)) for k in range(3))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=gc)
        x0, x1 = 20 * scale, (w - 20) * scale
        slot = (x1 - x0) / BARS
        floor = int(FLOOR / 2 * scale)
        for i in range(BARS):
            v = level(i, st)
            bh = int(42 * scale * v)
            k = i / (BARS - 1)
            col = tuple(int(pink[c] + (violet[c] - pink[c]) * k) for c in range(3))
            xa = int(x0 + i * slot + scale)
            d.rounded_rectangle((xa, floor - bh, int(xa + slot - 2 * scale), floor), radius=2 * scale, fill=col)
        d.line((x0, floor + scale, x1, floor + scale), fill=pink, width=1)
        if since_kick < 0.5:
            d.ellipse((x0, floor + 8 * scale, x0 + 4 * scale, floor + 12 * scale), fill=(255, 77, 109))
        d.text((x0 + 8 * scale, floor + 6 * scale), f"NOW PLAYING · CHICAGO HOUSE · {BPM} BPM", font=fnt, fill=rgb(p["muted"]))
        frames.append(img.resize((w * 2, h * 2), Image.LANCZOS).convert("P", palette=Image.ADAPTIVE, colors=64))
    OUT.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT / "beat.gif", save_all=True, append_images=frames[1:], duration=fps_ms, loop=0, optimize=True)


def render_all() -> None:
    for mode in MODES:
        write(OUT / f"beat-{mode}.svg", render_svg(mode))


if __name__ == "__main__":
    render_all()
    render_gif()
    print("wrote", OUT)
