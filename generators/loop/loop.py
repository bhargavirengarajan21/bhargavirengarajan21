"""The gesture loop: a 16-step sequencer that visitors play with hand gestures.

A nod to my hand-gesture music player: every gesture is a note. Visitors open
an issue titled "gesture: <name>", a workflow drops that note on the next free
step (wrapping around and overwriting once the loop is full), then re-renders
the piano roll, a WAV, a MIDI file and the header waveform.

The scale is C major pentatonic over two octaves, so any combination of
gestures sounds pleasant. Audio is synthesised with a Karplus-Strong plucked
string in NumPy and written with the standard-library ``wave`` module. The MIDI
file is written byte by byte. No audio libraries, no external services.
"""
from __future__ import annotations

import json
import struct
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from theme import ASSETS, FONT, MODES, PALETTES, esc, gradient, svg_open, write  # noqa: E402

HERE = Path(__file__).resolve().parent
STATE = HERE / "state.json"
OUT = ASSETS / "loop"
# audio and a copy of the roll go to docs/media, served by GitHub Pages as a player
MEDIA = ASSETS.parent / "docs" / "media"

STEPS = 16
BPM = 110
STEP_SECONDS = 60 / BPM / 2  # eighth notes
RATE = 22050

# key -> (emoji, label, note name, MIDI number). Ordered high to low for the roll.
GESTURES = {
    "thumbs-up": ("👍", "thumbs up", "E5", 76),
    "rock": ("🤘", "rock on", "D5", 74),
    "ok": ("👌", "ok", "C5", 72),
    "open-hand": ("🖐️", "open hand", "A4", 69),
    "love-you": ("🤟", "love you (ASL)", "G4", 67),
    "peace": ("✌️", "peace", "E4", 64),
    "point": ("☝️", "point", "D4", 62),
    "fist": ("✊", "fist", "C4", 60),
}
REST = "stop"
REST_EMOJI = "✋"
VALID = set(GESTURES) | {REST}


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def place(state: dict, gesture: str, user: str) -> int:
    """Put a gesture on the next free step and return the step index (0-based)."""
    if gesture not in VALID:
        raise ValueError(f"unknown gesture: {gesture}")
    steps = state["steps"]
    step = state.get("next", 0) % STEPS
    steps[step] = gesture
    free = [i for i, s in enumerate(steps) if s is None]
    later = [i for i in free if i > step]
    state["next"] = (later or free or [(step + 1) % STEPS])[0]
    state.setdefault("history", []).append(
        {
            "user": user,
            "gesture": gesture,
            "step": step + 1,
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    state["history"] = state["history"][-50:]
    return step


# ----------------------------------------------------------------- audio ----

def midi_to_hz(n: int) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def pluck(freq: float, seconds: float, seed: int) -> np.ndarray:
    """Karplus-Strong plucked string."""
    n = int(RATE * seconds)
    period = max(2, int(RATE / freq))
    rng = np.random.default_rng(seed)
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        j = i % period
        out[i] = buf[j]
        buf[j] = 0.996 * 0.5 * (buf[j] + buf[(j + 1) % period])
    return out


def synthesize(state: dict, loops: int = 2) -> np.ndarray:
    step_len = int(RATE * STEP_SECONDS)
    total = step_len * STEPS * loops + int(RATE * 1.5)
    mix = np.zeros(total)
    ring = STEP_SECONDS * 3
    for loop in range(loops):
        for i, g in enumerate(state["steps"]):
            if g is None or g == REST:
                continue
            note = pluck(midi_to_hz(GESTURES[g][3]), ring, seed=i * 31 + GESTURES[g][3])
            start = (loop * STEPS + i) * step_len
            mix[start : start + len(note)] += note * 0.55
    # soft dotted-eighth echo
    d = int(RATE * STEP_SECONDS * 1.5)
    echo = np.zeros_like(mix)
    echo[d:] = mix[:-d] * 0.32
    mix += echo
    peak = np.max(np.abs(mix)) or 1.0
    return mix / peak * 0.85


def write_wav(samples: np.ndarray, path: Path) -> None:
    pcm = (samples * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def _varlen(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def write_midi(state: dict, path: Path) -> None:
    tpq = 480
    eighth = tpq // 2
    events = bytearray()
    tempo = int(60_000_000 / BPM)
    events += b"\x00\xff\x51\x03" + tempo.to_bytes(3, "big")
    events += b"\x00\xc0\x18"  # program: nylon guitar
    wait = 0
    for g in state["steps"]:
        if g is None or g == REST:
            wait += eighth
            continue
        n = GESTURES[g][3]
        events += _varlen(wait) + bytes([0x90, n, 96])
        events += _varlen(eighth) + bytes([0x80, n, 0])
        wait = 0
    events += _varlen(wait) + b"\xff\x2f\x00"
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, tpq)
    track = b"MTrk" + struct.pack(">I", len(events)) + bytes(events)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + track)


# ------------------------------------------------------------ piano roll ----

def render_roll(state: dict, mode: str) -> str:
    p = PALETTES[mode]
    W, H = 960, 430
    left, top = 190, 58
    cw, ch = 46, 36
    rows = list(GESTURES)
    roll_w, roll_h = cw * STEPS, ch * len(rows)
    rest_y = top + roll_h + 10
    loop_s = STEP_SECONDS * STEPS
    nxt = state.get("next", 0)

    s = [svg_open(W, H, "Gesture loop: a 16-step sequencer that visitors play with hand gestures")]
    s.append(
        "<defs>"
        + gradient("g", p)
        + f"""<style>
        .ph{{animation:sweep {loop_s:.3f}s steps({STEPS}) infinite}}
        @keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({roll_w}px)}}}}
        .nx{{animation:blink 1.4s ease-in-out infinite}}
        @keyframes blink{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
        </style></defs>"""
    )
    s.append(f'<rect width="{W}" height="{H}" rx="18" fill="{p["bg"]}"/>')
    s.append(
        f'<text x="{left}" y="34" font-family="{FONT}" font-size="15" fill="{p["muted"]}">'
        f"C major pentatonic · {BPM} BPM · 16 steps · loops forever</text>"
    )
    # row labels and lanes
    for r, key in enumerate(rows):
        emoji, label, note, _ = GESTURES[key]
        y = top + r * ch
        fill = p["bg2"] if r % 2 == 0 else p["bg"]
        s.append(f'<rect x="{left}" y="{y}" width="{roll_w}" height="{ch}" fill="{fill}"/>')
        s.append(f'<text x="22" y="{y + 24}" font-size="19">{emoji}</text>')
        s.append(
            f'<text x="54" y="{y + 23}" font-family="{FONT}" font-size="14" fill="{p["text"]}">{esc(label)}</text>'
        )
        s.append(
            f'<text x="{left - 12}" y="{y + 23}" text-anchor="end" font-family="{FONT}" font-size="12" '
            f'fill="{p["muted"]}">{note}</text>'
        )
    # rest lane
    s.append(f'<text x="22" y="{rest_y + 22}" font-size="19">{REST_EMOJI}</text>')
    s.append(
        f'<text x="54" y="{rest_y + 21}" font-family="{FONT}" font-size="14" fill="{p["text"]}">stop (rest)</text>'
    )
    s.append(
        f'<rect x="{left}" y="{rest_y}" width="{roll_w}" height="30" rx="6" fill="{p["bg2"]}"/>'
    )
    # grid lines
    for c in range(STEPS + 1):
        x = left + c * cw
        sw = 2 if c % 4 == 0 else 1
        s.append(
            f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + roll_h}" stroke="{p["grid"]}" stroke-width="{sw}"/>'
        )
    for c in range(STEPS):
        s.append(
            f'<text x="{left + c * cw + cw / 2}" y="{top + roll_h + 70}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="12" fill="{p["muted"]}">{c + 1}</text>'
        )
    # next-free-step marker
    nx = left + nxt * cw
    s.append(
        f'<rect class="nx" x="{nx + 2}" y="{top + 2}" width="{cw - 4}" height="{roll_h + 36}" rx="8" '
        f'fill="none" stroke="{p["gold"]}" stroke-width="2" stroke-dasharray="5 4"/>'
    )
    s.append(
        f'<text x="{nx + cw / 2}" y="{top - 8}" text-anchor="middle" font-family="{FONT}" font-size="12" '
        f'font-weight="600" fill="{p["gold"]}">next</text>'
    )
    # notes
    for c, g in enumerate(state["steps"]):
        if g is None:
            continue
        x = left + c * cw
        if g == REST:
            s.append(
                f'<rect x="{x + 5}" y="{rest_y + 4}" width="{cw - 10}" height="22" rx="6" fill="{p["muted"]}" opacity=".45"/>'
            )
            s.append(f'<text x="{x + cw / 2}" y="{rest_y + 21}" text-anchor="middle" font-size="14">{REST_EMOJI}</text>')
            continue
        r = rows.index(g)
        y = top + r * ch
        s.append(f'<rect x="{x + 4}" y="{y + 4}" width="{cw - 8}" height="{ch - 8}" rx="8" fill="url(#g)"/>')
        s.append(
            f'<text x="{x + cw / 2}" y="{y + 24}" text-anchor="middle" font-size="16">{GESTURES[g][0]}</text>'
        )
    # playhead
    s.append(
        f'<g class="ph"><rect x="{left}" y="{top}" width="{cw}" height="{roll_h + 40}" fill="{p["cyan"]}" opacity=".13"/>'
        f'<rect x="{left}" y="{top}" width="2" height="{roll_h + 40}" fill="{p["cyan"]}"/></g>'
    )
    filled = sum(1 for x in state["steps"] if x is not None)
    s.append(
        f'<text x="{W - 24}" y="34" text-anchor="end" font-family="{FONT}" font-size="15" fill="{p["text"]}" '
        f'font-weight="600">{filled}/{STEPS} steps filled</text>'
    )
    s.append("</svg>")
    return "".join(s)


def credits(state: dict) -> str:
    filled = sum(1 for x in state["steps"] if x is not None)
    hist = state.get("history", [])
    visitors = [h for h in hist if h["user"] != state.get("owner")]
    recent = []
    for h in reversed(hist):
        if h["user"] not in recent:
            recent.append(h["user"])
        if len(recent) == 5:
            break
    line = f"<strong>{filled}/{STEPS} steps filled</strong> · next free step: {state.get('next', 0) + 1} · {len(visitors)} gesture{'' if len(visitors) == 1 else 's'} from visitors"
    if recent:
        names = ", ".join(f'<a href="https://github.com/{esc(u)}">@{esc(u)}</a>' for u in recent)
        line += f"<br><sub>recent players: {names}</sub>"
    if hist:
        h = hist[-1]
        e = GESTURES[h["gesture"]][0] if h["gesture"] in GESTURES else REST_EMOJI
        line += f"<br><sub>latest: @{esc(h['user'])} played {e} {esc(h['gesture'])} on step {h['step']}</sub>"
    return line


def render(state: dict) -> np.ndarray:
    for mode in MODES:
        roll = render_roll(state, mode)
        write(OUT / f"loop-{mode}.svg", roll)
        write(MEDIA / f"loop-{mode}.svg", roll)
    samples = synthesize(state)
    write_wav(samples, MEDIA / "loop.wav")
    (MEDIA / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_midi(state, OUT / "loop.mid")
    return samples
