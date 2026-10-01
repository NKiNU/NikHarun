"""Gen Z style 9:16 promo for Nik Harun. Renders frames with Pillow, pipes to ffmpeg."""
import io
import math
import subprocess
from functools import lru_cache

import pymupdf
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 24.0
BEAT = 0.5
DROP = 6.0
ASSETS = "C:/Users/acer/desktop/mantap-portfolio/assets/"
OUT = "C:/Users/acer/desktop/mantap-portfolio/promo/nik-harun-promo.mp4"

FONT_HEAVY = "C:/Windows/Fonts/ariblk.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"

LIME = (198, 255, 0)
PINK = (255, 46, 147)
BLUE = (45, 91, 255)
BLACK = (12, 12, 14)
WHITE = (255, 255, 255)
PURPLE = (140, 82, 255)


# ───────────────────────── text rendering ─────────────────────────

def is_emoji(c):
    o = ord(c)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0x200D, 0xFE0F)


@lru_cache(maxsize=None)
def font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(maxsize=None)
def text_img(text, size, fill=WHITE, stroke=0, stroke_fill=BLACK, face=FONT_HEAVY):
    """Render a single line, mixing a text face with colour emoji."""
    runs, cur, cur_e = [], "", None
    for c in text:
        e = is_emoji(c)
        if cur and e != cur_e:
            runs.append((cur, cur_e))
            cur = ""
        cur += c
        cur_e = e
    if cur:
        runs.append((cur, cur_e))

    tf = font(face, size)
    ef = font(FONT_EMOJI, size)
    pad = stroke + 10
    widths = []
    for r, e in runs:
        f = ef if e else tf
        b = f.getbbox(r, stroke_width=0 if e else stroke)
        widths.append(b[2] - min(b[0], 0))
    asc, desc = tf.getmetrics()
    h = asc + desc + pad * 2
    img = Image.new("RGBA", (sum(widths) + pad * 2, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for (r, e), w in zip(runs, widths):
        if e:
            d.text((x, pad + size * 0.12), r, font=ef, embedded_color=True)
        else:
            d.text((x, pad), r, font=tf, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += w
    return img


def ease_out_back(x):
    x = min(max(x, 0), 1)
    c1, c3 = 1.9, 2.9
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def paste_center(canvas, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    canvas.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def pop(canvas, img, cx, cy, t, start, rot=0.0, dur=0.22):
    """Text that 'pops' in with overshoot at `start`."""
    if t < start:
        return
    s = ease_out_back((t - start) / dur)
    paste_center(canvas, img, cx, cy, scale=0.3 + 0.7 * s, rot=rot)


@lru_cache(maxsize=None)
def pill(text, size, bg, fg, pad_x=34, pad_y=18, border=6):
    t = text_img(text, size, fill=fg, face=FONT_HEAVY)
    w, h = t.width + pad_x * 2 - 20, t.height + pad_y * 2 - 20
    img = Image.new("RGBA", (w + border * 2 + 10, h + border * 2 + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # hard drop shadow, sticker style
    d.rounded_rectangle((10, 10, w + border * 2 + 9, h + border * 2 + 9), radius=h // 2 + border, fill=BLACK)
    d.rounded_rectangle((0, 0, w + border * 2, h + border * 2), radius=h // 2 + border, fill=BLACK)
    d.rounded_rectangle((border, border, w + border, h + border), radius=h // 2, fill=bg)
    img.alpha_composite(t, (border + pad_x - 10, border + pad_y - 10))
    return img


# ───────────────────────── assets ─────────────────────────

@lru_cache(maxsize=None)
def photo_sticker():
    p = Image.open(ASSETS + "nikharun.jpg").convert("RGB").crop((300, 180, 880, 953))
    p = p.resize((600, int(600 * p.height / p.width)), Image.LANCZOS)
    b = 22
    card = Image.new("RGBA", (p.width + b * 2, p.height + b * 2 + 90), WHITE + (255,))
    card.paste(p, (b, b))
    cap = text_img("certified builder ✅", 40, fill=BLACK, face=FONT_HEAVY)
    card.alpha_composite(cap, ((card.width - cap.width) // 2, p.height + b + 8))
    shadow = Image.new("RGBA", (card.width + 30, card.height + 30), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", card.size, (0, 0, 0, 255)), (24, 24))
    shadow.alpha_composite(card, (0, 0))
    return shadow


@lru_cache(maxsize=None)
def svg_card(name, max_w=860, max_h=900):
    page = pymupdf.open(ASSETS + name)[0]
    z = min(max_w / page.rect.width, max_h / page.rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=True)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width, img.height), radius=36, fill=255)
    img.putalpha(mask)
    framed = Image.new("RGBA", (img.width + 36, img.height + 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(framed)
    d.rounded_rectangle((18, 18, img.width + 35, img.height + 35), radius=44, fill=BLACK)
    d.rounded_rectangle((0, 0, img.width + 16, img.height + 16), radius=44, fill=BLACK)
    framed.alpha_composite(img, (8, 8))
    return framed


@lru_cache(maxsize=None)
def marquee_strip(text, bg, fg):
    unit = text_img(text + "  •  ", 90, fill=fg, face=FONT_HEAVY)
    strip = Image.new("RGBA", (unit.width * 6, unit.height + 20), bg + (255,))
    for i in range(6):
        strip.alpha_composite(unit, (i * unit.width, 10))
    return strip, unit.width


def marquee(canvas, text, bg, fg, y, t, speed=320, rot=-7):
    strip, uw = marquee_strip(text, bg, fg)
    off = int((t * speed) % uw)
    band = strip.crop((off, 0, off + 1500, strip.height))
    paste_center(canvas, band, W / 2, y, rot=rot)


GRAIN = [
    Image.fromarray(np.random.default_rng(i).integers(0, 255, (H // 2, W // 2), dtype=np.uint8), "L")
    .resize((W, H), Image.NEAREST)
    for i in range(4)
]


def bg(color):
    return Image.new("RGBA", (W, H), color + (255,))


def dots_bg(color, dot, t):
    """Solid bg with a slowly drifting dot grid."""
    img = bg(color)
    d = ImageDraw.Draw(img)
    off = (t * 40) % 90
    for y in range(-90, H + 90, 90):
        for x in range(-90, W + 90, 90):
            d.ellipse((x + off - 5, y + off - 5, x + off + 5, y + off + 5), fill=dot)
    return img


# ───────────────────────── scenes ─────────────────────────

def stack_words(canvas, t, words, y0, gap, size, colors, stroke=10):
    for i, (start, word) in enumerate(words):
        img = text_img(word, size, fill=colors[i % len(colors)], stroke=stroke)
        pop(canvas, img, W / 2, y0 + i * gap, t, start, rot=(-3 if i % 2 else 3))


def scene_hook(t):
    c = dots_bg(BLACK, (40, 40, 46), t)
    pop(c, pill("POV:", 70, LIME, BLACK), W / 2, 470, t, 0.0, rot=-4)
    stack_words(c, t, [(0.5, "you need"), (1.0, "an app that"), (1.5, "actually"), (2.0, "SLAPS 💅")],
                700, 190, 120, [WHITE, WHITE, LIME, PINK])
    if t > 2.4:
        pop(c, pill("not mid. never mid.", 44, WHITE, BLACK), W / 2, 1560, t, 2.4, rot=5)
    return c


def scene_problem(t):
    c = bg(PINK)
    stack_words(c, t, [(3.0, "but did anyone"), (3.5, "ask your users"), (4.0, "what they"), (4.5, "ACTUALLY"), (5.0, "need?? 💀")],
                560, 180, 104, [WHITE, WHITE, WHITE, LIME, WHITE])
    return c


def scene_say_less(t):
    c = bg(WHITE) if t < 6.12 else bg(BLACK)
    fill = BLACK if t < 6.12 else LIME
    img = text_img("say less.", 190, fill=fill, stroke=0)
    paste_center(c, img, W / 2, H / 2, scale=1.0 + 0.6 * math.exp(-(t - 6.0) * 10))
    return c


def scene_meet(t):
    c = dots_bg(LIME, (170, 225, 0), t)
    marquee(c, "NIK HARUN", BLACK, LIME, 230, t)
    pop(c, text_img("meet", 80, fill=BLACK), W / 2, 420, t, 6.5)
    pop(c, photo_sticker(), W / 2, 1000, t, 6.6, rot=-5 + 1.5 * math.sin(t * 4), dur=0.3)
    pop(c, pill("software engineer × UX researcher", 40, PINK, WHITE), W / 2, 1560, t, 7.0, rot=3)
    pop(c, pill("📍 Kuala Lumpur", 40, WHITE, BLACK), W / 2 - 160, 1700, t, 7.5, rot=-4)
    marquee(c, "OPEN TO WORK", BLACK, LIME, 1850, t, speed=-320, rot=4)
    return c


MOVES = [
    (8.0, BLUE, "01", "FIND OUT 🔍", ["interviews + usability tests", "no guessing. just facts."], LIME),
    (10.0, BLACK, "02", "MAKE IT REAL ⚡", ["AI-powered prototype", "clickable in a week fr"], PINK),
    (12.0, PURPLE, "03", "SHIP IT 🚀", ["tested. accessible. measured.", "it just works™"], LIME),
]


def scene_moves(t):
    for start, color, num, title, lines, accent in reversed(MOVES):
        if t >= start:
            break
    c = dots_bg(color, tuple(min(255, v + 30) for v in color), t)
    pop(c, pill("HOW I COOK 🔥", 46, WHITE, BLACK), W / 2, 260, t, start, rot=-3)
    pop(c, text_img(num, 380, fill=accent, stroke=0), W / 2, 640, t, start)
    pop(c, text_img(title, 110, fill=WHITE, stroke=10), W / 2, 1000, t, start + 0.25)
    for i, ln in enumerate(lines):
        pop(c, text_img(ln, 58, fill=WHITE, stroke=7, face=FONT_BOLD), W / 2, 1220 + i * 100, t, start + 0.75 + i * 0.25)
    return c


PROJECTS = [
    ("SaveMe", "ui-mobile.svg", "where did my money go?? 💸", "Java · Firebase", PINK),
    ("MyBts", "ui-dashboard.svg", "track student progress 📚", "React · Express", BLUE),
    ("cekresult", "ui-chat.svg", "AI learning path 🧠", "Java · Postgres · Gemini", PURPLE),
    ("MySejid", "ui-kanban.svg", "connect with your kariah 🕌", "React · Express", PINK),
]
PROJ_START, PROJ_LEN = 14.5, 1.125


def scene_projects(t):
    if t < PROJ_START:
        c = bg(BLACK)
        img = text_img("the receipts 🧾", 130, fill=LIME, stroke=0)
        paste_center(c, img, W / 2, H / 2, scale=1.0 + 0.5 * math.exp(-(t - 14.0) * 10))
        return c
    i = min(int((t - PROJ_START) / PROJ_LEN), len(PROJECTS) - 1)
    name, svg, line, stack, color = PROJECTS[i]
    s0 = PROJ_START + i * PROJ_LEN
    c = dots_bg(color, tuple(min(255, v + 30) for v in color), t)
    pop(c, pill(f"{i + 1}/4", 40, WHITE, BLACK), 150, 170, t, s0)
    pop(c, text_img(name, 140, fill=WHITE, stroke=12), W / 2, 330, t, s0)
    # card slides in from the right, then sways
    k = min(1, (t - s0) / 0.25)
    x = W / 2 + (1 - ease_out_back(k)) * 900
    paste_center(c, svg_card(svg), x, 930, rot=2 * math.sin((t - s0) * 3))
    pop(c, pill(line, 48, LIME, BLACK), W / 2, 1520, t, s0 + 0.3, rot=-3)
    pop(c, text_img(stack, 44, fill=WHITE, stroke=6, face=FONT_BOLD), W / 2, 1680, t, s0 + 0.45)
    return c


CHIPS = [
    ("React", PINK), ("Node.js", LIME), ("Java", WHITE), ("Express", BLUE), ("MongoDB", LIME),
    ("Claude Code 🤖", PINK), ("UX research", WHITE), ("vibe coding ✨", PURPLE), ("ASP.NET", LIME),
    ("REST APIs", WHITE), ("user interviews", PINK), ("Git", LIME),
]


def scene_stack(t):
    c = dots_bg(BLACK, (40, 40, 46), t)
    pop(c, text_img("the stack 🧠", 120, fill=LIME, stroke=0), W / 2, 280, t, 19.0)
    for i, (label, col) in enumerate(CHIPS):
        start = 19.15 + i * 0.12
        row, colm = divmod(i, 2)
        x = 300 + colm * 480 + (40 if row % 2 else -40)
        y = 560 + row * 210
        fg = BLACK if col in (LIME, WHITE) else WHITE
        drop = max(0, 1 - (t - start) / 0.3)
        if t >= start:
            paste_center(c, pill(label, 46, col, fg), x, y - drop * 500, rot=((i * 37) % 11) - 5)
    return c


def scene_cta(t):
    c = dots_bg(PINK, (255, 90, 170), t)
    marquee(c, "NO CAP", BLACK, PINK, 170, t)
    glow = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 2)
    if t >= 21.25:
        paste_center(c, pill("● OPEN TO WORK", 70, LIME, BLACK), W / 2, 520, scale=1 + 0.04 * glow, rot=-3)
    else:
        pop(c, pill("● OPEN TO WORK", 70, LIME, BLACK), W / 2, 520, t, 21.0, rot=-3)
    pop(c, text_img("slide into", 120, fill=WHITE, stroke=10), W / 2, 820, t, 21.5)
    pop(c, text_img("my inbox 📩", 120, fill=WHITE, stroke=10), W / 2, 990, t, 21.75)
    pop(c, pill("harunkamal07@gmail.com", 50, WHITE, BLACK), W / 2, 1260, t, 22.0, rot=2)
    pop(c, text_img("research → build → ship", 54, fill=BLACK, face=FONT_HEAVY), W / 2, 1480, t, 22.5)
    marquee(c, "NIK HARUN", BLACK, LIME, 1780, t, speed=-320, rot=5)
    return c


TIMELINE = [
    (0.0, scene_hook), (3.0, scene_problem), (6.0, scene_say_less), (6.5, scene_meet),
    (8.0, scene_moves), (14.0, scene_projects), (19.0, scene_stack), (21.0, scene_cta),
]


# ───────────────────────── camera fx ─────────────────────────

def render(t):
    scene = next(f for start, f in reversed(TIMELINE) if t >= start)
    img = scene(t).convert("RGB")

    # zoom punch on every beat (harder after the drop) + shake building into the drop
    since = t % BEAT
    punch = (0.05 if t >= DROP else 0.018) * math.exp(-since * 12)
    shake = 0.0
    if 4.5 <= t < DROP:
        shake = 6 + 26 * (t - 4.5) / 1.5
    elif DROP <= t < DROP + 0.3:
        shake = 30 * (1 - (t - DROP) / 0.3)
    if punch > 0.001 or shake:
        rng = np.random.default_rng(int(t * FPS))
        dx, dy = (rng.uniform(-shake, shake, 2) if shake else (0, 0))
        s = 1 + punch + shake / 250
        cw, ch = W / s, H / s
        x0 = min(max((W - cw) / 2 + dx, 0), W - cw)
        y0 = min(max((H - ch) / 2 + dy, 0), H - ch)
        img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

    # RGB split glitch on scene cuts
    cuts = [s for s, _ in TIMELINE] + [10.0, 12.0] + [PROJ_START + i * PROJ_LEN for i in range(1, 4)]
    if any(0 <= t - c < 0.1 for c in cuts) and t > 0.2:
        r, g, b = img.split()
        r = r.transform(img.size, Image.AFFINE, (1, 0, 14, 0, 1, 0))
        b = b.transform(img.size, Image.AFFINE, (1, 0, -14, 0, 1, 0))
        img = Image.merge("RGB", (r, g, b))

    # film grain
    img = Image.blend(img, Image.merge("RGB", [GRAIN[int(t * FPS) % 4]] * 3), 0.05)

    # fade to black at the end
    if t > DURATION - 0.6:
        img = Image.blend(img, Image.new("RGB", img.size, BLACK), (t - (DURATION - 0.6)) / 0.6)
    return img


def main(preview_times=None):
    if preview_times:
        for pt in preview_times:
            render(pt).save(f"preview_{pt:05.2f}.png")
        return
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "C:/Users/acer/desktop/mantap-portfolio/promo/music.wav", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = int(DURATION * FPS)
    for i in range(n):
        proc.stdin.write(render(i / FPS).tobytes())
        if i % 60 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done ->", OUT, "exit", proc.returncode)


if __name__ == "__main__":
    import sys
    main([float(a) for a in sys.argv[1:]] or None)
