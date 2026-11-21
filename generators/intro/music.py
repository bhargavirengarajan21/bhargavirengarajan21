"""Original cinematic score for the profile intro ("Signal", D minor, 120 BPM).

Everything is synthesised from scratch in NumPy: drones, a plucked ostinato,
taiko-style drums, a riser, a low brass hit on the drop and a saw lead.
No samples, no audio libraries.

Structure (one bar = 2 s):
  bars 0-1   drone swell
  bars 2-7   ostinato + taiko pulse
  bars 8-9   build: snare roll + riser, then half a beat of silence
  bars 10-15 drop: brass hit, full drums, lead melody
  bar  16    final hit and tail
"""
from __future__ import annotations

import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
LENGTH = 17 * BAR + 2.0

CHORDS = {  # root MIDI notes per bar, i - VI - III - VII in D minor
    "Dm": [50, 53, 57], "Bb": [46, 50, 53], "F": [53, 57, 60], "C": [48, 52, 55],
}
PROGRESSION = ["Dm", "Bb", "F", "C"]

rng = np.random.default_rng(2026)


def hz(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def t_axis(seconds: float) -> np.ndarray:
    return np.arange(int(SR * seconds)) / SR


def env_adsr(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate([
        np.linspace(0, 1, max(a_n, 1)),
        np.linspace(1, s, max(d_n, 1)),
        np.full(s_n, s),
        np.linspace(s, 0, max(r_n, 1)),
    ])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw(freq: float, seconds: float, harmonics: int = 24, detune: float = 0.0) -> np.ndarray:
    t = t_axis(seconds)
    out = np.zeros_like(t)
    for f in (freq, freq * (1 + detune), freq * (1 - detune)) if detune else (freq,):
        for k in range(1, harmonics + 1):
            if f * k > SR / 2.2:
                break
            out += np.sin(2 * np.pi * f * k * t) / k
    return out / (3 if detune else 1)


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def onepole_fast(x: np.ndarray, cutoff: float) -> np.ndarray:
    """Cheap FFT brick-ish lowpass for long buffers."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= 1 / np.sqrt(1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def pluck(freq: float, seconds: float) -> np.ndarray:
    n = int(SR * seconds)
    period = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        j = i % period
        out[i] = buf[j]
        buf[j] = 0.994 * 0.5 * (buf[j] + buf[(j + 1) % period])
    return out


def kick(seconds: float = 0.7, big: bool = False) -> np.ndarray:
    t = t_axis(seconds)
    f = 42 + (130 if big else 90) * np.exp(-t * 28)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t * (3.5 if big else 6))
    click = rng.uniform(-1, 1, len(t)) * np.exp(-t * 180) * 0.3
    return np.tanh((body + click) * (2.2 if big else 1.6))


def taiko(seconds: float = 1.2) -> np.ndarray:
    t = t_axis(seconds)
    f = 70 + 40 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    skin = onepole_fast(rng.uniform(-1, 1, len(t)), 900) * np.exp(-t * 12) * 0.9
    return np.tanh((body + skin) * 1.8)


def snare(seconds: float = 0.45) -> np.ndarray:
    t = t_axis(seconds)
    noise = rng.uniform(-1, 1, len(t))
    noise = noise - onepole_fast(noise, 1500)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
    return (noise * np.exp(-t * 14) * 0.9 + tone * 0.6)


def reverb(x: np.ndarray, seconds: float = 2.2, mix: float = 0.3, seed: int = 0) -> np.ndarray:
    r = np.random.default_rng(seed)
    t = t_axis(seconds)
    ir = r.uniform(-1, 1, len(t)) * np.exp(-t * 3.2)
    ir = onepole_fast(ir, 5000)
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir**2)) or 1
    n = len(x) + len(ir)
    wet = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: len(x)]
    return x * (1 - mix) + wet * mix * 1.4


def add(buf: np.ndarray, sig: np.ndarray, start: float, gain: float = 1.0) -> None:
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def compose() -> tuple[np.ndarray, dict]:
    n = int(LENGTH * SR)
    drums = np.zeros(n)
    music = np.zeros(n)
    fx = np.zeros(n)
    events: dict[str, list[float]] = {"hits": [], "drop": [10 * BAR], "silence": [10 * BAR - BEAT / 2]}

    # drone swell (bars 0-9), cut before the drop
    drone_len = 10 * BAR - BEAT / 2
    t = t_axis(drone_len)
    drone = (saw(hz(38), drone_len, 12, 0.004) + 0.6 * saw(hz(45), drone_len, 10, 0.004))
    drone = onepole_fast(drone, 380) * np.minimum(1, t / 4.0) * 0.22
    add(music, drone, 0)

    # reverse-swell noise into bar 2
    sw = t_axis(BAR * 2)
    swell = onepole_fast(rng.uniform(-1, 1, len(sw)), 2500) * (sw / sw[-1]) ** 3 * 0.35
    add(fx, swell, 0)

    # plucked ostinato, bars 2-9 and 10-15
    pattern = [0, 1, 2, 1, 0, 2, 1, 2, 0, 1, 2, 1, 0, 2, 1, 2]
    for bar in list(range(2, 10)) + list(range(10, 16)):
        if bar == 9:
            pass
        chord = CHORDS[PROGRESSION[bar % 4]]
        for k, idx in enumerate(pattern):
            start = bar * BAR + k * BEAT / 4
            if bar == 9 and k >= 14:
                continue
            octave = 12 if (k % 8 == 4) else 0
            note = pluck(hz(chord[idx] + 12 + octave), 0.5)
            gain = 0.12 if bar < 10 else 0.14
            add(music, note * np.linspace(1, 0.3, len(note)), start, gain)

    # taiko pulse bars 2-9
    for bar in range(2, 10):
        add(drums, taiko(), bar * BAR, 0.38 + 0.03 * (bar - 2))
        events["hits"].append(bar * BAR)
        if bar >= 4:
            add(drums, taiko(), bar * BAR + 2 * BEAT, 0.3 + 0.03 * (bar - 4))
            events["hits"].append(bar * BAR + 2 * BEAT)
        if bar >= 6:
            add(drums, taiko(0.8), bar * BAR + 3.5 * BEAT, 0.25)

    # build: snare roll accelerating across bars 8-9
    pos, step = 8 * BAR, BEAT / 2
    while pos < 10 * BAR - BEAT / 2:
        prog = (pos - 8 * BAR) / (2 * BAR)
        add(drums, snare(0.3), pos, 0.08 + 0.4 * prog ** 1.5)
        step = BEAT / 2 if prog < 0.35 else BEAT / 4 if prog < 0.7 else BEAT / 8
        pos += step

    # riser bars 8-9
    rl = 2 * BAR - BEAT / 2
    rt = t_axis(rl)
    f = 200 * (8 ** (rt / rl))
    riser = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    riser += onepole_fast(rng.uniform(-1, 1, len(rt)), 6000) * 0.25
    riser *= (rt / rl) ** 2
    add(fx, riser, 8 * BAR)

    # the drop: low brass hit + big boom
    drop = 10 * BAR
    bl = 4.0
    bt = t_axis(bl)
    brass = sum(saw(hz(m), bl, 30, 0.006) for m in (26, 38, 45, 50))
    brass = np.tanh(onepole_fast(brass, 1400) * 1.6) * env_adsr(len(bt), 0.04, 0.6, 0.55, 2.4) * 0.5
    add(music, brass, drop)
    add(drums, kick(1.6, big=True), drop, 1.0)
    add(drums, taiko(2.0), drop, 0.8)
    events["hits"].append(drop)

    # full drums bars 10-15
    for bar in range(10, 16):
        b0 = bar * BAR
        for beat in (0, 2, 2.5):
            if bar == 10 and beat == 0:
                continue
            add(drums, kick(), b0 + beat * BEAT, 0.8)
            events["hits"].append(b0 + beat * BEAT)
        for beat in (1, 3):
            add(drums, snare(), b0 + beat * BEAT, 0.55)
        add(drums, taiko(), b0 + 3.5 * BEAT, 0.4)
        if bar % 2 == 1:
            for j, beat in enumerate((3.25, 3.5, 3.75)):
                add(drums, taiko(0.6), b0 + beat * BEAT, 0.35 + 0.1 * j)

    # string pad bars 10-15
    for bar in range(10, 16):
        chord = CHORDS[PROGRESSION[bar % 4]]
        pad = sum(saw(hz(m), BAR + 0.4, 14, 0.008) for m in chord)
        pad = onepole_fast(pad, 2200) * env_adsr(len(pad), 0.25, 0.2, 0.8, 0.5) * 0.12
        add(music, pad, bar * BAR)

    # lead melody (original), bars 10-15
    melody = [
        # (MIDI, beats)
        (69, 1), (74, 1), (77, 0.5), (76, 0.5), (74, 1),
        (74, 1.5), (72, 0.5), (70, 1), (65, 1),
        (69, 1), (72, 1), (77, 1.5), (76, 0.5),
        (76, 1), (74, 0.5), (72, 0.5), (67, 2),
        (69, 1), (74, 1), (77, 1), (81, 1),
        (79, 1.5), (77, 0.5), (74, 2),
    ]
    pos = drop
    for note, beats in melody:
        dur = beats * BEAT
        lt = t_axis(dur + 0.25)
        vib = np.sin(2 * np.pi * 5.5 * lt) * 0.004 * np.minimum(1, lt / 0.3)
        f0 = hz(note)
        phase = 2 * np.pi * np.cumsum(f0 * (1 + vib)) / SR
        tone = sum(np.sin(phase * k) / k for k in range(1, 14))
        tone += 0.5 * sum(np.sin(phase * 2 * k) / k for k in range(1, 7))
        tone = onepole_fast(tone, 3200) * env_adsr(len(lt), 0.03, 0.15, 0.75, 0.3) * 0.22
        add(music, tone, pos)
        pos += dur

    # final hit, bar 16
    end = 16 * BAR
    add(drums, kick(2.0, big=True), end, 1.0)
    add(drums, taiko(2.4), end, 0.9)
    fl = 3.0
    final = sum(saw(hz(m), fl, 30, 0.006) for m in (26, 38, 50, 57, 62))
    final = np.tanh(onepole_fast(final, 1800) * 1.4) * env_adsr(int(fl * SR), 0.02, 0.5, 0.5, 2.0) * 0.45
    add(music, final, end)
    events["hits"].append(end)
    events["end"] = [end]

    left = reverb(music, 2.6, 0.32, 1) + reverb(drums, 1.6, 0.22, 3) + reverb(fx, 3.0, 0.45, 5)
    right = reverb(music, 2.6, 0.32, 2) + reverb(drums, 1.6, 0.22, 4) + reverb(fx, 3.0, 0.45, 6)
    stereo = np.stack([left, right], axis=1)
    # cinematic half-beat of silence right before the drop
    g0, g1 = int((drop - BEAT / 2) * SR), int(drop * SR)
    gate = np.ones(len(stereo))
    gate[g0 : g0 + 1500] = np.linspace(1, 0.03, 1500)
    gate[g0 + 1500 : g1] = 0.03
    stereo *= gate[:, None]
    stereo = np.tanh(stereo * 1.1)
    stereo /= np.max(np.abs(stereo)) or 1
    stereo *= 0.89
    fade = int(1.5 * SR)
    stereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return stereo, events


if __name__ == "__main__":
    import wave

    audio, ev = compose()
    pcm = (audio * 32767).astype("<i2")
    with wave.open("/tmp/intro_test.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(len(audio) / SR, "seconds", {k: len(v) for k, v in ev.items()})
