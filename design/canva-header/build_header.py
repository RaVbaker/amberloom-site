"""Build App Store product-page header (4320x1080) layers + previews from the screenshot layers."""
import json, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'canva-layers')
OUT = HERE
PREV = os.path.join(HERE, 'preview')
W, H = 4320, 1080
FW = 640                      # phone frame width in header px
ORDER = [4, 2, 3, 5]          # screenshot pages used, left to right
GAP = 190
TOPS = [210, 110, 110, 210]   # frame tops (arch)
SH_OFF, SH_BLUR, SH_ALPHA = 28, 38, 0.42

os.makedirs(OUT, exist_ok=True); os.makedirs(PREV, exist_ok=True)

def background():
    stops = [(0, (249, 87, 0)), (.33, (209, 43, 0)), (.58, (171, 1, 0)), (.82, (112, 0, 0)), (1, (66, 0, 0))]
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    t = (x + 0.6 * y) / (W + 0.6 * H)
    img = np.zeros((H, W, 3), np.float32)
    ts = [s[0] for s in stops]
    for c in range(3):
        img[..., c] = np.interp(t, ts, [s[1][c] for s in stops])
    return Image.fromarray(img.round().astype(np.uint8), 'RGB')

def clean_phone(lang, page):
    im = Image.open(f'{SRC}/phone_{lang}{page}.png').convert('RGBA')
    a = np.asarray(im)[..., 3].astype(np.float32)
    # drop the baked shadow: keep only (near) opaque pixels, rescale the antialiased edge
    a2 = np.clip((a - 110) * 255 / 145, 0, 255)
    if page == 2:  # drop the tilted phone peeking out behind on the left
        a2[:, :138] = 0; a2[2236:, :] = 0
    lab, n = ndimage.label(a2 > 0)
    cy, cx = a.shape[0] // 3, a.shape[1] // 2
    keep = lab == lab[cy, cx]
    if page == 3:  # books are a separate blob overlapping the phone: keep blobs touching the phone's bottom-right
        sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        for i, s in enumerate(sizes, 1):
            if s > 20000: keep |= lab == i
    a2 *= keep
    arr = np.asarray(im).copy(); arr[..., 3] = a2.round().astype(np.uint8)
    out = Image.fromarray(arr, 'RGBA')
    m = (a2 > 200)
    ys, xs = np.where(m[: a.shape[0] // 2])
    frame = (xs.min(), ys.min(), xs.max())  # left, top, right of frame
    return out.crop(out.getbbox()), frame, out.getbbox()

def with_shadow(ph):
    pad = SH_BLUR * 3
    w, h = ph.size
    can = Image.new('RGBA', (w + 2 * pad, h + 2 * pad + SH_OFF), (0, 0, 0, 0))
    a = ph.split()[3]
    sh = Image.new('L', can.size, 0); sh.paste(a, (pad, pad + SH_OFF))
    sh = sh.filter(ImageFilter.GaussianBlur(SH_BLUR)).point(lambda v: int(v * SH_ALPHA))
    blk = Image.new('RGBA', can.size, (20, 0, 0, 255)); blk.putalpha(sh)
    can = Image.alpha_composite(can, blk)
    can.alpha_composite(ph, (pad, pad))
    return can, pad

def white_only(d):
    a = np.asarray(d).astype(np.float32)
    m = np.clip((a[..., :3].min(2) - 90) / 165, 0, 1)
    out = np.zeros_like(a); out[..., :3] = 255; out[..., 3] = a[..., 3] * m
    return Image.fromarray(out.round().astype(np.uint8), 'RGBA')

# (file, name, anchor, x, y, scale, mirror): anchor 'tl'/'tr'/'br'/'bl' pins that corner of the doodle to (x, y)
DOODLES = [
    ('doodle_en5_0', 'rays_r', 'tr', W, 0, 1.25, False),        # rays from the top-right corner, as on page 5
    ('doodle_en5_0', 'rays_l', 'tl', 0, 0, 1.25, True),         # mirrored, top-left corner
    ('doodle_en1_1', 'sparkle_l', 'bl', 0, 1040, 1.35, False),  # page 1 sparkle, on the left edge as on page 1
    ('doodle_en1_1', 'sparkle_r', 'br', W, 1040, 1.35, True),     # page 1 sparkle, mirrored to the right edge
]

def build(lang):
    layers = []
    bg = background(); bg.save(f'{OUT}/header_bg.png')
    layers.append(dict(src='header_bg.png', left=0, top=0, width=W, height=H))
    comp = bg.convert('RGBA')
    total = len(ORDER) * FW + (len(ORDER) - 1) * GAP
    x0 = (W - total) // 2
    for i, page in enumerate(ORDER):
        ph, (fl, ft, fr), bbox = clean_phone(lang, page)
        s = FW / (fr - fl + 1)
        # frame coords relative to the cropped image
        fl -= bbox[0]; ft -= bbox[1]
        # keep only what can be visible: crop the bottom
        vis_h = int((H - TOPS[i]) / s) + ft + 10
        ph = ph.crop((0, 0, ph.width, min(ph.height, vis_h)))
        ph = ph.resize((round(ph.width * s), round(ph.height * s)), Image.LANCZOS)
        ph, pad = with_shadow(ph)
        left = round(x0 + i * (FW + GAP) - fl * s - pad)
        top = round(TOPS[i] - ft * s - pad)
        # clip to the canvas so Canva gets a tidy box
        cl = max(0, -left); ct = max(0, -top)
        ph = ph.crop((cl, ct, min(ph.width, W - left), min(ph.height, H - top)))
        left += cl; top += ct
        name = f'header_phone_{lang}{i + 1}.png'; ph.save(f'{OUT}/{name}')
        layers.append(dict(src=name, left=left, top=top, width=ph.width, height=ph.height))
        comp.alpha_composite(ph, (left, top))
    for f, nm, anc, ax, ay, sc, mir in DOODLES:
        d = white_only(Image.open(f'{SRC}/{f}.png').convert('RGBA'))
        if mir: d = d.transpose(Image.FLIP_LEFT_RIGHT)
        d = d.resize((round(d.width * sc), round(d.height * sc)), Image.LANCZOS)
        name = f'header_doodle_{nm}.png'; d.save(f'{OUT}/{name}')
        left = ax - d.width if 'r' in anc else ax
        top = ay - d.height if 'b' in anc else ay
        layers.append(dict(src=name, left=left, top=top, width=d.width, height=d.height))
        comp.alpha_composite(d, (left, top))
    comp.convert('RGB').save(f'{PREV}/header_{lang}.png')
    return layers

pos = {lang: build(lang) for lang in ['en', 'pl']}
json.dump(pos, open(f'{OUT}/positions.json', 'w'), indent=1)
print(json.dumps(pos['en'], indent=0)[:1500])
