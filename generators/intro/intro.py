"""Cinematic intro video for the README: original score + audio-reactive titles.

    python generators/intro/intro.py            -> docs/media/intro.mp4 + poster
    python generators/intro/intro.py --preview  -> a few still frames in /tmp

GitHub's file viewer can't play an 8 MB video, so the MP4 lives in docs/media
and plays on the GitHub Pages player (docs/index.html). To also play it inline
in the README, drag docs/media/intro.mp4 into the README editor on github.com.
Needs ffmpeg.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import music  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "assets" / "intro"
MEDIA = ROOT / "docs" / "media"
FONTS = HERE / "fonts"

W, H, FPS = 1280, 720, 30
BAR_H = 64  # letterbox
PINK = np.array([255, 102, 204], dtype=np.float32)
VIOLET = np.array([157, 123, 255], dtype=np.float32)
CYAN = np.array([92, 225, 230], dtype=np.float32)
TEXT = (244, 236, 255)
MUTED = (169, 156, 199)

ANTON = str(FONTS / "Anton-Regular.ttf")
LIGHT = str(FONTS / "Inter-Light.otf")
MEDIUM = str(FONTS / "Inter-Medium.otf")

DROP = 10 * music.BAR          # 20.0 s
FINAL = 16 * music.BAR         # 32.0 s

CARDS = [  # start, end, kicker, line
    (0.8, 3.8, None, "every engineer has an origin story"),
    (4.0, 7.7, "2018", "a music player that listens to your hands"),
    (7.9, 11.7, "2020", "Mr. Cooper  ·  shipping fintech to production"),
    (11.9, 15.7, "2023", "UC Riverside  ·  M.S. Computer Engineering"),
    (15.9, 19.4, "2025", "Rocket Mortgage  ·  AI agents that answer the 2 a.m. page"),
]
TAGLINES = [
    (23.2, 26.2, "FULL-STACK  &  AI  ENGINEER"),
    (26.2, 29.2, "JAVA  ·  SPRING BOOT  ·  REACT  ·  NODE.JS"),
    (29.2, 32.0, "CLAUDE SDK  ·  MCP  ·  RAG"),
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def fade_window(t: float, start: float, end: float, fin: float = 0.6, fout: float = 0.5) -> float:
    if t < start or t > end:
        return 0.0
    return smooth((t - start) / fin) * smooth((end - t) / fout)


# --------------------------------------------------------------- statics ----

def background() -> np.ndarray:
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H * 0.45
    d = np.sqrt(((x - cx) / W) ** 2 + ((y - cy) / H) ** 2)
    base = np.array([20, 16, 31], np.float32)
    glow = np.array([70, 40, 110], np.float32)
    k = np.clip(1 - d * 1.9, 0, 1)[..., None] ** 2
    img = base + (glow - base) * k
    vign = np.clip(1.25 - d * 1.2, 0.25, 1)[..., None]
    return img * vign


def text_mask(text: str, fnt: ImageFont.FreeTypeFont, spacing: int = 0) -> Image.Image:
    if spacing:
        widths = [fnt.getbbox(ch)[2] - fnt.getbbox(ch)[0] if ch != " " else fnt.size // 3 for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
    else:
        b = fnt.getbbox(text)
        total = b[2] - b[0]
    asc, desc = fnt.getmetrics()
    m = Image.new("L", (int(total) + 40, asc + desc + 20), 0)
    d = ImageDraw.Draw(m)
    if spacing:
        x = 20
        for ch, w in zip(text, widths):
            d.text((x, 10), ch, font=fnt, fill=255)
            x += w + spacing
    else:
        d.text((20 - fnt.getbbox(text)[0], 10), text, font=fnt, fill=255)
    return m.crop(m.getbbox()) if m.getbbox() else m


def gradient_fill(size: tuple[int, int]) -> np.ndarray:
    w, h = size
    k = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    return np.broadcast_to(PINK + (VIOLET - PINK) * k, (h, w, 3))


class Frame:
    def __init__(self, base: np.ndarray):
        self.img = base.copy()

    def paste(self, mask: Image.Image, cx: float, cy: float, color, alpha: float, scale: float = 1.0) -> None:
        if alpha <= 0.003:
            return
        if scale != 1.0:
            mask = mask.resize((max(1, int(mask.width * scale)), max(1, int(mask.height * scale))), Image.LANCZOS)
        m = np.asarray(mask, np.float32)[..., None] / 255 * alpha
        h, w = m.shape[:2]
        if isinstance(color, np.ndarray) and color.ndim == 3 and color.shape[:2] != (h, w):
            img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
            color = np.asarray(img, np.float32)
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        xs, ys = max(0, x0), max(0, y0)
        xe, ye = min(W, x0 + w), min(H, y0 + h)
        if xs >= xe or ys >= ye:
            return
        m = m[ys - y0 : ye - y0, xs - x0 : xe - x0]
        if isinstance(color, np.ndarray) and color.ndim == 3:
            c = color[ys - y0 : ye - y0, xs - x0 : xe - x0]
        else:
            c = np.array(color, np.float32)
        region = self.img[ys:ye, xs:xe]
        self.img[ys:ye, xs:xe] = region * (1 - m) + c * m

    def add_glow(self, mask: Image.Image, cx: float, cy: float, color, alpha: float, radius: int = 18) -> None:
        if alpha <= 0.01:
            return
        pad = radius * 3
        big = Image.new("L", (mask.width + pad * 2, mask.height + pad * 2), 0)
        big.paste(mask, (pad, pad))
        blur = big.filter(ImageFilter.GaussianBlur(radius))
        m = np.asarray(blur, np.float32)[..., None] / 255 * alpha
        h, w = m.shape[:2]
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        if xs >= xe or ys >= ye:
            return
        m = m[ys - y0 : ye - y0, xs - x0 : xe - x0]
        self.img[ys:ye, xs:xe] = np.minimum(255, self.img[ys:ye, xs:xe] + np.array(color, np.float32) * m)


def make_poster(frame: Image.Image) -> None:
    """Still from just after the drop, with a play button, for the README."""
    im = frame.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(MEDIUM, 22)
    txt = "PLAY THE INTRO  ·  SOUND ON"
    tw = d.textlength(txt, font=f)
    r, gap, cy = 30, 18, 478
    total = 2 * r + gap + tw
    x0 = (W - total) / 2
    d.rounded_rectangle((x0 - 16, cy - r - 8, x0 + total + 22, cy + r + 8), radius=r + 8,
                        fill=(20, 16, 31, 200), outline=(255, 102, 204, 255), width=2)
    cx = x0 + r
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 102, 204, 255))
    d.polygon([(cx - 9, cy - 15), (cx - 9, cy + 15), (cx + 16, cy)], fill=(255, 255, 255, 255))
    d.text((x0 + 2 * r + gap, cy - 14), txt, font=f, fill=(255, 255, 255, 240))
    poster = Image.alpha_composite(im, ov).convert("RGB")
    poster.save(OUT / "poster.jpg", quality=86, optimize=True)
    frame.convert("RGB").save(MEDIA / "poster.jpg", quality=86, optimize=True)  # clean still for <video poster>


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    audio, events = music.compose()
    total = len(audio) / music.SR
    n_frames = int(total * FPS)
    mono = np.abs(audio.mean(axis=1))
    hop = music.SR // FPS
    rms = np.array([np.sqrt(np.mean(mono[i * hop : (i + 1) * hop] ** 2)) for i in range(n_frames)])
    rms = rms / (rms.max() or 1)
    # spectrum bars per frame
    bands = 64
    win = 2048
    spec = np.zeros((n_frames, bands), np.float32)
    edges = np.geomspace(40, 9000, bands + 1)
    freqs = np.fft.rfftfreq(win, 1 / music.SR)
    for i in range(n_frames):
        c = i * hop
        seg = mono[c : c + win]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        mag = np.abs(np.fft.rfft(seg * np.hanning(win)))
        for b in range(bands):
            sel = (freqs >= edges[b]) & (freqs < edges[b + 1])
            spec[i, b] = mag[sel].mean() if sel.any() else 0
    spec = np.log1p(spec * 4)
    spec /= np.percentile(spec, 99.5) or 1
    spec = np.clip(spec, 0, 1)
    smoothed = spec.copy()
    for i in range(1, n_frames):
        smoothed[i] = np.maximum(spec[i], smoothed[i - 1] * 0.82)

    hits = sorted(events["hits"])
    base = background()
    rng = np.random.default_rng(3)
    grains = [rng.normal(0, 3, (H, W, 1)).astype(np.float32) for _ in range(6)]
    n_p = 140
    px, py = rng.uniform(0, W, n_p), rng.uniform(0, H, n_p)
    pv, ps = rng.uniform(4, 22, n_p), rng.uniform(1, 2.6, n_p)

    f_kicker = font(ANTON, 120)
    f_line = font(LIGHT, 36)
    f_name = font(ANTON, 168)
    f_tag = font(MEDIUM, 26)
    f_small = font(LIGHT, 24)
    card_masks = [
        (s, e, text_mask(k, f_kicker) if k else None, text_mask(l, f_line, 2)) for s, e, k, l in CARDS
    ]
    name1 = text_mask("BHARGAVI", f_name, 10)
    name2 = text_mask("RENGARAJAN", font(ANTON, 76), 22)
    tag_masks = [(s, e, text_mask(t, f_tag, 3)) for s, e, t in TAGLINES]
    end1 = text_mask("github.com/bhargavirengarajan21", font(MEDIUM, 30), 1)
    end2 = text_mask("open to full-time software & AI engineering roles", f_small, 1)
    grad_k = {id(m): gradient_fill(m.size) for _, _, m, _ in card_masks if m is not None}
    grad_n1 = gradient_fill(name1.size)

    OUT.mkdir(parents=True, exist_ok=True)
    MEDIA.mkdir(parents=True, exist_ok=True)
    wav_path = Path("/tmp/intro_audio.wav")
    pcm = (audio * 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as wv:
        wv.setnchannels(2)
        wv.setsampwidth(2)
        wv.setframerate(music.SR)
        wv.writeframes(pcm.tobytes())

    preview_times = [2.0, 5.5, 13.5, 17.5, 20.15, 21.5, 24.5, 30.0, 33.5]
    frames_to_render = [int(t * FPS) for t in preview_times] if args.preview else range(n_frames)

    proc = None
    if not args.preview:
        proc = subprocess.Popen(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                "-i", str(wav_path),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                str(MEDIA / "intro.mp4"),
            ],
            stdin=subprocess.PIPE,
        )

    for fi in frames_to_render:
        t = fi / FPS
        level = rms[min(fi, n_frames - 1)]
        since_hit = min((t - h for h in hits if h <= t), default=9)
        punch = math.exp(-since_hit * 6) if since_hit < 1.5 else 0.0
        fr = Frame(base * (0.9 + 0.25 * level))

        # drifting particles
        yy = (py - pv * t) % H
        for x, y, sz in zip(px, yy, ps):
            xi, yi = int(x), int(y)
            r = int(sz + punch * 2)
            fr.img[max(0, yi - r) : yi + r, max(0, xi - r) : xi + r] = np.minimum(
                255, fr.img[max(0, yi - r) : yi + r, max(0, xi - r) : xi + r] + PINK * 0.25 * (0.4 + level)
            )

        # spectrum ribbon, mirrored
        sp = smoothed[min(fi, n_frames - 1)]
        intensity = 0.35 if t < DROP else 0.9
        if t < 0.8:
            intensity *= t / 0.8
        cy = H / 2 + (0 if DROP - 0.5 <= t < FINAL else 150)
        if DROP <= t < FINAL:
            cy = H / 2 + 200
        bw = (W - 200) / (bands * 2)
        for b in range(bands * 2):
            v = sp[abs(b - bands) if b >= bands else bands - 1 - b]
            h = 4 + v * (120 if t >= DROP else 90) * intensity
            x0 = int(100 + b * bw)
            col = PINK + (VIOLET - PINK) * (b / (bands * 2))
            y0, y1 = int(cy - h / 2), int(cy + h / 2)
            fr.img[y0:y1, x0 : x0 + max(2, int(bw) - 3)] = (
                fr.img[y0:y1, x0 : x0 + max(2, int(bw) - 3)] * (1 - 0.8 * intensity) + col * 0.8 * intensity
            )

        # story cards
        for s, e, km, lm in card_masks:
            a = fade_window(t, s, e)
            if a <= 0:
                continue
            drift = (t - s) * 6
            if km is not None:
                fr.add_glow(km, W / 2, H / 2 - 70 - drift * 0.3, PINK, a * 0.5, 22)
                fr.paste(km, W / 2, H / 2 - 70 - drift * 0.3, grad_k[id(km)], a)
                fr.paste(lm, W / 2, H / 2 + 40 - drift * 0.3, TEXT, a * 0.95)
            else:
                fr.paste(lm, W / 2, H / 2 - 10, TEXT, a * 0.9, scale=1.0 + (t - s) * 0.02)

        # the drop: name slam with chromatic split and shake
        if DROP <= t < FINAL + 0.2:
            dt = t - DROP
            slam = 1 + 0.35 * math.exp(-dt * 9)
            shake = math.exp(-dt * 5) * 14 + punch * 4
            sx = rng.uniform(-shake, shake)
            sy = rng.uniform(-shake, shake)
            a = min(1.0, dt / 0.06)
            split = 4 + 26 * math.exp(-dt * 4) + punch * 6
            nx, ny = W / 2 + sx, H / 2 - 95 + sy
            fr.add_glow(name1, nx, ny, PINK, 0.55 + 0.4 * punch, 30)
            fr.paste(name1, nx - split, ny, CYAN, a * 0.55, slam)
            fr.paste(name1, nx + split, ny, PINK, a * 0.55, slam)
            fr.paste(name1, nx, ny, grad_n1 * 0.35 + 255 * 0.65, a, slam)
            a2 = smooth((dt - 0.5) / 0.8)
            fr.paste(name2, W / 2 + sx * 0.5, H / 2 + 25 + sy * 0.5, TEXT, a2 * 0.92)
            for s, e, m in tag_masks:
                ta = fade_window(t, s, e, 0.5, 0.4)
                fr.paste(m, W / 2, H / 2 + 95, PINK, ta)

        # end card
        if t >= FINAL:
            dt = t - FINAL
            a = smooth(dt / 0.6) * smooth((total - 0.3 - t) / 1.6)
            fr.img *= 1 - 0.75 * smooth(dt / 0.5)
            fr.add_glow(end1, W / 2, H / 2 - 10, PINK, a * 0.4, 16)
            fr.paste(end1, W / 2, H / 2 - 10, TEXT, a)
            fr.paste(end2, W / 2, H / 2 + 40, MUTED, a * 0.9)

        # flash on the drop and the final hit
        for moment, strength in ((DROP, 1.0), (FINAL, 0.8)):
            if 0 <= t - moment < 0.5:
                f = strength * math.exp(-(t - moment) * 10)
                fr.img = fr.img * (1 - f) + 255 * f

        # silence before the drop: near black
        if DROP - 0.5 <= t < DROP:
            fr.img *= 0.12

        # grain, letterbox, fade in/out
        fr.img += grains[(fi // 4) % len(grains)]
        fade = smooth(t / 0.8) * smooth((total - t) / 0.4)
        fr.img *= fade
        fr.img[:BAR_H] = 0
        fr.img[H - BAR_H :] = 0
        out = np.clip(fr.img, 0, 255).astype(np.uint8)

        if args.preview:
            Image.fromarray(out).save(f"/tmp/intro_{t:05.2f}.png")
        else:
            proc.stdin.write(out.tobytes())
            if fi == int((DROP + 1.4) * FPS):
                make_poster(Image.fromarray(out))
    if proc:
        proc.stdin.close()
        proc.wait()
        print("wrote", MEDIA / "intro.mp4")


if __name__ == "__main__":
    main()
