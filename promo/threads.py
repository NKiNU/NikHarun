"""Threads promo (4:5): 'explaining my job to the group chat' + original jersey-club beat.
Reuses the text/sticker helpers from video.py. Run: python threads.py [preview seconds...]"""
import math
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import video as v
from video import BLACK, BLUE, FONT_BOLD, FONT_HEAVY, LIME, PINK, PURPLE, WHITE, pill, pop, paste_center, text_img

W, H = 1080, 1350
FPS = 30
BPM = 140
B = 60 / BPM
TOTAL_BEATS = 48
DURATION = TOTAL_BEATS * B          # ~20.6 s
DROP = 32 * B                       # "say less." lands here
OUT = "C:/Users/acer/desktop/mantap-portfolio/promo/nik-harun-threads.mp4"
WAV = "C:/Users/acer/desktop/mantap-portfolio/promo/threads_music.wav"
GREY = (38, 38, 44)

# (beat, sender, text) — "me" = Nik (right, lime), "bestie" = friend (left, grey)
CHAT = [
    (5, "bestie", "wait so what do u actually do"),
    (8, "me", "i find out what users actually need 🔍"),
    (11, "me", "then build it. fast. with AI ⚡"),
    (14, "bestie", "so... vibe coding?? 💀"),
    (17, "me", "vibe coding + i read every line fr"),
    (20, "me", "then ship it & check it actually worked 🚀"),
    (23, "bestie", "ok that's lowkey elite"),
    (26, "bestie", "can u build mine 🥺"),
]
CHAT_T = [(beat * B, who, txt) for beat, who, txt in CHAT]


# ───────────────────────── music ─────────────────────────

def make_music():
    sr = 44100
    n = int(sr * DURATION)
    rng = np.random.default_rng(11)

    def ta(sec):
        return np.arange(int(sr * sec)) / sr

    def place(buf, sig, at):
        i = int(at * sr)
        j = min(len(buf), i + len(sig))
        if 0 <= i < len(buf):
            buf[i:j] += sig[: j - i]

    def midi(m):
        return 440 * 2 ** ((m - 69) / 12)

    def kick(gain=1.0):
        t = ta(0.3)
        f = 48 + 140 * np.exp(-t * 35)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 9) * gain

    def noise_hit(length, decay, gain, smooth):
        t = ta(length)
        x = rng.standard_normal(len(t))
        x = x - np.convolve(x, np.ones(smooth) / smooth, "same")
        return x * np.exp(-t * decay) * gain

    def chirp(f0, f1, length=0.12, gain=0.18):
        t = ta(length)
        f = f0 + (f1 - f0) * (t / length)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 18) * gain

    def keys(freqs, length, gain=0.05):
        t = ta(length)
        s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) for f in freqs)
        trem = 1 + 0.15 * np.sin(2 * np.pi * 4 * t)
        return s * trem * np.minimum(1, t / 0.02) * np.exp(-t * 0.9) * gain

    def bass(freq, length):
        t = ta(length)
        s = np.tanh(2 * np.sin(2 * np.pi * freq * (1 + 0.5 * np.exp(-t * 40)) * t)) * 0.5
        return s * np.minimum(1, t * 300) * np.exp(-t * 2)

    chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]  # Fmaj7 Em7 Dm7 Cmaj7
    roots = [29, 28, 26, 24]
    drums, music, low, fx = (np.zeros(n) for _ in range(4))

    for bar in range(TOTAL_BEATS // 4):
        t0 = bar * 4 * B
        ci = bar % 4
        place(music, keys([midi(m + 12) for m in chords[ci]], 4 * B), t0)
        if t0 < DROP:
            if bar >= 1:  # soft lo-fi groove under the chat
                place(drums, kick(0.55), t0)
                place(drums, kick(0.45), t0 + 2.5 * B)
                for b in (1, 3):
                    place(drums, noise_hit(0.15, 30, 0.22, 6), t0 + b * B)
                for s in range(8):
                    place(drums, noise_hit(0.04, 90, 0.08, 2), t0 + s * B / 2)
            continue
        # jersey club after the drop: boom..boom..boom.boom-boom-boom
        for step in (0, 3, 6, 10, 12, 13, 14):
            place(drums, kick(), t0 + step * B / 4)
        for b in (1, 3):
            place(drums, noise_hit(0.2, 25, 0.4, 8), t0 + b * B)
        for s in range(16):
            place(drums, noise_hit(0.04, 90, 0.11 if s % 2 else 0.07, 2), t0 + s * B / 4)
        for step in (2, 7, 11, 15):  # squeaky chirps, the jersey club signature
            place(fx, chirp(1800, 2600 if step % 2 else 1400), t0 + step * B / 4)
        place(low, bass(midi(roots[ci]), 2 * B), t0)
        place(low, bass(midi(roots[ci] + (7 if bar % 2 else 0)), 2 * B), t0 + 2 * B)

    for t, _, _ in CHAT_T:  # message pop blips
        place(fx, chirp(1100, 700, 0.08, 0.25), t)
    # riser + hard gap into the drop
    rl = 4 * B
    tr = ta(rl)
    place(fx, noise_hit(rl, 0, 0.12, 4) * (tr / rl) ** 2, DROP - rl)
    gap = slice(int((DROP - 0.1) * sr), int(DROP * sr))
    for buf in (drums, music, fx):
        buf[gap] = 0

    mix = np.tanh((drums + low * 0.9 + music + fx) * 1.3) * 0.85
    mix[-sr:] *= np.linspace(1, 0, sr)
    st = np.stack([mix, np.roll(mix, 250) * 0.98], axis=1)
    st /= np.abs(st).max() * 1.05
    with wave.open(WAV, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ───────────────────────── chat visuals ─────────────────────────

BUBBLE_MAX = 700
CHAT_TOP, CHAT_BOTTOM = 200, H - 150
GAP = 22


def wrap(text, size):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_img(trial, size, face=FONT_BOLD).width > BUBBLE_MAX - 40 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    return lines + [cur]


_bubbles = {}


def bubble(who, text):
    key = (who, text)
    if key in _bubbles:
        return _bubbles[key]
    mine = who == "me"
    fg, bgc = (BLACK, LIME) if mine else (WHITE, GREY)
    lines = [text_img(ln, 46, fill=fg, face=FONT_BOLD) for ln in wrap(text, 46)]
    lh = 64
    w = max(im.width for im in lines) + 30
    h = lh * len(lines) + 34
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=38, fill=bgc)
    tail = (w - 30, h - 34, w - 1, h - 1) if mine else (0, h - 34, 30, h - 1)
    d.rectangle(tail, fill=bgc)
    for i, im in enumerate(lines):
        img.alpha_composite(im, (6, 8 + i * lh))
    _bubbles[key] = img
    return img


def typing_bubble(who, t):
    img = Image.new("RGBA", (170, 92), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 169, 91), radius=40, fill=LIME if who == "me" else GREY)
    dot = BLACK if who == "me" else (170, 170, 180)
    for i in range(3):
        jump = 8 * max(0, math.sin(t * 9 - i * 0.9))
        d.ellipse((38 + i * 36 - 10, 46 - jump - 10, 38 + i * 36 + 10, 46 - jump + 10), fill=dot)
    return img


LAYOUT = []  # (y, height) of each chat message in content space
_y = 0
for _, who, txt in CHAT_T:
    hgt = bubble(who, txt).height + (52 if who == "bestie" else 0)  # room for name label
    LAYOUT.append((_y, hgt))
    _y += hgt + GAP
VIEW = CHAT_BOTTOM - CHAT_TOP


def scroll_offset(t):
    targets = [max(0, y + h - VIEW) for y, h in LAYOUT]
    starts = [mt - B for mt, _, _ in CHAT_T]  # scroll as soon as typing starts
    k = sum(1 for s in starts if t >= s) - 1
    if k < 0:
        return 0
    prev = targets[k - 1] if k > 0 else 0
    e = min(1, (t - starts[k]) / 0.25)
    return prev + (targets[k] - prev) * (1 - (1 - e) ** 3)


def scene_title(t):
    c = dots(BLACK, (36, 36, 42), t)
    pop(c, pill("REAL STORY", 40, PINK, WHITE), W / 2, 330, t, 0.0, rot=-4)
    pop(c, text_img("me explaining", 104, fill=WHITE, stroke=8), W / 2, 560, t, B)
    pop(c, text_img("my job to the", 104, fill=WHITE, stroke=8), W / 2, 700, t, 2 * B)
    pop(c, text_img("group chat 💬", 104, fill=LIME, stroke=8), W / 2, 840, t, 3 * B)
    return c


def scene_chat(t):
    c = dots(BLACK, (28, 28, 34), t)
    d = ImageDraw.Draw(c)
    off = scroll_offset(t)
    for (mt, who, txt), (y, hgt) in zip(CHAT_T, LAYOUT):
        top = CHAT_TOP + y - off
        if top > CHAT_BOTTOM or top + hgt < CHAT_TOP - 200:
            continue
        mine = who == "me"
        if t < mt - B:
            continue
        label_h = 0 if mine else 52
        if not mine:
            lbl = text_img("bestie 🫶", 30, fill=(150, 150, 160), face=FONT_BOLD)
            c.alpha_composite(lbl, (40, int(top)))
        if t < mt:
            tb = typing_bubble(who, t)
            x = W - 50 - tb.width if mine else 50
            c.alpha_composite(tb, (x, int(top + label_h)))
            continue
        bb = bubble(who, txt)
        s = 0.5 + 0.5 * v.ease_out_back((t - mt) / 0.2)
        bw, bh = int(bb.width * s), int(bb.height * s)
        img = bb.resize((max(1, bw), max(1, bh)), Image.BILINEAR) if s != 1 else bb
        x = W - 50 - bw if mine else 50
        c.alpha_composite(img, (int(x), int(top + label_h + (bb.height - bh))))
    # header + input bar drawn last so messages scroll underneath
    d.rectangle((0, 0, W, 170), fill=(18, 18, 22))
    d.ellipse((40, 45, 120, 125), fill=PINK)
    c.alpha_composite(text_img("🫶", 44), (48, 52))
    c.alpha_composite(text_img("the group chat", 46, face=FONT_HEAVY), (130, 40))
    c.alpha_composite(text_img("3 members · active now", 30, fill=(150, 150, 160), face=FONT_BOLD), (130, 98))
    d.rectangle((0, H - 130, W, H), fill=(18, 18, 22))
    d.rounded_rectangle((40, H - 105, W - 40, H - 30), radius=38, fill=GREY)
    c.alpha_composite(text_img("message...", 34, fill=(130, 130, 140), face=FONT_BOLD), (70, H - 95))
    return c


def scene_drop(t):
    flash = t < DROP + 0.1
    c = Image.new("RGBA", (W, H), (WHITE if flash else LIME) + (255,))
    img = text_img("say less.", 190, fill=BLACK)
    paste_center(c, img, W / 2, H / 2, scale=1 + 0.6 * math.exp(-(t - DROP) * 10))
    return c


PROJECT_TILES = [("SaveMe", "ui-mobile.svg", PINK), ("MyBts", "ui-dashboard.svg", BLUE),
                 ("cekresult", "ui-chat.svg", PURPLE), ("MySejid", "ui-kanban.svg", PINK)]


def scene_receipts(t):
    s0 = 33 * B
    c = dots(LIME, (170, 225, 0), t)
    pop(c, text_img("built by Nik Harun", 76, fill=BLACK), W / 2, 120, t, s0)
    pop(c, pill("SWE × UX researcher · 📍 KL", 36, BLACK, WHITE), W / 2, 225, t, s0 + B / 2, rot=-2)
    for i, (name, svg, col) in enumerate(PROJECT_TILES):
        cx = 290 + (i % 2) * 500
        cy = 560 + (i // 2) * 520
        st = s0 + B + i * B
        if t < st:
            continue
        card = v.svg_card(svg, max_w=400, max_h=360)
        k = v.ease_out_back((t - st) / 0.22)
        rot = (-3 if i % 2 else 3) + 1.2 * math.sin(t * 3 + i)
        paste_center(c, card, cx, cy, scale=0.3 + 0.7 * k, rot=rot)
        paste_center(c, pill(name, 38, col, WHITE), cx, cy + 210, scale=0.3 + 0.7 * k, rot=-rot)
    return c


def scene_cta(t):
    s0 = 40 * B
    c = dots(PINK, (255, 90, 170), t)
    v.marquee(c, "OPEN TO WORK", BLACK, LIME, 110, t)
    pop(c, text_img("need one too?", 110, fill=WHITE, stroke=9), W / 2, 420, t, s0)
    pop(c, text_img("slide in 📩", 110, fill=LIME, stroke=9), W / 2, 570, t, s0 + B)
    pop(c, pill("harunkamal07@gmail.com", 50, WHITE, BLACK), W / 2, 800, t, s0 + 2 * B, rot=2)
    pop(c, text_img("research → build → ship", 50, fill=BLACK), W / 2, 980, t, s0 + 3 * B)
    v.marquee(c, "NIK HARUN", BLACK, LIME, 1250, t, speed=-320, rot=5)
    return c




def dots(color, dot, t):
    img = Image.new("RGBA", (W, H), color + (255,))
    d = ImageDraw.Draw(img)
    off = (t * 40) % 90
    for y in range(-90, H + 90, 90):
        for x in range(-90, W + 90, 90):
            d.ellipse((x + off - 5, y + off - 5, x + off + 5, y + off + 5), fill=dot)
    return img


TIMELINE = [(0, scene_title), (4 * B, scene_chat), (DROP, scene_drop), (33 * B, scene_receipts), (40 * B, scene_cta)]
GRAIN = [Image.fromarray(np.random.default_rng(i).integers(0, 255, (H // 2, W // 2), dtype=np.uint8), "L")
         .resize((W, H), Image.NEAREST) for i in range(4)]


def render(t):
    scene = next(f for s, f in reversed(TIMELINE) if t >= s)
    img = scene(t).convert("RGB")
    punch = (0.045 if t >= DROP else 0.0) * math.exp(-(t % B) * 12)
    shake = 24 * (1 - (t - DROP) / 0.3) if DROP <= t < DROP + 0.3 else 0
    if punch > 0.001 or shake:
        rng = np.random.default_rng(int(t * FPS))
        dx, dy = rng.uniform(-shake, shake, 2) if shake else (0, 0)
        s = 1 + punch + shake / 250
        cw, ch = W / s, H / s
        x0 = min(max((W - cw) / 2 + dx, 0), W - cw)
        y0 = min(max((H - ch) / 2 + dy, 0), H - ch)
        img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    if any(0 <= t - s < 0.1 for s, _ in TIMELINE[1:]):
        r, g, b = img.split()
        r = r.transform(img.size, Image.AFFINE, (1, 0, 14, 0, 1, 0))
        b = b.transform(img.size, Image.AFFINE, (1, 0, -14, 0, 1, 0))
        img = Image.merge("RGB", (r, g, b))
    img = Image.blend(img, Image.merge("RGB", [GRAIN[int(t * FPS) % 4]] * 3), 0.04)
    if t > DURATION - 0.6:
        img = Image.blend(img, Image.new("RGB", img.size, BLACK), (t - (DURATION - 0.6)) / 0.6)
    return img


def main():
    if len(sys.argv) > 1:
        for a in sys.argv[1:]:
            render(float(a)).save(f"threads_preview_{float(a):05.2f}.png")
        return
    make_music()
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", WAV, "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        proc.stdin.write(render(i / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print("done ->", OUT, "exit", proc.returncode)


if __name__ == "__main__":
    main()
