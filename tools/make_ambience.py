"""Generate the ambient soundscapes for the five VR theme worlds.

Every sound is synthesised here from noise and oscillators, so the files are
original and free of third-party licences. Each soundscape is a seamless 60 s
loop (60 is a multiple of the 10 s breathing cycle used by the 3D player, so
the "breathing" swell stays in step across loops).

Usage:  python tools/make_ambience.py [output_dir]   (default: static/wellbeing/audio)
Needs numpy and scipy (already project dependencies) and ffmpeg on PATH for MP3
encoding. Without ffmpeg it leaves WAV files instead.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
LOOP = 60.0  # seconds; multiple of the 10 s breathing cycle
TAIL = 4.0   # extra seconds rendered for the loop crossfade
N = int(SR * (LOOP + TAIL))
T = np.arange(N) / SR


# ----------------------------------------------------------------- building blocks

def filt(signal, kind, freq, order=2):
    sos = butter(order, freq, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, signal)


def pink(rng, n=N):
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spectrum[1:] /= np.sqrt(freqs[1:])
    spectrum[0] = 0
    out = np.fft.irfft(spectrum, n)
    return out / np.max(np.abs(out))


def brown(rng, n=N):
    out = np.cumsum(rng.standard_normal(n))
    out = filt(out, "highpass", 20)
    return out / np.max(np.abs(out))


def breath(t):
    """Same curve as the 3D player: 4 s rising, 6 s falling, 0..1."""
    phase = np.mod(t, 10.0)
    ease = lambda x: 0.5 - np.cos(np.pi * x) / 2  # noqa: E731
    return np.where(phase < 4, ease(phase / 4), 1 - ease((phase - 4) / 6))


def slow_lfo(rng, rate, depth=1.0):
    """Smooth random modulation, 0..1."""
    points = max(4, int(LOOP * rate) + 4)
    knots = rng.random(points)
    x = np.linspace(0, len(knots) - 1, N)
    curve = np.interp(x, np.arange(len(knots)), knots)
    curve = filt(curve, "lowpass", max(rate * 2, 0.05), 1)
    curve = (curve - curve.min()) / (np.ptp(curve) + 1e-9)
    return 1 - depth + depth * curve


def pad(notes, rng, brightness=1200, detune=0.15):  # ±0.15 Hz → ~0.3 Hz beating: a slow shimmer, not a tremolo
    out = np.zeros(N)
    for i, freq in enumerate(notes):
        for spread in (-detune, detune):
            f = freq + spread
            phase = rng.random() * 2 * np.pi
            wobble = 1 + 0.002 * np.sin(2 * np.pi * (0.07 + 0.03 * i) * T)
            tone = np.sin(2 * np.pi * f * T * wobble + phase)
            tone += 0.25 * np.sin(2 * np.pi * 2 * f * T + phase)  # soft 2nd harmonic
            out += tone * (0.75 + 0.25 * np.sin(2 * np.pi * (0.05 + 0.02 * i) * T + i))
    out = filt(out, "lowpass", brightness, 2)
    return out / np.max(np.abs(out))


def place(out, event, start):
    i = int(start * SR)
    j = min(len(out), i + len(event))
    if i < len(out):
        out[i:j] += event[: j - i]


def chime(freq, rng, length=4.0, gain=1.0):
    t = np.arange(int(length * SR)) / SR
    partials = [(1, 1.0, 1.6), (2.0, 0.35, 1.0), (2.76, 0.18, 0.7), (5.4, 0.06, 0.35)]
    tone = sum(a * np.sin(2 * np.pi * freq * r * t + rng.random() * 6) * np.exp(-t / d) for r, a, d in partials)
    attack = np.minimum(1, t / 0.008)
    return gain * tone * attack


def chirp(f0, f1, length, rng, curve=1.0):
    t = np.arange(int(length * SR)) / SR
    sweep = f0 + (f1 - f0) * (t / length) ** curve
    phase = 2 * np.pi * np.cumsum(sweep) / SR
    env = np.sin(np.pi * t / length) ** 2
    return np.sin(phase + rng.random()) * env


def bird_phrase(rng, base):
    """A short, gentle song: 3–7 chirps around a base pitch."""
    parts = []
    for _ in range(rng.integers(3, 8)):
        f0 = base * rng.uniform(0.85, 1.25)
        f1 = f0 * rng.uniform(0.7, 1.5)
        parts.append(chirp(f0, f1, rng.uniform(0.05, 0.16), rng, rng.uniform(0.5, 2)))
        parts.append(np.zeros(int(SR * rng.uniform(0.03, 0.12))))
    return np.concatenate(parts)


def reverb(signal, rng, seconds=2.4, decay=0.55, mix=0.35, tone=5000):
    length = int(seconds * SR)
    t = np.arange(length) / SR
    ir = rng.standard_normal(length) * np.exp(-t / decay)
    ir = filt(ir, "lowpass", tone, 1)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = fftconvolve(signal, ir)[: len(signal)]
    return (1 - mix) * signal + mix * wet / (np.max(np.abs(wet)) + 1e-9) * np.max(np.abs(signal))


def finish(signal):
    """Crossfade the tail into the head for a seamless loop, then level-match."""
    loop_n, fade_n = int(LOOP * SR), int(TAIL * SR)
    out = signal[:loop_n].copy()
    ramp = np.linspace(0, np.pi / 2, fade_n)
    out[:fade_n] = signal[:fade_n] * np.sin(ramp) + signal[loop_n:loop_n + fade_n] * np.cos(ramp)
    out -= np.mean(out)
    rms = np.sqrt(np.mean(out ** 2))
    out *= 10 ** (-22 / 20) / rms              # about -22 dBFS RMS: quiet, consistent
    peak = np.max(np.abs(out))
    if peak > 0.89:                            # soft-limit peaks to about -1 dBFS
        out = np.tanh(out / 0.89) * 0.89
    return out


# ----------------------------------------------------------------- soundscapes

def calm(rng):
    """Garden at dusk: warm breathing chord, distant crickets, a soft breeze, rare chimes."""
    chord = pad([110.0, 164.81, 220.0, 277.18, 329.63], rng, brightness=900)
    out = chord * (0.45 + 0.55 * breath(T)) * 0.55
    breeze = filt(pink(rng), "bandpass", [180, 900]) * slow_lfo(rng, 0.08, 0.8)
    out += breeze / np.max(np.abs(breeze)) * 0.12
    crickets = np.zeros(N)
    for carrier, rate, gain in ((4300, 0.62, 0.032), (4700, 0.81, 0.022)):
        pulse = (np.sin(2 * np.pi * 28 * T) > 0.2).astype(float)
        bursts = (np.mod(T, rate) < 0.11).astype(float)
        crickets += np.sin(2 * np.pi * carrier * T) * filt(pulse * bursts, "lowpass", 300, 1) * gain
    out += crickets * slow_lfo(rng, 0.05, 0.6)
    chimes = np.zeros(N)
    for start in np.arange(3.0, LOOP + TAIL - 4, 11.0) + rng.uniform(0, 3, len(np.arange(3.0, LOOP + TAIL - 4, 11.0))):
        place(chimes, chime(rng.choice([440.0, 554.37, 659.25, 880.0]), rng, gain=0.12), start)
    out += reverb(chimes, rng, 3.2, 0.9, 0.6)
    return reverb(out, rng, 2.0, 0.6, 0.2)


def nature(rng):
    """Forest rain: steady rain on leaves, close drips, soft wind, a low breathing hum."""
    rain = filt(pink(rng), "bandpass", [500, 9000], 2) * (0.85 + 0.15 * slow_lfo(rng, 0.1))
    canopy = filt(pink(rng), "bandpass", [150, 1200], 2) * slow_lfo(rng, 0.06, 0.5)
    out = rain * 0.55 + canopy * 0.35
    drips = np.zeros(N)
    for _ in range(int((LOOP + TAIL) * 9)):
        freq = rng.uniform(1600, 4200)
        length = int(SR * 0.05)
        t = np.arange(length) / SR
        drop = np.sin(2 * np.pi * freq * t * (1 - 0.35 * t / t[-1])) * np.exp(-t / 0.012)
        place(drips, drop * rng.uniform(0.05, 0.22), rng.uniform(0, LOOP + TAIL - 0.1))
    out += drips
    wind = filt(brown(rng), "lowpass", 400) * slow_lfo(rng, 0.05, 0.7)
    out += wind / np.max(np.abs(wind)) * 0.2
    hum = pad([73.42, 110.0, 146.83], rng, brightness=500) * (0.4 + 0.6 * breath(T))
    out += hum * 0.12
    return reverb(out, rng, 1.6, 0.4, 0.15)


def learning(rng):
    """Language lab: a calm focus pad with an unhurried music-box melody."""
    chord = pad([130.81, 196.0, 293.66, 329.63], rng, brightness=1400)
    out = chord * 0.4 * (0.75 + 0.25 * slow_lfo(rng, 0.05))
    scale = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66]  # C major pentatonic-ish
    melody = np.zeros(N)
    step, index = 0.0, 2
    while step < LOOP + TAIL - 4:
        index = int(np.clip(index + rng.choice([-2, -1, 1, 1, 2]), 0, len(scale) - 1))
        place(melody, chime(scale[index], rng, 3.0, gain=0.16 * rng.uniform(0.7, 1.0)), step)
        step += rng.choice([1.2, 1.2, 1.8, 2.4, 3.6])
    out += reverb(melody, rng, 2.8, 0.7, 0.45)
    room = filt(pink(rng), "lowpass", 600) * 0.05
    return out + room


def active(rng):
    """Football & bike: sea swell on the shore, lively birds, a bright breeze."""
    swell = np.zeros(N)
    start = 0.0
    while start < LOOP + TAIL:
        period = rng.uniform(6.5, 9.5)
        t = np.arange(int(period * SR)) / SR
        shape = np.sin(np.pi * t / period) ** 3
        place(swell, shape, start)
        start += period * 0.8
    surf = filt(pink(rng), "bandpass", [200, 6000], 2)
    out = surf * (0.15 + 0.85 * swell) * 0.6
    out += filt(brown(rng), "lowpass", 250) * 0.18
    birds = np.zeros(N)
    for _ in range(int((LOOP + TAIL) / 2.2)):
        place(birds, bird_phrase(rng, rng.choice([2600, 3200, 3900])) * rng.uniform(0.06, 0.14), rng.uniform(0, LOOP + TAIL - 2))
    out += reverb(birds, rng, 1.2, 0.3, 0.3)
    breeze = filt(pink(rng), "bandpass", [600, 3000]) * slow_lfo(rng, 0.12, 0.8)
    out += breeze / np.max(np.abs(breeze)) * 0.08
    return out


def family(rng):
    """School run: a bright morning chorus, rustling leaves and a warm, homely chord."""
    out = filt(pink(rng), "lowpass", 500) * 0.12  # distant town hush
    leaves = filt(pink(rng), "highpass", 2500) * slow_lfo(rng, 0.2, 0.9)
    out += leaves / np.max(np.abs(leaves)) * 0.07
    birds = np.zeros(N)
    for _ in range(int((LOOP + TAIL) / 1.6)):
        place(birds, bird_phrase(rng, rng.choice([2200, 2900, 3500, 4200])) * rng.uniform(0.05, 0.15), rng.uniform(0, LOOP + TAIL - 2))
    out += reverb(birds, rng, 1.5, 0.35, 0.35)
    warm = pad([174.61, 220.0, 261.63, 349.23], rng, brightness=1000)
    out += warm * 0.14 * (0.7 + 0.3 * slow_lfo(rng, 0.06))
    return out


SOUNDSCAPES = {"calm": calm, "nature": nature, "learning": learning, "active": active, "family": family}


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("static/wellbeing/audio")
    output.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    for seed, (key, build) in enumerate(SOUNDSCAPES.items(), start=11):
        audio = finish(build(np.random.default_rng(seed)))
        wav = output / f"{key}.wav"
        wavfile.write(wav, SR, (audio * 32767).astype(np.int16))
        if ffmpeg:
            mp3 = output / f"{key}.mp3"
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", "96k",
                            "-metadata", f"title=Astro-Doctor ambience: {key}", str(mp3)], check=True)
            wav.unlink()
            print(f"{mp3}  ({mp3.stat().st_size // 1024} KB)")
        else:
            print(f"{wav}  (ffmpeg not found; left as WAV)")


if __name__ == "__main__":
    main()
