"""Build the App Store header artwork (3840x1646) layers + previews from the screenshot layers."""
import json, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'canva-layers')
OUT = HERE
PREV = os.path.join(HERE, 'preview')
ORDER = [2, 3, 5, 4]          # screenshot pages used, left to right
# per size: phone frame width, gap between phones, frame tops (arch; pushed down if a phone
# would end above the bottom edge), doodle scale. Phones stay at or below the source scale.
SIZES = {
    (3840, 1646): dict(fw=640, gap=180, tops=[610, 410, 410, 610], dsc=1.15),
    }
SH_ALPHA = 0.42

os.makedirs(OUT, exist_ok=True); os.makedirs(PREV, exist_ok=True)

def background(W, H):
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
        a2[:, :138] = 0; a2[1700:, :] = 0  # below y 1700 its shadow darkens the left edge
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

def with_shadow(ph, k):
    SH_OFF, SH_BLUR = round(28 * k), round(38 * k)
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

# (file, name, anchor, x, y, mirror): anchor 'tl'/'tr'/'br'/'bl' pins that corner of the doodle to (x, y);
# x/y are fractions of the canvas
DOODLES = [
    ('doodle_en5_0', 'rays_r', 'tr', 1, 0, False),       # rays from the top-right corner, as on page 5
    ('doodle_en5_0', 'rays_l', 'tl', 0, 0, True),        # mirrored, top-left corner
    ('doodle_en1_1', 'sparkle_l', 'bl', 0, .963, False), # page 1 sparkle, on the left edge as on page 1
    ('doodle_en1_1', 'sparkle_r', 'br', 1, .963, True),  # mirrored to the right edge
]

def build(lang, W, H, fw, gap, tops, dsc):
    tag = f'{W}x{H}'
    layers = []
    bg = background(W, H); bg.save(f'{OUT}/header_bg_{tag}.png')
    layers.append(dict(src=f'header_bg_{tag}.png', left=0, top=0, width=W, height=H))
    comp = bg.convert('RGBA')
    total = len(ORDER) * fw + (len(ORDER) - 1) * gap
    x0 = (W - total) // 2
    for i, page in enumerate(ORDER):
        ph, (fl, ft, fr), bbox = clean_phone(lang, page)
        s = fw / (fr - fl + 1)
        assert s <= 1.0, 'would upscale the screenshot'
        fl -= bbox[0]; ft -= bbox[1]
        top_f = max(tops[i], round(H - (ph.height - ft) * s) + 4)
        vis_h = int((H - top_f) / s) + ft + 10
        ph = ph.crop((0, 0, ph.width, min(ph.height, vis_h)))
        ph = ph.resize((round(ph.width * s), round(ph.height * s)), Image.LANCZOS)
        ph, pad = with_shadow(ph, fw / 640)
        left = round(x0 + i * (fw + gap) - fl * s - pad)
        top = round(top_f - ft * s - pad)
        cl = max(0, -left); ct = max(0, -top)
        ph = ph.crop((cl, ct, min(ph.width, W - left), min(ph.height, H - top)))
        left += cl; top += ct
        name = f'header_phone_{lang}{i + 1}_{tag}.png'; ph.save(f'{OUT}/{name}')
        layers.append(dict(src=name, left=left, top=top, width=ph.width, height=ph.height))
        comp.alpha_composite(ph, (left, top))
    for f, nm, anc, fx, fy, mir in DOODLES:
        d = white_only(Image.open(f'{SRC}/{f}.png').convert('RGBA'))
        if mir: d = d.transpose(Image.FLIP_LEFT_RIGHT)
        d = d.resize((round(d.width * dsc), round(d.height * dsc)), Image.LANCZOS)
        name = f'header_doodle_{nm}_{tag}.png'; d.save(f'{OUT}/{name}')
        ax, ay = round(fx * W), round(fy * H)
        left = ax - d.width if 'r' in anc else ax
        top = ay - d.height if 'b' in anc else ay
        layers.append(dict(src=name, left=left, top=top, width=d.width, height=d.height))
        comp.alpha_composite(d, (left, top))
    comp.convert('RGB').save(f'{PREV}/header_{lang}_{tag}.png')
    return layers

pos = {f'{w}x{h}': {lang: build(lang, w, h, **cfg) for lang in ['en', 'pl']} for (w, h), cfg in SIZES.items()}
json.dump(pos, open(f'{OUT}/positions.json', 'w'), indent=1)
