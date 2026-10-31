"""Synthesized background music: quiet, dark, ambient beds that sit under narration.

from music import generate, TRACKS
audio = generate(seconds, mood="night_walk", sr=24000, seed=3)   # mono float32, peak ~0.9

Design rules (after review on 2026-10-31): background only. No FM/vibrato bells ("UFO" sound),
no drums, no bright leads; soft pads, low strings, felt piano, gentle plucks, drones, wind, a quiet
clock or heartbeat. Modelled on craftee_films' beds: ~60-66 bpm, minor, mid-range, little bass.
Older mood names (eerie, suspense, mystery, playful, sweet, tech) map onto these tracks.
"""
import numpy as np

# ------------------------------------------------------------------ instruments (all soft)


def hz(semi):
    return 440.0 * 2 ** (semi / 12)


def env(n, sr, a, r, total=None):
    """Attack a, release r (seconds) over a note of n samples."""
    t = np.arange(n) / sr
    length = n / sr
    return np.clip(np.minimum(t / max(a, 1e-4), (length - t) / max(r, 1e-4)), 0, 1)


def lowpass(x, cutoff, sr):
    """One-pole low-pass (vectorised in blocks via lfilter-free recursion)."""
    a = np.exp(-2 * np.pi * cutoff / sr)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def sine_pad(freqs, length, sr, a=1.6, r=1.6):
    n = int(length * sr)
    t = np.arange(n) / sr
    w = np.zeros(n)
    for f in freqs:
        for det in (-0.06, 0.06):
            w += np.sin(2 * np.pi * f * 2 ** (det / 12) * t) + 0.18 * np.sin(2 * np.pi * 2 * f * t)
    return w / (2 * max(1, len(freqs))) * env(n, sr, a, r)


def warm_pad(freqs, length, sr, cutoff=650):
    n = int(length * sr)
    t = np.arange(n) / sr
    w = np.zeros(n)
    for f in freqs:
        for det in (-0.08, 0.08):
            w += 2 * ((t * f * 2 ** (det / 12)) % 1) - 1
    w = lowpass(w / (2 * max(1, len(freqs))), cutoff, sr)
    return w * env(n, sr, 1.4, 1.4)


def piano(freq, length, sr):
    """Felt-piano-ish: a few decaying harmonics, soft attack."""
    n = int(length * sr)
    t = np.arange(n) / sr
    w = sum(a * np.sin(2 * np.pi * freq * k * 1.001 ** k * t) * np.exp(-t * (1.2 + k * 0.8))
            for k, a in ((1, 1.0), (2, 0.35), (3, 0.12), (4, 0.05)))
    return w * env(n, sr, 0.012, 0.3)


def soft_box(freq, length, sr):
    """Plain sine music box: no FM, no vibrato."""
    n = int(length * sr)
    t = np.arange(n) / sr
    return (np.sin(2 * np.pi * freq * t) + 0.08 * np.sin(2 * np.pi * 3 * freq * t)) * np.exp(-t / 0.9) * env(n, sr, 0.004, 0.2)


def cello(freq, length, sr):
    n = int(length * sr)
    t = np.arange(n) / sr
    w = np.sin(2 * np.pi * freq * t) + 0.45 * np.sin(2 * np.pi * 2 * freq * t) + 0.2 * np.sin(2 * np.pi * 3 * freq * t)
    return lowpass(w, 900, sr) * env(n, sr, 0.5, 0.8)


def drone(freq, length, sr):
    n = int(length * sr)
    t = np.arange(n) / sr
    return (np.sin(2 * np.pi * freq * t) + np.sin(2 * np.pi * freq * 1.003 * t) + 0.3 * np.sin(2 * np.pi * 1.5 * freq * t)) / 2.3 * env(n, sr, 2.5, 2.5)


def pluck(freq, length, sr, rng, damp=0.985):
    n = int(length * sr)
    period = max(2, int(sr / freq))
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = damp * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return lowpass(out, 1800, sr) * env(n, sr, 0.003, 0.15)


def heartbeat(sr):
    n = int(0.6 * sr)
    t = np.arange(n) / sr
    thump = lambda t0, g: g * np.sin(2 * np.pi * 52 * (t - t0)) * np.exp(-np.clip(t - t0, 0, None) / 0.06) * (t >= t0)
    return thump(0.0, 1.0) + thump(0.22, 0.7)


def tick(sr, rng):
    n = int(0.03 * sr)
    x = rng.normal(0, 1, n) * np.exp(-np.arange(n) / sr / 0.004)
    return x - lowpass(x, 3000, sr)


def wind(length, sr, rng):
    n = int(length * sr)
    x = lowpass(rng.normal(0, 1, n), 500, sr)
    t = np.arange(n) / sr
    return x / (np.max(np.abs(x)) or 1) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * t + 1.3)) * env(n, sr, 2.0, 2.0)


# ------------------------------------------------------------------ tracks

B_MINOR = [[-10, -7, -3], [-14, -10, -7], [-17, -14, -10], [-12, -8, -5]]       # Bm, G, Em, F#(minor-ish)
D_MINOR = [[-7, -4, 0], [-11, -7, -4], [-14, -11, -7], [-9, -5, -2]]           # Dm, Bb, Gm, A


class Bed:
    def __init__(self, seconds, sr, seed):
        self.sr, self.seconds = sr, seconds
        self.rng = np.random.default_rng(seed)
        self.out = np.zeros(int((seconds + 4) * sr))

    def put(self, sig, at, gain):
        i = int(at * self.sr)
        if i >= len(self.out):
            return
        seg = sig[: len(self.out) - i]
        self.out[i:i + len(seg)] += gain * seg

    def bars(self, bpm):
        bar = 240.0 / bpm
        t, k = 0.0, 0
        while t < self.seconds:
            yield k, t, bar
            t += bar
            k += 1


def t_hollow(b):            # 1. drone + slow pad chords, no melody
    for k, t, bar in b.bars(60):
        ch = B_MINOR[k % 4]
        b.put(sine_pad([hz(n) for n in ch], bar * 1.3, b.sr), t, 0.5)
        if k % 2 == 0:
            b.put(drone(hz(-22), bar * 2.4, b.sr), t, 0.35)


def t_night_walk(b):        # 2. sparse felt piano over a warm pad
    for k, t, bar in b.bars(62):
        ch = B_MINOR[k % 4]
        b.put(warm_pad([hz(n) for n in ch], bar * 1.25, b.sr), t, 0.45)
        for s, nte in enumerate((ch[0] + 12, ch[2], ch[1] + 12) if k % 2 else (ch[2] + 12, ch[0] + 12)):
            b.put(piano(hz(nte), 2.5, b.sr), t + s * bar / 3 + 0.05, 0.18)


def t_clockwork(b):         # 3. quiet clock + pad + low piano
    for k, t, bar in b.bars(64):
        ch = D_MINOR[k % 4]
        b.put(sine_pad([hz(n) for n in ch], bar * 1.3, b.sr), t, 0.45)
        for s in range(4):
            b.put(tick(b.sr, b.rng), t + s * bar / 4, 0.06)
        if k % 2 == 1:
            b.put(piano(hz(ch[0] - 12), 3.0, b.sr), t + bar / 2, 0.22)


def t_heartbeat(b):         # 4. soft heartbeat + drone + slowly rising pad
    for k, t, bar in b.bars(60):
        ch = B_MINOR[(k // 2) % 4]
        b.put(sine_pad([hz(n) for n in ch], bar * 1.3, b.sr), t, 0.3 + 0.1 * min(1, k / 12))
        b.put(drone(hz(-22), bar * 1.4, b.sr), t, 0.25)
        for s in (0, 2):
            b.put(heartbeat(b.sr), t + s * bar / 4, 0.35)


def t_lullaby(b):           # 5. very soft plain music box, slow, over a pad
    tune = [0, 3, 7, 5, 3, 2, 3, 0]
    for k, t, bar in b.bars(58):
        ch = B_MINOR[k % 4]
        b.put(sine_pad([hz(n) for n in ch], bar * 1.3, b.sr), t, 0.4)
        for s in range(4):
            b.put(soft_box(hz(-10 + 12 + tune[(k * 4 + s) % 8]), 1.6, b.sr), t + s * bar / 4, 0.1)


def t_cellar(b):            # 6. low cello notes + wind
    b.put(wind(b.seconds + 3, b.sr, b.rng), 0, 0.22)
    for k, t, bar in b.bars(56):
        ch = D_MINOR[k % 4]
        b.put(cello(hz(ch[0] - 12), bar * 1.1, b.sr), t, 0.42)
        if k % 2:
            b.put(cello(hz(ch[2] - 12), bar * 0.6, b.sr), t + bar / 2, 0.25)


def t_mist(b):              # 7. airy wind + soft high pad
    b.put(wind(b.seconds + 3, b.sr, b.rng), 0, 0.3)
    for k, t, bar in b.bars(54):
        ch = B_MINOR[k % 4]
        b.put(sine_pad([hz(n + 12) for n in ch], bar * 1.4, b.sr, a=2.5, r=2.5), t, 0.28)


def t_pizzicato(b):         # 8. gentle sparse pizzicato + pad
    for k, t, bar in b.bars(66):
        ch = D_MINOR[k % 4]
        b.put(sine_pad([hz(n) for n in ch], bar * 1.3, b.sr), t, 0.35)
        for s, idx in enumerate((0, 2, 1, 2) if k % 2 == 0 else (0, 1, 2, 1)):
            b.put(pluck(hz(ch[idx]), 0.6, b.sr, b.rng), t + s * bar / 4, 0.28)


def t_suspicion(b):         # 9. quiet pulsing low strings in eighths + pad
    for k, t, bar in b.bars(63):
        ch = B_MINOR[(k // 2) % 4]
        b.put(warm_pad([hz(n) for n in ch], bar * 1.25, b.sr, cutoff=500), t, 0.4)
        for s in range(8):
            g = 0.16 if s % 2 == 0 else 0.1
            b.put(cello(hz(ch[0] - 12), bar / 8 * 0.9, b.sr), t + s * bar / 8, g)


def t_static_lake(b):       # 10. long evolving pad + a distant soft bell now and then
    for k, t, bar in b.bars(52):
        ch = D_MINOR[(k // 2) % 4]
        cutoff = 450 + 300 * (0.5 + 0.5 * np.sin(k * 0.6))
        b.put(warm_pad([hz(n) for n in ch], bar * 1.4, b.sr, cutoff=cutoff), t, 0.45)
        if k % 3 == 2:
            b.put(soft_box(hz(ch[2] + 12), 2.5, b.sr), t + bar / 3, 0.07)


TRACKS = {
    "hollow": t_hollow, "night_walk": t_night_walk, "clockwork": t_clockwork, "heartbeat": t_heartbeat,
    "lullaby": t_lullaby, "cellar": t_cellar, "mist": t_mist, "pizzicato": t_pizzicato,
    "suspicion": t_suspicion, "static_lake": t_static_lake,
}
ALIASES = {"eerie": "night_walk", "suspense": "suspicion", "mystery": "pizzicato",
           "playful": "pizzicato", "sweet": "lullaby", "tech": "clockwork"}
MOODS = TRACKS


def generate(seconds, mood="night_walk", sr=24000, seed=0):
    fn = TRACKS.get(ALIASES.get(mood, mood), t_night_walk)
    b = Bed(seconds, sr, seed)
    fn(b)
    out = b.out[: int(seconds * sr)]
    out = 0.3 * out + 0.7 * lowpass(out, 1800, sr)      # keep it dark and out of the voice's way
    fade_in = np.minimum(1, np.arange(len(out)) / (1.5 * sr))
    fade_out = np.minimum(1, (len(out) - np.arange(len(out))) / (1.2 * sr))
    out *= fade_in * fade_out
    peak = np.max(np.abs(out)) or 1.0
    return (0.9 * out / peak).astype(np.float32)


if __name__ == "__main__":
    import sys
    import wave
    from pathlib import Path
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    dest.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(TRACKS, 1):
        a = generate(30, name, seed=i)
        with wave.open(str(dest / f"{i:02d}_{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes((a * 32767).astype(np.int16).tobytes())
        print("wrote", f"{i:02d}_{name}")
