"""Sound effects for the video, generated from code (no samples, no third-party audio, no music).

Everything is synthesised with numpy/scipy: scene and chapter whooshes, an intro sting and an outro chord. Because
nothing is sampled or downloaded, there is no licensing question (see video/AUDIO-LICENSES.md).

    python video/sound_effects.py preview      writes every sound effect to video/out/preview/

build.py calls render_mix() during the "post" step: the cleaned voice plus the sound effects.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, oaconvolve, resample_poly, sosfilt

SR = 48000


def t_axis(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SR)) / SR


def lowpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, cutoff, "lowpass", fs=SR, output="sos"), x, axis=0)


def highpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, cutoff, "highpass", fs=SR, output="sos"), x, axis=0)


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x, axis=0)


def stereo(x: np.ndarray, pan: float = 0.0) -> np.ndarray:
    """Mono to stereo with an equal-power pan (-1 left .. +1 right)."""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


class Reverb:
    """A small synthetic room: decorrelated, darkened, exponentially decaying noise as the impulse response."""

    def __init__(self, seconds: float = 1.6, decay: float = 0.42, seed: int = 7):
        rng = np.random.default_rng(seed)
        t = t_axis(seconds)
        ir = rng.standard_normal((len(t), 2)) * np.exp(-t / decay)[:, None]
        ir[: int(0.012 * SR)] = 0                                   # 12 ms pre-delay
        ir = lowpass(ir, 5200)
        self.ir = (ir / np.sqrt((ir ** 2).sum(axis=0))).astype(np.float32)

    def __call__(self, x: np.ndarray, wet: float) -> np.ndarray:
        x2 = x if x.ndim == 2 else stereo(x)
        pad = np.zeros((len(self.ir), 2), dtype=np.float32)
        dry = np.vstack([x2, pad])
        tail = np.zeros_like(dry)
        for c in range(2):
            wet_c = oaconvolve(x2[:, c], self.ir[:, c])[: len(dry)]
            tail[: len(wet_c), c] = wet_c
        return (1 - wet) * dry + wet * tail


ROOM = Reverb()


def place(buf: np.ndarray, sig: np.ndarray, start: float, gain: float, pan: float = 0.0) -> None:
    s = int(start * SR)
    if s >= len(buf):
        return
    x = sig if sig.ndim == 2 else stereo(sig, pan)
    n = min(len(x), len(buf) - s)
    buf[s:s + n] += gain * x[:n].astype(np.float32)



# ----------------------------------------------------------------------------------------------- sound effects
def whoosh(seconds: float, lo: float, hi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = t_axis(seconds)
    noise = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    blocks = 24
    size = len(t) // blocks
    win = np.hanning(size * 2)
    for b in range(blocks - 1):
        f = lo * (hi / lo) ** (b / blocks)
        seg = bandpass(noise[b * size: b * size + 2 * size], f * 0.7, min(f * 1.4, SR / 2 - 100))
        out[b * size: b * size + len(seg)] += seg * win[: len(seg)]
    env = np.sin(np.pi * np.clip(t / seconds, 0, 1)) ** 1.5
    x = out * env
    x = stereo(x / np.abs(x).max(), 0)
    x[:, 0] *= np.linspace(1.0, 0.6, len(t))                          # a slight left-to-right movement
    x[:, 1] *= np.linspace(0.6, 1.0, len(t))
    return x


def bell(freq: float, seconds: float, decay: float) -> np.ndarray:
    t = t_axis(seconds)
    partials = ((1, 1.0, 1.0), (2.76, 0.45, 0.6), (5.40, 0.22, 0.35), (8.93, 0.10, 0.2))
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / (decay * d)) for r, a, d in partials)
    return x * np.minimum(1, t / 0.003)


def sfx(kind: str, seed: int = 3) -> np.ndarray:
    if kind == "scene":
        return whoosh(0.5, 500, 3500, seed) * 0.5
    if kind == "chapter":
        return whoosh(0.8, 300, 4500, seed + 1) * 0.75
    if kind == "success":                                              # two rising bell notes
        x = np.zeros(int(1.6 * SR))
        for i, f in enumerate((1318.5, 1760.0)):
            b = bell(f, 1.4, 0.45)
            s = int(i * 0.09 * SR)
            x[s:s + len(b)] += b[: len(x) - s]
        return ROOM(x / np.abs(x).max() * 0.55, wet=0.3)
    if kind == "error":                                                # two soft falling tones
        t = t_axis(0.2)
        x = np.zeros(int(0.5 * SR))
        for i, f in enumerate((392.0, 311.1)):
            tone = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5)) * np.exp(-t / 0.07) * np.minimum(1, t / 0.004)
            s = int(i * 0.14 * SR)
            x[s:s + len(tone)] += tone
        return ROOM(lowpass(x / np.abs(x).max() * 0.6, 2800), wet=0.15)
    if kind == "pop":
        t = t_axis(0.09)
        f = 700 + 600 * np.exp(-t / 0.02)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
        return ROOM(x * 0.5, wet=0.2)
    if kind == "intro":                                                # soft impact + shimmering A major arpeggio
        t = t_axis(2.8)
        boom = np.sin(2 * np.pi * np.cumsum(50 + 60 * np.exp(-t / 0.06)) / SR) * np.exp(-t / 0.7)
        x = 0.9 * boom
        for i, f in enumerate((880.0, 1108.7, 1318.5, 1760.0)):
            b = bell(f, 2.4, 0.7) * 0.25
            s = int((0.05 + i * 0.07) * SR)
            x[s:s + len(b)] += b[: len(x) - s]
        return ROOM(lowpass(x / np.abs(x).max() * 0.8, 9000), wet=0.4)
    if kind == "outro":                                                # a gentle closing chord
        x = np.zeros(int(3.6 * SR))
        for i, f in enumerate((440.0, 554.4, 659.3, 880.0)):
            b = bell(f, 3.2, 1.0) * 0.3
            s = int(i * 0.12 * SR)
            x[s:s + len(b)] += b[: len(x) - s]
        return ROOM(x / np.abs(x).max() * 0.7, wet=0.45)
    raise ValueError(kind)


SFX_GAIN = {"scene": 0.07, "chapter": 0.11, "success": 0.16, "error": 0.15, "pop": 0.10, "intro": 0.30, "outro": 0.22}


# ----------------------------------------------------------------------------------------------- mixing
def render_mix(voice_path: Path, out_path: Path, total: float, events: list[tuple[float, str]]) -> None:
    """The voice plus every sound effect at its time, as a 48 kHz stereo float WAV."""
    rate, voice = wavfile.read(voice_path)
    voice = voice.astype(np.float32) / (32768.0 if voice.dtype == np.int16 else 1.0)
    if voice.ndim == 2:
        voice = voice.mean(axis=1)
    if rate != SR:
        voice = resample_poly(voice, SR, rate).astype(np.float32)
    n = max(len(voice), int(total * SR))
    voice = np.pad(voice, (0, n - len(voice)))
    fx = np.zeros((n, 2), dtype=np.float32)
    cache: dict[str, np.ndarray] = {}
    for when, kind in events:
        cache.setdefault(kind, sfx(kind))
        lead = 0.25 if kind in ("scene", "chapter") else 0.0           # whooshes peak on the cut
        place(fx, cache[kind], max(0.0, when - lead), SFX_GAIN[kind])
    mix = stereo(voice) + fx
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    wavfile.write(out_path, SR, mix.astype(np.float32))


if __name__ == "__main__" and sys.argv[1:] == ["preview"]:
    out = Path(__file__).resolve().parent / "out" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    for kind in SFX_GAIN:
        x = sfx(kind)
        wavfile.write(out / f"sfx-{kind}.wav", SR, (x if x.ndim == 2 else stereo(x)).astype(np.float32))
    print("preview written to", out)
