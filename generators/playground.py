"""Glue for the living README.

    python generators/playground.py --render-only
    python generators/playground.py --gesture "gesture: peace" --user octocat
    python generators/playground.py --refresh-history --render-only   (needs GH_TOKEN)

Rendering also rewrites the credit lines between the <!-- ...:START/END -->
markers in README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theme import ROOT  # noqa: E402
from loop import loop as L  # noqa: E402
from header import header  # noqa: E402
from skyline import skyline  # noqa: E402
from toolbox import toolbox  # noqa: E402
import social  # noqa: E402

README = ROOT / "README.md"
RATELIMIT = Path(__file__).resolve().parent / "ratelimit.json"
MAX_PER_DAY = 3

ALIASES = {
    "👍": "thumbs-up", "thumbsup": "thumbs-up", "thumbs up": "thumbs-up",
    "🤘": "rock", "rock on": "rock",
    "👌": "ok",
    "🖐": "open-hand", "🖐️": "open-hand", "open hand": "open-hand", "hand": "open-hand",
    "🤟": "love-you", "love you": "love-you", "ily": "love-you",
    "✌": "peace", "✌️": "peace",
    "☝": "point", "☝️": "point",
    "✊": "fist",
    "✋": "stop", "rest": "stop",
}


def parse_title(title: str) -> str | None:
    m = re.match(r"^\s*gesture\s*:\s*(.+?)\s*$", title or "", re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip().lower()
    key = ALIASES.get(raw, raw.replace(" ", "-"))
    return key if key in L.VALID else None


def allowed(user: str, owner: str) -> bool:
    if user == owner:
        return True
    data = json.loads(RATELIMIT.read_text()) if RATELIMIT.exists() else {}
    now = datetime.now(timezone.utc)
    recent = [t for t in data.get(user, []) if now - datetime.fromisoformat(t) < timedelta(days=1)]
    if len(recent) >= MAX_PER_DAY:
        return False
    recent.append(now.isoformat(timespec="seconds"))
    data = {u: ts for u, ts in data.items() if ts and u != user}
    data[user] = recent
    RATELIMIT.write_text(json.dumps(data, indent=1) + "\n")
    return True


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def render_everything() -> None:
    state = L.load_state()
    samples = L.render(state)
    header.render_all(samples, state)
    hist = skyline.load()
    skyline.render_all(hist)
    toolbox.render_all()
    social.render_all()
    if README.exists():
        text = README.read_text(encoding="utf-8")
        text = replace_block(text, "LOOP:CREDITS", L.credits(state))
        text = replace_block(text, "SKYLINE:CREDITS", skyline.credits(hist))
        README.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gesture", help='issue title, e.g. "gesture: peace"')
    ap.add_argument("--user", default="anonymous")
    ap.add_argument("--refresh-history", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--result-file", help="where to write a short result message for the issue reply")
    args = ap.parse_args()

    message = ""
    if args.refresh_history:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GH_TOKEN is required for --refresh-history", file=sys.stderr)
            return 1
        try:
            skyline.refresh(token)
        except Exception as exc:  # keep rendering with the cached history
            print(f"skyline refresh failed, using cached history: {exc}", file=sys.stderr)

    if args.gesture is not None:
        key = parse_title(args.gesture)
        state = L.load_state()
        user = re.sub(r"[^A-Za-z0-9-]", "", args.user)[:39] or "anonymous"
        if key is None:
            message = "I couldn't read that gesture. Use one of the links in the README, for example `gesture: peace`."
        elif not allowed(user, state.get("owner", "")):
            message = f"Thanks @{user}! You've already played {MAX_PER_DAY} gestures today. Come back tomorrow for more. 🎶"
        else:
            step = L.place(state, key, user)
            L.save_state(state)
            emoji = L.GESTURES[key][0] if key in L.GESTURES else L.REST_EMOJI
            message = (
                f"{emoji} Played **{key}** on step {step + 1}. Thanks for jamming, @{user}! "
                "The piano roll, header waveform, WAV and MIDI refresh in a minute."
            )

    render_everything()
    if args.result_file and message:
        Path(args.result_file).write_text(message + "\n", encoding="utf-8")
    if message:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
