"""Original 120 BPM hyperpop/trap-ish beat, synthesized from scratch (royalty-free)."""
import numpy as np
import wave

SR = 44100
BPM = 120
BEAT = 60 / BPM            # 0.5 s
DURATION = 24.0
DROP = 6.0                 # beat drop lands here (matches the "say less" cut)
N = int(SR * DURATION)
rng = np.random.default_rng(7)


def t_arr(sec):
    return np.arange(int(SR * sec)) / SR


def place(buf, sig, at):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def kick():
    t = t_arr(0.35)
    freq = 45 + 120 * np.exp(-t * 30)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * np.exp(-t * 7) * 1.0


def clap():
    t = t_arr(0.25)
    n = rng.standard_normal(len(t))
    env = np.exp(-t * 22)
    for off in (0.0, 0.012, 0.024):  # flam for a clap feel
        env += np.where(t > off, np.exp(-(t - off) * 60), 0) * 0.5
    # crude bandpass: difference of moving averages
    hp = n - np.convolve(n, np.ones(8) / 8, "same")
    return hp * env * 0.45


def hat(open_=False):
    t = t_arr(0.18 if open_ else 0.05)
    n = rng.standard_normal(len(t))
    n = n - np.convolve(n, np.ones(3) / 3, "same")
    return n * np.exp(-t * (18 if open_ else 90)) * 0.18


def bass808(freq, length):
    t = t_arr(length)
    f = freq * (1 + 0.6 * np.exp(-t * 40))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    s = np.tanh(s * 2.2) * 0.55  # a little grit
    return s * np.minimum(1, t * 200) * np.exp(-t * 1.2)


def pluck(freq, length=0.45, bright=1.0):
    t = t_arr(length)
    s = sum(np.sign(np.sin(2 * np.pi * freq * k * t)) / k for k in (1, 2.003))
    s += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    return s * np.exp(-t * 7 / bright) * 0.07


def pad(freqs, length):
    t = t_arr(length)
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.25, 0.25):
            ph = 2 * np.pi * (f + det) * t
            s += 2 * (ph / (2 * np.pi) % 1) - 1  # saw
    s = np.convolve(s, np.ones(24) / 24, "same")  # soften
    env = np.minimum(1, t / 0.08) * np.minimum(1, (length - t) / 0.1)
    return s * env * 0.035


def riser(length):
    t = t_arr(length)
    n = rng.standard_normal(len(t))
    n = n - np.convolve(n, np.ones(4) / 4, "same")
    sweep = np.sin(2 * np.pi * np.cumsum(300 + 2500 * (t / length) ** 2) / SR)
    return (n * 0.15 + sweep * 0.12) * (t / length) ** 2


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


# Am - F - C - G, one chord per bar (2 s)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [33, 29, 36, 31]
ARP = [0, 1, 2, 1, 2, 0, 2, 1]

drums = np.zeros(N)
bass = np.zeros(N)
music = np.zeros(N)
fx = np.zeros(N)

bars = int(DURATION / (BEAT * 4))
for bar in range(bars):
    t0 = bar * BEAT * 4
    ci = bar % 4
    chord = CHORDS[ci]
    post_drop = t0 >= DROP

    # pad everywhere, arp plucks everywhere (an octave up after the drop)
    place(music, pad([midi(m) for m in chord], BEAT * 4), t0)
    for step in range(8):
        note = chord[ARP[step]] + (12 if post_drop else 0)
        place(music, pluck(midi(note), bright=1.4 if post_drop else 0.8), t0 + step * BEAT / 2)

    if not post_drop:
        # intro: muffled kick on 1 & 3, light hats, nothing heavy
        if t0 < DROP - BEAT * 4:
            for b in (0, 2):
                place(drums, kick() * 0.6, t0 + b * BEAT)
            for s in range(8):
                place(drums, hat() * 0.7, t0 + s * BEAT / 2)
        continue

    # post-drop: trap groove
    for b in (0, 1.5, 2.75):
        place(drums, kick(), t0 + b * BEAT)
    for b in (1, 3):
        place(drums, clap(), t0 + b * BEAT)
    for s in range(16):
        tt = t0 + s * BEAT / 4
        if bar % 2 == 1 and s >= 12:  # trap hat roll at end of every other bar
            for r in range(3):
                place(drums, hat() * 0.8, tt + r * BEAT / 12)
        elif s % 2 == 0 or rng.random() < 0.35:
            place(drums, hat() * (1.0 if s % 4 == 2 else 0.7), tt)
    place(drums, hat(open_=True), t0 + 3.5 * BEAT)
    place(bass, bass808(midi(ROOTS[ci]), BEAT * 1.5), t0)
    place(bass, bass808(midi(ROOTS[ci]), BEAT * 1.2), t0 + 1.5 * BEAT)
    place(bass, bass808(midi(ROOTS[ci] + 12 if bar % 2 else ROOTS[ci]), BEAT * 1.2), t0 + 2.75 * BEAT)

# riser into the drop, then a hard silence gap right before it
place(fx, riser(BEAT * 4 - 0.12), DROP - BEAT * 4)
gap = slice(int((DROP - 0.12) * SR), int(DROP * SR))
music[gap] *= 0.0
drums[gap] *= 0.0

# sidechain pump on music from the kicks after the drop
t = np.arange(N) / SR
pump = np.ones(N)
for bar in range(bars):
    t0 = bar * BEAT * 4
    if t0 < DROP:
        continue
    for b in (0, 1.5, 2.75):
        k0 = t0 + b * BEAT
        m = (t >= k0) & (t < k0 + 0.3)
        pump[m] = np.minimum(pump[m], 0.35 + 0.65 * ((t[m] - k0) / 0.3))

mix = drums * 0.9 + bass * 0.9 + music * pump * 1.1 + fx
mix = np.tanh(mix * 1.3) * 0.85
# fade out over last second
fade = np.ones(N)
fade[-SR:] = np.linspace(1, 0, SR)
mix *= fade

# light stereo widening: delay the music on the right channel
left = mix
right = np.roll(mix * 0.98, 300)
stereo = np.stack([left, right], axis=1)
stereo /= np.abs(stereo).max() * 1.05

with wave.open("music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print("music.wav written", DURATION, "s")
