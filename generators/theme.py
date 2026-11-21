"""Shared palette and SVG helpers for every generated asset.

Two variants of each image are rendered ("dark" and "light"); the README picks
one with <picture> + prefers-color-scheme. The palette is a sakura/neon theme:
deep plum night for dark mode, soft blush paper for light mode.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

FONT = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'Fira Code', 'SFMono-Regular', Consolas, monospace"

PALETTES = {
    "dark": {
        "bg": "#14101f",
        "bg2": "#1d1630",
        "panel": "#241b3a",
        "grid": "#33284f",
        "text": "#f4ecff",
        "muted": "#a99cc7",
        "pink": "#ff66cc",
        "violet": "#9d7bff",
        "cyan": "#5ce1e6",
        "gold": "#ffd36e",
        "window_off": "#2c2344",
        "water": "#191230",
    },
    "light": {
        "bg": "#fff7fb",
        "bg2": "#fbeaf5",
        "panel": "#ffffff",
        "grid": "#ecd6e8",
        "text": "#2a1b3d",
        "muted": "#7c6a93",
        "pink": "#e0349f",
        "violet": "#6b4fd8",
        "cyan": "#0f9fb0",
        "gold": "#d99a00",
        "window_off": "#e9dcef",
        "water": "#f3e4f3",
    },
}

MODES = ("dark", "light")


def esc(text: str) -> str:
    return escape(str(text), quote=True)


def svg_open(width: int, height: int, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title>"
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = content.strip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == new:
        return
    path.write_text(new, encoding="utf-8")


def gradient(gid: str, p: dict, vertical: bool = False) -> str:
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
        f'<stop offset="0" stop-color="{p["pink"]}"/>'
        f'<stop offset="1" stop-color="{p["violet"]}"/></linearGradient>'
    )
