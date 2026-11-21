"""Original score for the video résumé: an over-the-top 80s power-pop anthem.

E major, 128 BPM, I-V-vi-IV. Everything is synthesised in NumPy (helpers come
from the trailer's music module): gated-reverb snares, octave bass, square
arpeggios, orchestra-hit stabs on every title card, a bell "ding" per stat,
a blip per skill, a riser into the finale and a big final hit.

Sections line up with the video scenes (one bar = 1.875 s); SCENES maps them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "intro"))
import music as M  # noqa: E402  (synth helpers)

SR = M.SR
BPM = 128
BEAT = 60 / BPM
BAR = BEAT * 4

# scene name -> (first bar, number of bars)
SCENES = {
    "intro": (0, 2),
    "name": (2, 2),
    "experience": (4, 4),
    "numbers": (8, 3),
    "skills": (11, 2),
    "testimonials": (13, 6),
    "awards": (19, 3),
    "finale": (22, 3),
    "end": (25, 2),
}
TOTAL_BARS = 27
LENGTH = TOTAL_BARS * BAR

CHORDS = [[52, 56, 59], [47, 51, 54], [49, 52, 56], [45, 49, 52]]  # E B C#m A
rng = np.random.default_rng(128)


def t_axis(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def square(freq: float, sec: float, harmonics: int = 15) -> np.ndarray:
    t = t_axis(sec)
    out = np.zeros_like(t)
    for k in range(1, harmonics * 2, 2):
        if freq * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * freq * k * t) / k
    return out


def bell(freq: float, sec: float = 1.2) -> np.ndarray:
    t = t_axis(sec)
    partials = [(1, 1.0), (2.76, 0.5), (5.4, 0.25), (8.93, 0.12)]
    return sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * (3 + r)) for r, a in partials)


def orch_hit(root: int = 52, sec: float = 1.1) -> np.ndarray:
    t = t_axis(sec)
    tone = sum(M.saw(M.hz(root + o), sec, 30, 0.01) for o in (-12, 0, 7, 12, 19, 24))
    noise = rng.uniform(-1, 1, len(t)) * np.exp(-t * 30) * 0.8
    env = np.exp(-t * 5.5)
    return np.tanh((M.onepole_fast(tone, 3500) * 0.5 + noise) * env * 1.6)


def crash(sec: float = 2.4) -> np.ndarray:
    t = t_axis(sec)
    n = rng.uniform(-1, 1, len(t))
    n = n - M.onepole_fast(n, 5000)
    return n * np.exp(-t * 2.2)


def hat(sec: float = 0.08) -> np.ndarray:
    t = t_axis(sec)
    n = rng.uniform(-1, 1, len(t))
    n = n - M.onepole_fast(n, 7000)
    return n * np.exp(-t * 60)


def gated_snare() -> np.ndarray:
    s = M.snare(0.5)
    wet = M.reverb(np.pad(s, (0, int(SR * 0.4))), 0.8, 0.7, 9)
    gate = np.ones(len(wet))
    cut = int(SR * 0.22)
    gate[cut:] = 0
    gate[cut - 400 : cut] = np.linspace(1, 0, 400)
    return wet * gate


def compose() -> tuple[np.ndarray, dict]:
    n = int((LENGTH + 2.5) * SR)
    drums, bass, synth, fx = (np.zeros(n) for _ in range(4))
    hits: list[float] = []
    ev: dict = {"hits": hits, "beats": [i * BEAT for i in range(TOTAL_BARS * 4)]}

    def add(buf, sig, start, gain=1.0):
        M.add(buf, sig, start, gain)

    snare_s = gated_snare()
    kick_s = M.kick(0.5)

    def bars(name):
        a, b = SCENES[name]
        return range(a, a + b)

    full = set(bars("name")) | set(bars("experience")) | set(bars("numbers")) | set(bars("skills")) | set(bars("finale"))
    light = set(bars("testimonials"))
    build = set(bars("awards"))

    for bar in range(TOTAL_BARS - 2):
        b0 = bar * BAR
        chord = CHORDS[bar % 4]
        root = chord[0] - 24
        # pad everywhere except the end
        pad = sum(M.saw(M.hz(m), BAR + 0.3, 14, 0.008) for m in chord)
        pad = M.onepole_fast(pad, 1800 if bar in full else 1100) * M.env_adsr(len(pad), 0.08, 0.2, 0.8, 0.4)
        add(synth, pad, b0, 0.09 if bar in full else 0.07)
        # square arpeggio (16ths)
        if bar >= 1:
            arp = [0, 1, 2, 1] * 4
            for k, idx in enumerate(arp):
                note = chord[idx] + 12 + (12 if k % 8 == 6 else 0)
                tone = square(M.hz(note), BEAT / 4) * M.env_adsr(int(SR * BEAT / 4), 0.002, 0.05, 0.4, 0.04)
                add(synth, tone, b0 + k * BEAT / 4, 0.05)
        if bar in full or bar in build:
            # octave bass eighths
            for k in range(8):
                note = root + (12 if k % 2 else 0)
                tone = M.saw(M.hz(note), BEAT / 2, 12) * M.env_adsr(int(SR * BEAT / 2), 0.004, 0.08, 0.6, 0.05)
                add(bass, M.onepole_fast(tone, 900), b0 + k * BEAT / 2, 0.22)
        if bar in full:
            for beat in range(4):
                add(drums, kick_s, b0 + beat * BEAT, 0.75)
            for beat in (1, 3):
                add(drums, snare_s, b0 + beat * BEAT, 0.5)
            for k in range(16):
                add(drums, hat(), b0 + k * BEAT / 4, 0.12 if k % 2 else 0.2)
        if bar in light:
            for beat in (0, 2.5):
                add(drums, kick_s, b0 + beat * BEAT, 0.6)
            for beat in (1, 3):
                add(drums, snare_s, b0 + beat * BEAT, 0.35)
            for k in range(4):
                tone = M.saw(M.hz(root), BEAT, 12) * M.env_adsr(int(SR * BEAT), 0.004, 0.1, 0.6, 0.1)
                add(bass, M.onepole_fast(tone, 700), b0 + k * BEAT, 0.2)
            for k in range(8):
                add(drums, hat(), b0 + k * BEAT / 2, 0.1)

    # build: snare roll + riser into the finale
    sb, _ = SCENES["awards"]
    pos = sb * BAR
    end = SCENES["finale"][0] * BAR
    while pos < end - BEAT / 4:
        prog = (pos - sb * BAR) / (end - sb * BAR)
        add(drums, M.snare(0.25), pos, 0.1 + 0.35 * prog)
        pos += BEAT / 2 if prog < 0.5 else BEAT / 4 if prog < 0.8 else BEAT / 8
    rt = t_axis(end - sb * BAR)
    f = 300 * (6 ** (rt / rt[-1]))
    riser = (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + M.onepole_fast(rng.uniform(-1, 1, len(rt)), 6000) * 0.3) * (rt / rt[-1]) ** 2
    add(fx, riser, sb * BAR, 0.8)

    # orchestra hits + crashes on scene changes and card downbeats
    def stab(at, root=52, gain=0.55, with_crash=False):
        add(fx, orch_hit(root), at, gain)
        if with_crash:
            add(fx, crash(), at, 0.35)
        hits.append(at)

    stab(0.0, 52, 0.5)
    stab(BAR, 47, 0.45)
    stab(SCENES["name"][0] * BAR, 52, 0.7, True)
    for bar in bars("experience"):
        stab(bar * BAR, CHORDS[bar % 4][0], 0.45, bar == SCENES["experience"][0])
    nb, _ = SCENES["numbers"]
    stab(nb * BAR, CHORDS[nb % 4][0], 0.45, True)
    for row in range(4):  # arcade "ding" as each high score locks in
        at = nb * BAR + (row * 2 + 1.5) * BEAT
        add(fx, square(M.hz(88 + row * 2), 0.18) * np.exp(-t_axis(0.18) * 14), at, 0.18)
        add(fx, bell(M.hz(88 + row * 2)), at, 0.14)
        hits.append(at)
    for k in range(16):  # a blip as each skill chip pops in (triplets)
        at = SCENES["skills"][0] * BAR + k * BEAT / 3
        add(fx, square(M.hz([76, 80, 83, 88][k % 4]), 0.12) * np.exp(-t_axis(0.12) * 25), at, 0.16)
        hits.append(at)
    stab(SCENES["skills"][0] * BAR, 52, 0.5, True)
    tb, tn = SCENES["testimonials"]
    for q in range(3):  # a bell as each recommendation appears
        add(fx, bell(M.hz(83)), (tb + q * tn / 3) * BAR, 0.2)
    ab, _ = SCENES["awards"]
    stab(ab * BAR, 52, 0.55, True)
    for k in range(4):
        add(fx, bell(M.hz(83 + k * 2)), (ab + 1) * BAR + k * BEAT * 1.5, 0.16)
    stab(SCENES["finale"][0] * BAR, 52, 0.8, True)
    final = SCENES["end"][0] * BAR
    stab(final, 40, 0.9, True)
    add(drums, M.kick(1.5, big=True), final, 0.9)
    tail = sum(M.saw(M.hz(m), 3.0, 25, 0.01) for m in (40, 52, 56, 59, 64))
    tail = np.tanh(M.onepole_fast(tail, 2600) * 1.2) * M.env_adsr(int(3.0 * SR), 0.01, 0.4, 0.5, 2.2)
    add(synth, tail, final, 0.35)

    # lead melody on the name drop and the finale (original)
    phrase = [
        (68, 1), (71, 0.5), (73, 0.5), (76, 1), (75, 0.5), (73, 0.5),
        (71, 1.5), (68, 0.5), (66, 1), (71, 1),
        (73, 1), (76, 0.5), (78, 0.5), (80, 1.5), (78, 0.5),
        (76, 1), (73, 1), (76, 2),
    ]

    def lead(start, notes):
        pos = start
        for note, beats in notes:
            dur = beats * BEAT
            lt = t_axis(dur + 0.15)
            vib = 1 + np.sin(2 * np.pi * 6 * lt) * 0.005 * np.minimum(1, lt / 0.2)
            ph = 2 * np.pi * np.cumsum(M.hz(note) * vib) / SR
            tone = sum(np.sin(ph * k) / k for k in range(1, 16)) + 0.6 * sum(np.sin(ph * k) / k for k in range(1, 12, 2))
            tone = M.onepole_fast(tone, 4200) * M.env_adsr(len(lt), 0.01, 0.1, 0.7, 0.12)
            add(synth, tone, pos, 0.13)
            pos += dur

    lead(SCENES["name"][0] * BAR, phrase[:10])
    lead(SCENES["finale"][0] * BAR, phrase)

    left = M.reverb(synth, 1.8, 0.25, 1) + M.reverb(drums, 1.0, 0.12, 3) + bass + M.reverb(fx, 2.2, 0.3, 5)
    right = M.reverb(synth, 1.8, 0.25, 2) + M.reverb(drums, 1.0, 0.12, 4) + bass + M.reverb(fx, 2.2, 0.3, 6)
    stereo = np.tanh(np.stack([left, right], axis=1) * 1.15)
    stereo /= np.max(np.abs(stereo)) or 1
    stereo *= 0.89
    fade = int(1.2 * SR)
    stereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return stereo, ev


if __name__ == "__main__":
    import wave

    a, ev = compose()
    pcm = (a * 32767).astype("<i2")
    with wave.open("/tmp/resume_score.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{len(a) / SR:.1f}s", len(ev["hits"]), "hits")
