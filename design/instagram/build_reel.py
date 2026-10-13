#!/usr/bin/env python3
"""Builds the Instagram reel (1080x1920 MP4) and feed post (1080x1350 PNG) for Amberloom 1.1.

Everything is drawn from the full-resolution app screenshots in design/screenshots-1.1
and the doodle layers in design/canva-layers, so the phones stay sharp (no Canva resampling).

    python3 design/instagram/build_reel.py          # writes design/instagram/out/
    python3 design/instagram/build_reel.py --lang en

Needs Pillow and ffmpeg.
"""
import argparse
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SHOTS = os.path.join(ROOT, "design", "screenshots-1.1")
LAYERS = os.path.join(ROOT, "design", "canva-layers")
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "out")

W, H = 1080, 1920
FPS = 30
DURATION = 15.0

WHITE = (255, 255, 255)
ACCENT = (201, 122, 30)          # WidgetPalette.defaultAccentHex #C97A1E
WARM = (250, 246, 240)           # WidgetPalette.warmBackground #FAF6F0
CREAM = (255, 234, 192)          # site badge colour #FFEAC0
DARK = (44, 26, 14)              # site text colour #2C1A0E

COPY = {
    "pl": {
        "s0": "Zapisuj małe\nchwile dziecka.",
        "s0_sub": "Jedno pytanie dziennie.",
        "badge": "Nowość\nw 1.1",
        "s1": "Zapisuj, jak\nrośnie i co kocha.",
        "s2": "Pytanie dnia\ni fakty na ekranie\npoczątkowym.",
        "w_question_title": "Pytanie dnia: Ania",
        "w_question": "Co dziś najbardziej Cię rozśmieszyło?",
        "w_answer": "Odpowiedz",
        "w_height": "📏 Wzrost",
        "w_height_value": "133 cm",
        "w_height_when": "dzisiaj",
        "w_text": "🎨 Ulubiony kolor",
        "w_text_value": "Zielony",
        "w_text_since": "od 12 marca 2026",
        "w_text_ago": "3 miesiące temu",
        "tagline": "Prywatny dziennik\nwspomnień dziecka",
        "cta": "Pobierz za darmo w App Store",
        "url": "amberloom.app",
        "post_title": "Nowość w Amberloom:\nfakty i widgety.",
        "post_sub": "Wzrost, ulubione rzeczy i pytanie dnia\nna ekranie początkowym.",
    },
    "en": {
        "s0": "Keep your child's\nlittle moments.",
        "s0_sub": "One question a day.",
        "badge": "New\nin 1.1",
        "s1": "Track how they grow\nand what they love.",
        "s2": "Today's question\nand facts on your\nHome Screen.",
        "w_question_title": "Question of the day: Emma",
        "w_question": "What made you laugh the most today?",
        "w_answer": "Answer",
        "w_height": "📏 Height",
        "w_height_value": "133 cm",
        "w_height_when": "today",
        "w_text": "🎨 Favourite colour",
        "w_text_value": "Green",
        "w_text_since": "since 12 March 2026",
        "w_text_ago": "3 months ago",
        "tagline": "A private journal of\nyour child's moments",
        "cta": "Download free on the App Store",
        "url": "amberloom.app",
        "post_title": "New in Amberloom:\nfacts and widgets.",
        "post_sub": "Height, favourite things and today's\nquestion on your Home Screen.",
    },
}

HEIGHTS = [118, 121, 123.5, 126, 129, 131.5, 133]  # marketing demo data, oldest first


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def head_font(size):
    return font("BricolageGrotesque-Bold.ttf", size)


# ---------- easing ----------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def ease_back(p, s=1.6):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


# ---------- building blocks ----------

def gradient_strip(width, height, stops):
    """Horizontal gradient through (x, rgb) stops, like the App Store backgrounds."""
    row = Image.new("RGB", (width, 1))
    px = row.load()
    for x in range(width):
        for (x0, c0), (x1, c1) in zip(stops, stops[1:]):
            if x0 <= x <= x1:
                f = (x - x0) / max(1, x1 - x0)
                px[x, 0] = tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
                break
    strip = row.resize((width, height), Image.NEAREST)
    # A soft diagonal light, so the background isn't flat.
    glow = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(glow)
    for i in range(0, width, 1080):
        d.ellipse((i - 300, -500, i + 900, 700), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    light = Image.new("RGB", (width, height), (255, 170, 60))
    return Image.composite(light, strip, glow.point(lambda v: int(v * 0.45)))


def text_block(text, fnt, fill=WHITE, align="center", spacing=0.08, tracking=0):
    """Multi-line text on a transparent canvas, tight line height like the App Store headlines."""
    lines = text.split("\n")
    asc, desc = fnt.getmetrics()
    lh = int((asc + desc) * (1 + spacing) - fnt.size * 0.12)

    def line_w(s):
        return fnt.getlength(s) + tracking * max(0, len(s) - 1)

    width = int(max(line_w(l) for l in lines)) + 20
    height = lh * len(lines) + desc + 10
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        lw = line_w(l)
        x = {"center": (width - lw) / 2, "left": 0, "right": width - lw}[align]
        if tracking:
            for ch in l:
                d.text((x, i * lh), ch, font=fnt, fill=fill)
                x += fnt.getlength(ch) + tracking
        else:
            d.text((x, i * lh), l, font=fnt, fill=fill)
    return im


def rounded_mask(size, radius, scale=4):
    w, h = size
    m = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * scale - 1, h * scale - 1), radius * scale, fill=255)
    return m.resize(size, Image.LANCZOS)


def drop_shadow(im, blur=40, offset=(0, 30), opacity=0.45):
    pad = blur * 3
    w, h = im.size
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: int(v * opacity))
    sh.paste((20, 0, 0, 255), (pad + offset[0], pad + offset[1]), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(im, (pad, pad))
    return out, pad


def phone(shot_name, width):
    """An iPhone-style frame around a full-resolution screenshot, downscaled once with LANCZOS."""
    shot = Image.open(os.path.join(SHOTS, shot_name)).convert("RGBA")
    bezel = round(width * 0.035)
    sw = width - 2 * bezel
    sh = round(shot.height * sw / shot.width)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    h = sh + 2 * bezel
    body = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    body.paste((22, 18, 16, 255), (0, 0), rounded_mask((width, h), round(width * 0.15)))
    # Thin lighter rim, like the titanium edge.
    rim = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle((1, 1, width - 2, h - 2), round(width * 0.15), outline=(90, 80, 74, 255), width=3)
    body.alpha_composite(rim)
    body.paste(shot, (bezel, bezel), rounded_mask((sw, sh), round(sw * 0.125)))
    return drop_shadow(body, blur=45, offset=(0, 40), opacity=0.55)


def starburst(text, size, fill=CREAM, ink=(191, 88, 0)):
    """The "Nowość w 1.1" badge from the website's Facts card."""
    s = 4
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c = size * s / 2
    pts = []
    n = 14
    for i in range(n * 2):
        r = c * (0.98 if i % 2 == 0 else 0.84)
        a = math.pi * i / n
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=fill)
    im = big.resize((size, size), Image.LANCZOS)
    t = text_block(text, head_font(int(size * 0.2)), fill=ink, spacing=0.0)
    im.alpha_composite(t, ((size - t.width) // 2, (size - t.height) // 2 + 4))
    return im


def accent_card(size, radius):
    """AccentBackground from the widgets: accent over warm background, fading to 70%."""
    w, h = size
    base = Image.new("RGB", size, WARM)
    grad = Image.new("L", size)
    gp = grad.load()
    for y in range(h):
        for x in range(0, w):
            f = (x / w + y / h) / 2
            gp[x, y] = int(255 * (1 - 0.3 * f))
    card = Image.composite(Image.new("RGB", size, ACCENT), base, grad).convert("RGBA")
    card.putalpha(rounded_mask(size, radius))
    return card


def emoji_text(d, xy, text, fnt, fill):
    """Pillow can't draw colour emoji here, so the emoji prefix is dropped on widget labels."""
    clean = text.split(" ", 1)[1] if text[:1] and ord(text[0]) > 0x2000 else text
    d.text(xy, clean, font=fnt, fill=fill)


def question_widget(c, scale):
    w, h = int(338 * scale), int(158 * scale)
    card = accent_card((w, h), int(23 * scale))
    d = ImageDraw.Draw(card)
    p = int(16 * scale)
    d.text((p, p), c["w_question_title"], font=font("Inter-SemiBold.otf", int(12 * scale)), fill=(255, 255, 255, 230))
    q = text_block(wrap(c["w_question"], font("Lora-Italic.ttf", int(17 * scale)), w - 2 * p),
                   font("Lora-Italic.ttf", int(17 * scale)), align="left", spacing=0.1)
    card.alpha_composite(q, (p, p + int(24 * scale)))
    d.text((p, h - p - int(15 * scale)), c["w_answer"], font=font("Inter-SemiBold.otf", int(13 * scale)), fill=WHITE)
    return card


def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        nxt = (cur + " " + wd).strip()
        if fnt.getlength(nxt) > max_w and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = nxt
    lines.append(cur)
    return "\n".join(lines)


def height_widget(c, scale):
    w = h = int(158 * scale)
    card = accent_card((w, h), int(23 * scale))
    d = ImageDraw.Draw(card)
    p = int(16 * scale)
    emoji_text(d, (p, p), c["w_height"], font("Inter-SemiBold.otf", int(12 * scale)), (255, 255, 255, 205))
    cx, cy, r = w - p - int(6 * scale), p + int(7 * scale), int(6 * scale)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 230))
    d.line((cx - r * 0.5, cy, cx + r * 0.5, cy), fill=ACCENT, width=max(2, int(1.6 * scale)))
    d.line((cx, cy - r * 0.5, cx, cy + r * 0.5), fill=ACCENT, width=max(2, int(1.6 * scale)))
    d.text((p, p + int(18 * scale)), c["w_height_value"], font=head_font(int(24 * scale)), fill=WHITE)
    d.text((p, p + int(48 * scale)), c["w_height_when"], font=font("Inter-Medium.otf", int(11 * scale)), fill=(255, 255, 255, 225))
    # Line chart of the demo heights.
    x0, x1 = p, w - p
    y0, y1 = h - p, p + int(72 * scale)
    lo, hi = min(HEIGHTS) - 1, max(HEIGHTS) + 1
    pts = [(x0 + (x1 - x0) * i / (len(HEIGHTS) - 1), y0 - (y0 - y1) * (v - lo) / (hi - lo)) for i, v in enumerate(HEIGHTS)]
    d.line(pts, fill=WHITE, width=max(3, int(2.2 * scale)), joint="curve")
    for x, y in pts:
        rr = int(2.6 * scale)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=WHITE)
    return card


def text_widget(c, scale):
    w = h = int(158 * scale)
    card = accent_card((w, h), int(23 * scale))
    d = ImageDraw.Draw(card)
    p = int(16 * scale)
    emoji_text(d, (p, p), c["w_text"], font("Inter-SemiBold.otf", int(12 * scale)), (255, 255, 255, 205))
    d.text((p, p + int(42 * scale)), c["w_text_value"], font=font("Lora-Regular.ttf", int(22 * scale)), fill=WHITE)
    d.text((p, p + int(80 * scale)), c["w_text_since"], font=font("Inter-SemiBold.otf", int(11 * scale)), fill=(255, 255, 255, 220))
    d.text((p, p + int(96 * scale)), c["w_text_ago"], font=font("Inter-Medium.otf", int(10 * scale)), fill=(255, 255, 255, 215))
    return card


def white_doodle(name, width):
    im = Image.open(os.path.join(LAYERS, name)).convert("RGBA")
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def pill(text, fnt, fg, bg, pad=(46, 24)):
    tw = int(fnt.getlength(text))
    asc, desc = fnt.getmetrics()
    w, h = tw + 2 * pad[0], asc + desc + 2 * pad[1] - 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.paste(bg + (255,), (0, 0), rounded_mask((w, h), h // 2))
    ImageDraw.Draw(im).text((pad[0], pad[1] - 4), text, font=fnt, fill=fg)
    return im


# ---------- compositing helpers ----------

def with_alpha(im, a):
    if a >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


def place(frame, im, x, y, alpha=1.0, scale=1.0, anchor="tl"):
    """Composite im at (x, y), optionally scaled about its centre and faded."""
    if alpha <= 0.001 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.001:
        cx, cy = x + im.width / 2, y + im.height / 2
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        x, y = cx - im.width / 2, cy - im.height / 2
    im = with_alpha(im, alpha)
    x, y = round(x), round(y)
    # Clip to the frame so alpha_composite accepts it.
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, W - x), min(im.height, H - y)
    if r <= l or b <= t:
        return
    frame.alpha_composite(im.crop((l, t, r, b)), (x + l, y + t))


def wipe(im, p):
    """Reveal a doodle from left to right, like it's being drawn."""
    if p >= 0.999:
        return im
    out = im.copy()
    a = out.getchannel("A")
    cut = int(im.width * p)
    ImageDraw.Draw(a).rectangle((cut, 0, im.width, im.height), fill=0)
    out.putalpha(a)
    return out


# ---------- the reel ----------

SCENE_T = [0.0, 4.0, 8.4, 12.0]          # when each scene's elements start
PANS = [(3.6, 4.3), (8.0, 8.7), (11.6, 12.3)]  # camera moves to the next scene


def camera_x(t):
    x = 0.0
    for i, (a, b) in enumerate(PANS):
        x += W * ease_in_out(prog(t, a, b - a))
    return x


def build_assets(lang):
    c = COPY[lang]
    A = {}
    A["bg"] = gradient_strip(W * 4, H, [(0, (250, 112, 12)), (1080, (238, 70, 0)), (2160, (175, 24, 0)),
                                       (3240, (100, 4, 0)), (4320, (48, 0, 0))]).convert("RGBA")
    A["h0"] = text_block(c["s0"], head_font(118), tracking=-3)
    A["sub0"] = pill(c["s0_sub"], font("Inter-SemiBold.otf", 40), (191, 88, 0), WHITE)
    A["p0"] = phone(f"{lang}_1_timeline.png", 760)
    A["rays"] = white_doodle(f"doodle_{lang}5_0.png", 300)
    A["badge"] = starburst(c["badge"], 220)
    A["h1"] = text_block(c["s1"], head_font(108), tracking=-3)
    A["under"] = white_doodle(f"doodle_{lang}6_0.png", 640)
    A["p1b"] = phone(f"{lang}_7_height.png", 760)
    A["h2"] = text_block(c["s2"], head_font(104), tracking=-3)
    scale = 2.75
    A["wq"], _ = drop_shadow(question_widget(c, scale), blur=30, offset=(0, 24), opacity=0.5)
    A["wh"], _ = drop_shadow(height_widget(c, scale), blur=30, offset=(0, 24), opacity=0.5)
    A["wt"], _ = drop_shadow(text_widget(c, scale), blur=30, offset=(0, 24), opacity=0.5)
    A["widget_pad"] = 90
    icon = Image.open(os.path.join(HERE, "app_icon.png")).convert("RGBA").resize((300, 300), Image.LANCZOS)
    icon.putalpha(rounded_mask((300, 300), 68))
    A["icon"], _ = drop_shadow(icon, blur=40, offset=(0, 26), opacity=0.6)
    A["name"] = text_block("Amberloom", head_font(150), tracking=-4)
    A["tag"] = text_block(c["tagline"], font("Lora-Italic.ttf", 64), spacing=0.15)
    A["cta"] = pill(c["cta"], font("Inter-SemiBold.otf", 44), (191, 88, 0), WHITE, pad=(56, 32))
    A["url"] = text_block(c["url"], font("Inter-Medium.otf", 40), fill=(255, 225, 200))
    return A


def render_frame(t, A, cam=None):
    cam = camera_x(t) if cam is None else cam
    frame = A["bg"].crop((round(cam), 0, round(cam) + W, H))

    def sx(scene, x):
        return scene * W + x - cam

    # Scene 0: daily question + timeline
    lt = t - SCENE_T[0]
    if cam < W * 1.0:
        p = ease_out(prog(lt, 0.15, 0.7))
        place(frame, A["h0"], sx(0, (W - A["h0"].width) / 2), 150 + 40 * (1 - p), alpha=p)
        p = ease_back(prog(lt, 0.9, 0.5))
        place(frame, A["sub0"], sx(0, (W - A["sub0"].width) / 2), 470, alpha=clamp(p), scale=0.6 + 0.4 * p)
        ph, pad = A["p0"]
        p = ease_out(prog(lt, 0.35, 1.0))
        place(frame, ph, sx(0, (W - ph.width) / 2), 640 - pad + 900 * (1 - p) - 25 * math.sin(clamp(lt - 1.35, 0, 2.3) * 1.3))
        p = ease_back(prog(lt, 1.2, 0.5))
        place(frame, A["rays"], sx(0, W - 270), -30, alpha=clamp(p), scale=0.4 + 0.6 * p)

    # Scene 1: Facts
    lt = t - SCENE_T[1]
    if W * 0.0 < cam + W and cam < W * 2.0:
        p = ease_out(prog(lt, -0.3, 0.7))
        place(frame, A["h1"], sx(1, (W - A["h1"].width) / 2), 230 + 40 * (1 - p), alpha=p)
        place(frame, wipe(A["under"], ease_out(prog(lt, 0.4, 0.6))), sx(1, (W - A["under"].width) / 2), 510)
        ph, pad = A["p1b"]
        p = ease_out(prog(lt, -0.4, 1.0))
        y = 700 - pad + 900 * (1 - p) - 25 * math.sin(clamp(lt - 0.6, 0, 3) * 1.0)
        place(frame, ph, sx(1, (W - ph.width) / 2), y)
        p = ease_back(prog(lt, 0.3, 0.55), 2.2)
        place(frame, A["badge"].rotate(-12 + 12 * (1 - clamp(p)), Image.BICUBIC, expand=False),
              sx(1, 830), 6, alpha=clamp(p * 1.5), scale=max(0.01, p))

    # Scene 2: widgets
    lt = t - SCENE_T[2]
    if cam + W > W * 2.0 and cam < W * 3.0:
        p = ease_out(prog(lt, -0.3, 0.7))
        place(frame, A["h2"], sx(2, (W - A["h2"].width) / 2), 170 + 40 * (1 - p), alpha=p)
        pad = A["widget_pad"]
        wq, wh, wt = A["wq"], A["wh"], A["wt"]
        inner_w = wq.width - 2 * pad
        left = (W - inner_w) / 2
        gap = inner_w - 2 * (wh.width - 2 * pad)
        y_top = 690
        for i, (im, x, y) in enumerate([(wq, left, y_top),
                                        (wh, left, y_top + (wq.height - 2 * pad) + gap),
                                        (wt, left + (wh.width - 2 * pad) + gap, y_top + (wq.height - 2 * pad) + gap)]):
            p = ease_back(prog(lt, 0.25 + 0.3 * i, 0.55))
            bob = 8 * math.sin((lt - i) * 1.6)
            place(frame, im, sx(2, x - pad), y - pad + bob, alpha=clamp(p * 1.4), scale=max(0.01, 0.5 + 0.5 * p))

    # Scene 3: end card
    lt = t - SCENE_T[3]
    if cam + W > W * 3.0:
        p = ease_back(prog(lt, -0.1, 0.6))
        icon = A["icon"]
        place(frame, icon, sx(3, (W - icon.width) / 2), 330, alpha=clamp(p * 1.4), scale=max(0.01, 0.5 + 0.5 * p))
        p = ease_out(prog(lt, 0.35, 0.6))
        place(frame, A["name"], sx(3, (W - A["name"].width) / 2), 790 + 30 * (1 - p), alpha=p)
        p = ease_out(prog(lt, 0.6, 0.6))
        place(frame, A["tag"], sx(3, (W - A["tag"].width) / 2), 1010 + 30 * (1 - p), alpha=p)
        p = ease_back(prog(lt, 1.0, 0.55))
        place(frame, A["cta"], sx(3, (W - A["cta"].width) / 2), 1330, alpha=clamp(p * 1.4), scale=max(0.01, 0.7 + 0.3 * p))
        p = ease_out(prog(lt, 1.3, 0.5))
        place(frame, A["url"], sx(3, (W - A["url"].width) / 2), 1500, alpha=p)

    return frame.convert("RGB")


def render_video(lang, A, path):
    n = int(DURATION * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(render_frame(i / FPS, A).tobytes())
    proc.stdin.close()
    proc.wait()


def render_post(lang, A, path):
    """Static 1080x1350 feed post: Facts phone + widgets."""
    c = COPY[lang]
    PW, PH = 1080, 1350
    bg = gradient_strip(PW, PH, [(0, (245, 96, 6)), (PW, (150, 16, 0))]).convert("RGBA")
    title = text_block(c["post_title"], head_font(92), tracking=-3)
    bg.alpha_composite(title, ((PW - title.width) // 2, 70))
    sub = text_block(c["post_sub"], font("Lora-Italic.ttf", 40), spacing=0.15, fill=(255, 236, 214))
    bg.alpha_composite(sub, ((PW - sub.width) // 2, 70 + title.height + 10))
    ph, pad = phone(f"{lang}_7_height.png", 560)
    top = 480
    bg.alpha_composite(ph.crop((0, 0, ph.width, min(ph.height, PH - top + pad))), (40 - pad + 20, top - pad))
    scale = 2.0
    wh, wpad = drop_shadow(height_widget(c, scale), blur=26, offset=(0, 20), opacity=0.5)
    wt, _ = drop_shadow(text_widget(c, scale), blur=26, offset=(0, 20), opacity=0.5)
    bg.alpha_composite(wh, (640 - wpad, 560 - wpad))
    bg.alpha_composite(wt, (640 - wpad, 920 - wpad))
    badge = starburst(c["badge"], 190).rotate(12, Image.BICUBIC)
    bg.alpha_composite(badge, (6, 410))
    bg.convert("RGB").save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="pl", choices=sorted(COPY))
    ap.add_argument("--stills", action="store_true", help="only write preview stills")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    A = build_assets(args.lang)
    for t in (2.5, 5.0, 7.5, 10.5, 14.5):
        render_frame(t, A).save(os.path.join(OUT, f"reel_{args.lang}_t{t:04.1f}.png"))
    render_post(args.lang, A, os.path.join(OUT, f"post_{args.lang}_1080x1350.png"))
    if not args.stills:
        render_video(args.lang, A, os.path.join(OUT, f"reel_{args.lang}_1080x1920.mp4"))


if __name__ == "__main__":
    main()
