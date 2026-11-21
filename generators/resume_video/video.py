"""The video résumé: loud, proud, over-the-top, and every fact is real.

    python generators/resume_video/video.py            -> docs/media/resume.mp4 + posters
    python generators/resume_video/video.py --preview  -> still frames in /tmp/rv_*.png

Original score (score.py) plus cheesy-on-purpose title cards drawn with Pillow:
spinning sunbursts, 3D extruded titles, counters that tick up and land with a
arcade high-score screen, a one-skill-per-beat montage, real LinkedIn recommendations,
star wipes, confetti. Needs ffmpeg.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score as S  # noqa: E402

ROOT = HERE.parent.parent
MEDIA = ROOT / "docs" / "media"
ASSETS = ROOT / "assets" / "resume"
FONTS = HERE.parent / "intro" / "fonts"
ANTON = str(FONTS / "Anton-Regular.ttf")
INTER_M = str(FONTS / "Inter-Medium.otf")
INTER_L = str(FONTS / "Inter-Light.otf")
PIXEL = str(FONTS / "Silkscreen-Regular.ttf")

W, H, FPS = 1280, 720, 30
BAR, BEAT = S.BAR, S.BEAT

PINK = (255, 102, 204)
VIOLET = (157, 123, 255)
GOLD = (255, 211, 110)
CYAN = (92, 225, 230)
WHITE = (255, 255, 255)
INK = (40, 18, 60)


def scene_time(name: str) -> tuple[float, float]:
    a, b = S.SCENES[name]
    return a * BAR, (a + b) * BAR


EXPERIENCE = [
    ("ROCKET MORTGAGE", "Software Engineer  ·  2025 – now", "AI agents  ·  payments  ·  Kafka  ·  Spring Boot"),
    ("MR. COOPER", "Intern → Software Engineer II  ·  2020 – 2023", "Challenger Q4 Award winner  ·  React  ·  Next.js  ·  Java"),
    ("UC RIVERSIDE", "M.S. Computer Engineering  ·  GPA 3.7", "GPU-accelerated computer vision research"),
    ("THIAGARAJAR COLLEGE OF ENGINEERING", "B.E. Computer Science", "IEEE publication on ML hazard assessment"),
]
# arcade high-score table: (score, label), locked in one row every two beats
HIGH_SCORES = [
    ("80%", "ALERT NOISE CUT"),
    ("518K+", "API CALLS A MONTH"),
    ("17K", "EVENTS A DAY RESCUED"),
    ("$350K", "SAVED"),
]
SKILLS = ["JAVA", "SPRING BOOT", "KAFKA", "REACT", "NEXT.JS", "NODE.JS", "TYPESCRIPT", "CLAUDE SDK",
          "MCP", "RAG", "LANGGRAPH", "POSTGRESQL", "REDIS", "KUBERNETES", "AZURE", "AWS"]
# Real recommendations from my LinkedIn profile (linkedin.com/in/bhargavi-r21), quoted word for word.
TESTIMONIALS = [
    ("“She’s a standout developer. She adapts quickly",
     "and picks up new technologies with ease.”",
     "Troy Calandra", "Software Engineer · senior teammate"),
    ("“She is extremely detailed, a challenger of convention…",
     "I would openly welcome her to my team again!”",
     "Carson Burrus", "Product Manager · worked with Bhargavi at Mr. Cooper"),
    ("“I would highly recommend Bhargavi in a heartbeat!",
     "…completed professionally, with high quality, and on time!”",
     "Shayla M Ochoa", "Product Manager · Bhargavi’s product and engineering team"),
]
AWARDS = [
    "IEEE publication  ·  ML-based spatial hazard assessment",
    "Certified: Claude with the Anthropic API",
    "Certified: Microsoft Azure Fundamentals (AZ-900)",
    "Hackathons: Meta AI  ·  Build Small",
]


# ---------------------------------------------------------------- helpers ----

def ease_out_back(x: float) -> float:
    x = min(1.0, max(0.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


@lru_cache(maxsize=None)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def fit_font(text: str, path: str, size: int, max_w: int) -> ImageFont.FreeTypeFont:
    f = font(path, size)
    while f.getlength(text) > max_w and size > 12:
        size -= 4
        f = font(path, size)
    return f


@lru_cache(maxsize=256)
def text_layer(text: str, path: str, size: int, fill: tuple, depth: int = 0, shadow: tuple = INK,
               outline: int = 0, max_w: int = 1180) -> Image.Image:
    """RGBA layer with optional 3D extrusion and outline, cropped to content."""
    f = fit_font(text, path, size, max_w)
    l, t, r, b = f.getbbox(text)
    pad = depth + outline + 12
    img = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = pad - l, pad - t
    for k in range(depth, 0, -1):
        shade = tuple(int(c * (0.55 + 0.45 * (1 - k / max(depth, 1)))) for c in shadow) + (255,)
        d.text((ox + k, oy + k), text, font=f, fill=shade)
    if outline:
        d.text((ox, oy), text, font=f, fill=fill + (255,), stroke_width=outline, stroke_fill=INK + (255,))
    else:
        d.text((ox, oy), text, font=f, fill=fill + (255,))
    return img


def paste(frame: Image.Image, layer: Image.Image, cx: float, cy: float, scale: float = 1.0,
          angle: float = 0.0, alpha: float = 1.0) -> None:
    if alpha <= 0.01 or scale <= 0.01:
        return
    lay = layer
    if abs(scale - 1) > 0.01:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BILINEAR)
    if abs(angle) > 0.2:
        lay = lay.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99:
        a = lay.getchannel("A").point(lambda v: int(v * alpha))
        lay = lay.copy()
        lay.putalpha(a)
    frame.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def gradient_bg(c1: tuple, c2: tuple) -> Image.Image:
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    k = np.clip(0.6 * y + 0.4 * x, 0, 1)
    arr = np.array(c1, np.float32) * (1 - k) + np.array(c2, np.float32) * k
    arr = np.broadcast_to(arr, (H, W, 3))
    return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")


def sunburst(c1: tuple, c2: tuple, rays: int = 24) -> Image.Image:
    size = int(math.hypot(W, H)) + 40
    img = Image.new("RGBA", (size, size), c1 + (255,))
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    for i in range(rays):
        if i % 2:
            continue
        a0 = 2 * math.pi * i / rays
        a1 = 2 * math.pi * (i + 1) / rays
        d.polygon([(cx, cy), (cx + size * math.cos(a0), cy + size * math.sin(a0)),
                   (cx + size * math.cos(a1), cy + size * math.sin(a1))], fill=c2 + (255,))
    return img


def star_points(cx: float, cy: float, r: float, inner: float = 0.45, n: int = 5, rot: float = -90):
    pts = []
    for i in range(n * 2):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def draw_star(frame: Image.Image, cx, cy, r, color, alpha=255, rot=-90):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon(star_points(cx, cy, r, rot=rot), fill=color + (alpha,))
    frame.alpha_composite(layer)


def draw_trophy(frame: Image.Image, cx: float, cy: float, scale: float, shine: float = 0.5) -> None:
    if scale <= 0.02:
        return
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    k = scale * 1.25
    gold, dark = GOLD + (255,), (205, 140, 30, 255)
    # handles
    d.ellipse((cx - 95 * k, cy - 80 * k, cx - 35 * k, cy + 10 * k), outline=dark, width=int(12 * k) or 1)
    d.ellipse((cx + 35 * k, cy - 80 * k, cx + 95 * k, cy + 10 * k), outline=dark, width=int(12 * k) or 1)
    # cup
    d.pieslice((cx - 70 * k, cy - 150 * k, cx + 70 * k, cy + 40 * k), 0, 180, fill=gold)
    d.rectangle((cx - 70 * k, cy - 100 * k, cx + 70 * k, cy - 55 * k), fill=gold)
    d.polygon([(cx - 70 * k, cy - 100 * k), (cx + 70 * k, cy - 100 * k), (cx + 70 * k, cy - 55 * k), (cx - 70 * k, cy - 55 * k)], fill=gold)
    # stem and base
    d.rectangle((cx - 12 * k, cy + 40 * k, cx + 12 * k, cy + 80 * k), fill=dark)
    d.rounded_rectangle((cx - 55 * k, cy + 80 * k, cx + 55 * k, cy + 110 * k), radius=int(8 * k), fill=gold)
    d.rounded_rectangle((cx - 70 * k, cy + 110 * k, cx + 70 * k, cy + 135 * k), radius=int(8 * k), fill=dark)
    # shine and star
    d.ellipse((cx - 45 * k, cy - 90 * k, cx - 28 * k, cy - 20 * k), fill=(255, 255, 255, int(120 + 100 * shine)))
    d.polygon(star_points(cx + 5 * k, cy - 45 * k, 26 * k), fill=(255, 255, 255, 230))
    frame.alpha_composite(layer)


# ------------------------------------------------------------------ scenes ----

class Scenes:
    def __init__(self):
        self.bg = {
            "intro": gradient_bg((20, 10, 40), (60, 20, 90)),
            "experience": gradient_bg((60, 20, 110), (255, 102, 204)),
            "skills": gradient_bg((10, 10, 30), (40, 20, 80)),
            "testimonials": gradient_bg((255, 240, 250), (240, 220, 255)),
            "awards": gradient_bg((30, 15, 60), (90, 40, 140)),
            "arcade": gradient_bg((6, 4, 16), (18, 8, 34)),
            "end": gradient_bg((20, 10, 40), (50, 20, 80)),
        }
        self.burst_pink = sunburst((255, 102, 204), (255, 140, 220))
        self.burst_violet = sunburst((120, 80, 230), (157, 123, 255))
        self.burst_gold = sunburst((255, 190, 70), (255, 220, 120))
        rng = np.random.default_rng(5)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3), rng.uniform(0, 6.28)) for _ in range(120)]
        self.confetti = [
            (rng.uniform(0, W), rng.uniform(-H, 0), rng.uniform(60, 220), rng.uniform(-60, 60),
             rng.uniform(0, 360), rng.uniform(-400, 400), [PINK, VIOLET, GOLD, CYAN, WHITE][int(rng.integers(5))])
            for _ in range(260)
        ]
        self.rng = np.random.default_rng(9)

    def burst(self, which: Image.Image, t: float, speed: float = 18) -> Image.Image:
        rot = which.rotate(t * speed, resample=Image.BILINEAR)
        x = (rot.width - W) // 2
        y = (rot.height - H) // 2
        return rot.crop((x, y, x + W, y + H))

    def starfield(self, frame: Image.Image, t: float, color=WHITE):
        d = ImageDraw.Draw(frame)
        for x, y, s, ph in self.stars:
            a = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 3 + ph))
            r = s * a
            c = tuple(int(v * a) for v in color)
            d.ellipse((x - r, y - r, x + r, y + r), fill=c + (255,))

    def sparkles(self, frame: Image.Image, t: float, count: int = 14, seed: int = 0):
        r = np.random.default_rng(seed + int(t * 6))
        for _ in range(count):
            x, y = r.uniform(60, W - 60), r.uniform(70, H - 70)
            s = r.uniform(8, 22) * (0.5 + 0.5 * math.sin(t * 9 + x))
            if s > 2:
                draw_star(frame, x, y, s, GOLD, 230, rot=r.uniform(0, 72))

    # each scene draws onto a fresh RGBA frame
    def intro(self, t, f):
        f.paste(self.bg["intro"])
        self.starfield(f, t)
        p = t / BAR
        if p < 1:
            s = ease_out_back(p * 1.6) * 1.0
            paste(f, text_layer("PRESENTING...", ANTON, 130, GOLD, depth=10), W / 2, H / 2, scale=s, angle=(1 - min(1, p * 1.6)) * 360)
        else:
            q = p - 1
            paste(f, text_layer("THE VIDEO RÉSUMÉ OF", ANTON, 96, WHITE, depth=8, shadow=(120, 40, 160)), W / 2, H / 2,
                  scale=0.6 + 0.4 * ease_out_back(q * 2))
            self.sparkles(f, t, 10)

    def name(self, t0, t, f):
        f.paste(self.burst(self.burst_pink, t))
        dt = t - t0
        s = ease_out_back(dt * 2.2)
        wob = math.sin(dt * 7) * 2 * math.exp(-dt * 1.5)
        paste(f, text_layer("BHARGAVI", ANTON, 210, WHITE, depth=16, shadow=(110, 30, 140), outline=4), W / 2, 270, scale=s, angle=wob)
        paste(f, text_layer("RENGARAJAN", ANTON, 120, GOLD, depth=10, shadow=(110, 30, 140), outline=3), W / 2, 445,
              scale=ease_out_back((dt - 0.35) * 2.5))
        a = smooth((dt - 0.9) * 3)
        paste(f, text_layer("★  FULL-STACK & AI ENGINEER  ·  CHICAGO  ★", INTER_M, 34, WHITE, depth=3), W / 2, 560, alpha=a)
        self.sparkles(f, t, 12, 3)

    def experience(self, t0, t, f):
        f.paste(self.bg["experience"])
        self.starfield(f, t, GOLD)
        paste(f, text_layer("EXPERIENCE", ANTON, 70, GOLD, depth=6), W / 2, 86, angle=-3)
        idx = min(3, int((t - t0) / BAR))
        dt = (t - t0) - idx * BAR
        title, line1, line2 = EXPERIENCE[idx]
        side = -1 if idx % 2 == 0 else 1
        x = W / 2 + side * (1 - ease_out_back(dt * 2.4)) * W
        card = card_layer(title, line1, line2)
        paste(f, card, x, H / 2 + 40, angle=side * -2 * (1 - smooth(dt * 3)))
        if title == "MR. COOPER" and dt > 0.45:
            paste(f, badge_layer("AWARD WINNER"), x + 380, H / 2 - 120, angle=12,
                  scale=ease_out_back((dt - 0.45) * 4))
        if dt < 0.25:
            self.sparkles(f, t, 8, idx)

    def numbers(self, t0, t, f):
        f.paste(self.bg["arcade"])
        d = ImageDraw.Draw(f)
        for y in range(0, H, 4):  # CRT scanlines
            d.line((0, y, W, y), fill=(0, 0, 0, 90))
        dt = t - t0
        blink = (int(dt * 4) % 2) == 0
        paste(f, text_layer("HIGH SCORES", PIXEL, 64, PINK if blink else GOLD), W / 2, 92)
        paste(f, text_layer("PLAYER 1:  BHARGAVI", PIXEL, 24, CYAN), W / 2, 150)
        for row, (score, label) in enumerate(HIGH_SCORES):
            lock = (row * 2 + 1.5) * BEAT
            appear = lock - 1.2 * BEAT
            if dt < appear:
                continue
            y = 250 + row * 98
            rank = ["1ST", "2ND", "3RD", "4TH"][row]
            color = [GOLD, (220, 220, 235), (230, 160, 90), PINK][row]
            if dt < lock:  # slot-machine digits rolling
                r = np.random.default_rng(int(dt * 30) + row * 100)
                shown = "".join(str(int(r.integers(10))) if ch.isdigit() else ch for ch in score)
                c = (150, 150, 170)
            else:
                shown, c = score, color
            paste(f, text_layer(rank, PIXEL, 40, color), 230, y)
            sc = 1.0 + (0.18 * math.exp(-(dt - lock) * 12) if dt >= lock else 0)
            paste(f, text_layer(shown, PIXEL, 52, c), 470, y, scale=sc)
            paste(f, text_layer(label, PIXEL, 28, WHITE), 885, y, alpha=smooth((dt - lock) * 5))
        if dt > (3 * 2 + 1.5) * BEAT and blink:
            paste(f, text_layer("NEW HIGH SCORE!", PIXEL, 34, GOLD), W / 2, 640)

    def skills(self, t0, t, f):
        f.paste(self.bg["skills"])
        self.starfield(f, t)
        dt = t - t0
        paste(f, text_layer("SKILLS", ANTON, 84, GOLD, depth=7, shadow=(90, 40, 140)), W / 2, 92,
              scale=ease_out_back(dt * 3))
        colors = [PINK, CYAN, GOLD, VIOLET]
        cols, rows = 4, 4
        cw, ch, gx, gy = 268, 92, 22, 22
        x0 = (W - (cols * cw + (cols - 1) * gx)) / 2 + cw / 2
        y0 = 205
        for k, word in enumerate(SKILLS):
            appear = dt - k * BEAT / 3
            if appear <= 0:
                continue
            r, c = divmod(k, cols)
            cx = x0 + c * (cw + gx)
            cy = y0 + r * (ch + gy)
            paste(f, chip_layer(word, colors[(r + c) % 4]), cx, cy, scale=ease_out_back(appear * 5))

    def testimonials(self, t0, t, f):
        f.paste(self.bg["testimonials"])
        paste(f, text_layer("TESTIMONIALS", ANTON, 68, PINK, depth=6, shadow=(120, 60, 160)), W / 2, 92)
        paste(f, text_layer("real ones, from my LinkedIn recommendations", INTER_L, 22, (120, 90, 150)), W / 2, 142)
        span = (scene_time("testimonials")[1] - t0) / 3
        idx = min(2, int((t - t0) / span))
        dt = (t - t0) - idx * span
        line1, line2, who, role = TESTIMONIALS[idx]
        paste(f, text_layer("“", ANTON, 220, (255, 170, 220)), 150, 300, alpha=smooth(dt * 3), scale=0.6 + 0.4 * ease_out_back(dt * 3))
        y = 300 if line2 else 335
        paste(f, text_layer(line1, INTER_M, 42, INK, max_w=1080), W / 2, y, scale=0.94 + 0.06 * ease_out_back(dt * 3),
              alpha=smooth(dt * 4))
        if line2:
            paste(f, text_layer(line2, INTER_M, 42, INK, max_w=1080), W / 2, y + 62, alpha=smooth((dt - 0.25) * 4))
        paste(f, text_layer("— " + who, INTER_M, 34, PINK), W / 2, 470, alpha=smooth((dt - 0.6) * 3))
        paste(f, text_layer(role, INTER_L, 26, (120, 60, 160)), W / 2, 515, alpha=smooth((dt - 0.8) * 3))

    def awards(self, t0, t, f):
        f.paste(self.bg["awards"])
        self.starfield(f, t, GOLD)
        dt = t - t0
        s1 = ease_out_back(dt * 2.5)
        draw_trophy(f, 150, 235, 0.8 * s1, shine=0.5 + 0.5 * math.sin(dt * 6))
        paste(f, text_layer("AWARD-WINNING", INTER_M, 30, (230, 210, 255)), 750, 140, alpha=smooth(dt * 3))
        paste(f, text_layer("CHALLENGER Q4 AWARD", ANTON, 88, GOLD, depth=8, shadow=(90, 40, 20), outline=3, max_w=860),
              750, 215, scale=s1)
        paste(f, text_layer("Mr. Cooper", INTER_M, 32, WHITE), 750, 298, alpha=smooth((dt - 0.4) * 3))
        for i, line in enumerate(AWARDS):
            appear = dt - BAR - i * BEAT * 1.5
            if appear > 0:
                paste(f, text_layer("★  " + line, INTER_M, 32, WHITE, depth=2), W / 2, 445 + i * 58,
                      scale=ease_out_back(appear * 4))
        if dt < 0.3:
            self.sparkles(f, t, 14, 77)

    def finale(self, t0, t, f):
        f.paste(self.burst(self.burst_gold, t, 30))
        dt = t - t0
        slam = 1 + 1.6 * math.exp(-dt * 10)
        paste(f, text_layer("HIRE HER.", ANTON, 230, PINK, depth=18, shadow=INK, outline=6), W / 2, 300, scale=slam,
              angle=-4 * math.exp(-dt * 3))
        if dt > BAR:
            paste(f, text_layer("AVAILABLE IMMEDIATELY", ANTON, 70, WHITE, depth=6, shadow=INK, outline=3), W / 2, 470,
                  scale=ease_out_back((dt - BAR) * 3))
        if dt > 2 * BAR:
            paste(f, text_layer("FULL-TIME  ·  SOFTWARE & AI ENGINEERING", INTER_M, 34, INK), W / 2, 560,
                  alpha=smooth((dt - 2 * BAR) * 3))
        self.confetti_rain(f, dt)

    def confetti_rain(self, f, dt):
        d = ImageDraw.Draw(f)
        for x, y, vy, vx, rot, vr, col in self.confetti:
            yy = y + vy * dt * 2.2
            xx = x + vx * dt + 20 * math.sin(dt * 3 + x)
            if 0 < yy < H:
                a = math.radians(rot + vr * dt)
                w, h = 9, 4
                pts = [(xx + w * math.cos(a) - h * math.sin(a), yy + w * math.sin(a) + h * math.cos(a)),
                       (xx - w * math.cos(a) - h * math.sin(a), yy - w * math.sin(a) + h * math.cos(a)),
                       (xx - w * math.cos(a) + h * math.sin(a), yy - w * math.sin(a) - h * math.cos(a)),
                       (xx + w * math.cos(a) + h * math.sin(a), yy + w * math.sin(a) - h * math.cos(a))]
                d.polygon(pts, fill=col + (255,))

    def end(self, t0, t, f):
        f.paste(self.bg["end"])
        self.starfield(f, t, GOLD)
        dt = t - t0
        paste(f, text_layer("BHARGAVI RENGARAJAN", ANTON, 96, WHITE, depth=8, shadow=(110, 30, 140)), W / 2, 250,
              scale=ease_out_back(dt * 2))
        a = smooth((dt - 0.4) * 2)
        paste(f, text_layer("bhargavirengarajan21@gmail.com", INTER_M, 40, GOLD), W / 2, 380, alpha=a)
        paste(f, text_layer("linkedin.com/in/bhargavi-r21", INTER_M, 34, WHITE), W / 2, 440, alpha=a)
        paste(f, text_layer("github.com/bhargavirengarajan21", INTER_M, 34, WHITE), W / 2, 492, alpha=a)
        paste(f, text_layer("thanks for watching ♥", INTER_L, 26, (200, 180, 240)), W / 2, 575, alpha=smooth((dt - 1) * 2))
        self.confetti_rain(f, dt + 6)


@lru_cache(maxsize=16)
def card_layer(title: str, line1: str, line2: str) -> Image.Image:
    cw, ch = 980, 330
    img = Image.new("RGBA", (cw + 24, ch + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, cw + 16, ch + 16), radius=34, fill=(40, 18, 60, 180))
    d.rounded_rectangle((0, 0, cw, ch), radius=34, fill=(255, 255, 255, 255), outline=GOLD + (255,), width=6)
    t = text_layer(title, ANTON, 92, PINK, depth=5, shadow=(120, 60, 160), max_w=cw - 80)
    img.alpha_composite(t, (int(cw / 2 - t.width / 2), 34))
    l1 = text_layer(line1, INTER_M, 38, INK, max_w=cw - 80)
    img.alpha_composite(l1, (int(cw / 2 - l1.width / 2), 175))
    l2 = text_layer(line2, INTER_L, 32, (110, 70, 150), max_w=cw - 80)
    img.alpha_composite(l2, (int(cw / 2 - l2.width / 2), 245))
    return img


@lru_cache(maxsize=64)
def chip_layer(word: str, color: tuple) -> Image.Image:
    w, h = 268, 92
    img = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, w + 8, h + 8), radius=24, fill=(10, 5, 25, 200))
    d.rounded_rectangle((0, 0, w, h), radius=24, fill=(30, 18, 60, 255), outline=color + (255,), width=4)
    t = text_layer(word, ANTON, 50, color, max_w=w - 30)
    img.alpha_composite(t, (int(w / 2 - t.width / 2), int(h / 2 - t.height / 2)))
    return img


@lru_cache(maxsize=8)
def badge_layer(text: str) -> Image.Image:
    t = text_layer(text, ANTON, 38, INK)
    w, h = t.width + 30, t.height + 14
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, w + 6, h + 6), radius=16, fill=(40, 18, 60, 160))
    d.rounded_rectangle((0, 0, w, h), radius=16, fill=GOLD + (255,), outline=(205, 140, 30, 255), width=4)
    img.alpha_composite(t, (15, 7))
    return img


ORDER = ["intro", "name", "experience", "numbers", "skills", "testimonials", "awards", "finale", "end"]


def render_frame(sc: Scenes, t: float, hits: list[float]) -> Image.Image:
    f = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    current = "end"
    for name in ORDER:
        a, b = scene_time(name)
        if a <= t < b:
            current = name
            break
    t0 = scene_time(current)[0]
    if current == "intro":
        sc.intro(t, f)
    else:
        getattr(sc, current)(t0, t, f)

    # camera punch on hits
    since = min((t - h for h in hits if h <= t), default=9)
    if since < 0.25:
        k = 1 + 0.04 * math.exp(-since * 14)
        big = f.resize((int(W * k), int(H * k)), Image.BILINEAR)
        x, y = (big.width - W) // 2, (big.height - H) // 2
        f = big.crop((x, y, x + W, y + H))

    # star wipe into each scene change
    for name in ORDER[1:]:
        boundary = scene_time(name)[0]
        if 0 < boundary - t < 0.22:
            p = 1 - (boundary - t) / 0.22
            draw_star(f, W / 2, H / 2, 40 + p * 1100, GOLD, 255, rot=-90 + p * 90)
        if 0 <= t - boundary < 0.12:
            flash = int(255 * (1 - (t - boundary) / 0.12) * 0.8)
            f.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, flash)))

    # fade in / out
    total = scene_time("end")[1] + 2.5
    fade = smooth(t / 0.4) * smooth((total - t) / 0.8)
    if fade < 1:
        f.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - fade)))))
    return f.convert("RGB")


def make_poster(frame: Image.Image) -> None:
    im = frame.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(INTER_M, 24)
    txt = "PLAY MY VIDEO RÉSUMÉ  ·  SOUND ON"
    tw = d.textlength(txt, font=f)
    r, gap, cy = 32, 18, H - 92
    total = 2 * r + gap + tw
    x0 = (W - total) / 2
    d.rounded_rectangle((x0 - 18, cy - r - 10, x0 + total + 24, cy + r + 10), radius=r + 10,
                        fill=(40, 18, 60, 225), outline=GOLD + (255,), width=3)
    cx = x0 + r
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PINK + (255,))
    d.polygon([(cx - 9, cy - 16), (cx - 9, cy + 16), (cx + 17, cy)], fill=WHITE + (255,))
    d.text((x0 + 2 * r + gap, cy - 15), txt, font=f, fill=WHITE + (255,))
    ASSETS.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(im, ov).convert("RGB").save(ASSETS / "poster.jpg", quality=86, optimize=True)
    frame.save(MEDIA / "resume-poster.jpg", quality=86, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    audio, ev = S.compose()
    total = len(audio) / S.SR
    hits = sorted(ev["hits"])
    sc = Scenes()

    if args.preview:
        for t in (10.5, 16.0, 20.4, 22.0, 24.0):
            render_frame(sc, t, hits).save(f"/tmp/rv_{t:05.2f}.png")
        return

    MEDIA.mkdir(parents=True, exist_ok=True)
    wav_path = Path("/tmp/resume_audio.wav")
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(S.SR)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(wav_path), "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
         str(MEDIA / "resume.mp4")],
        stdin=subprocess.PIPE,
    )
    poster_t = scene_time("name")[0] + 1.3
    for fi in range(int(total * FPS)):
        t = fi / FPS
        frame = render_frame(sc, t, hits)
        if abs(t - poster_t) < 0.5 / FPS:
            make_poster(frame)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    print("wrote", MEDIA / "resume.mp4")


if __name__ == "__main__":
    main()
