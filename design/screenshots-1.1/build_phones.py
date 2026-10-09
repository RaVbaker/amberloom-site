"""Rebuild the phone layers in design/canva-layers/ from new simulator screenshots.

Each phone layer keeps its original shape, rim and shadow; only the screen inside is
replaced. Page 1's phone is rotated -16 degrees and continues onto page 2 in front of the
front phone (casting a shadow on it), so both are drawn from the same geometry.

Usage: python3 build_phones.py <screens dir> <out dir>
The screens dir holds <lang>_<n>_*.png from an iPhone 17 Pro Max (1320 x 2868, 440 pt).
Page mapping is in PAGES below.
"""
import glob
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAYERS = os.environ.get('LAYERS', os.path.join(HERE, '..', 'canva-layers'))

# page -> screenshot number (see README.md in this folder)
PAGES = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 7}
# Page 6 (facts) reuses page 5's phone shape and shadow, placed lower on the page.
PAGE6_TOP = 900


def warp(shot, tl, ex, ey, width, size):
    s = width / shot.shape[1]
    m = np.float32([[s * ex[0], s * ey[0], tl[0]], [s * ex[1], s * ey[1], tl[1]]])
    return cv2.warpAffine(shot, m, size, flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def line(c, sel):
    vx, vy, x0, y0 = cv2.fitLine(c[sel], cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    return np.array([x0, y0]), np.array([vx, vy])


def intersect(p1, d1, p2, d2):
    a = np.array([d1, -d2]).T
    t = np.linalg.solve(a, p2 - p1)
    return p1 + t[0] * d1


def rotated_geometry(lang):
    """Top-left corner, axes and width of page 1's rotated phone, in page 1 coordinates."""
    layer = cv2.imread(os.path.join(LAYERS, f"phone_{lang}1.png"), cv2.IMREAD_UNCHANGED)
    pos = json.load(open(os.path.join(LAYERS, "positions.json")))[f"{lang}1"]
    m = (layer[:, :, 3] >= 250).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    top = (c[:, 0] > 200) & (c[:, 0] < 900) & (c[:, 1] < 320)
    left = (c[:, 1] > 600) & (c[:, 1] < 2100) & (c[:, 0] < 480)
    right = (c[:, 1] > 250) & (c[:, 1] < 560) & (c[:, 0] > 1150) & (c[:, 0] < 1285)
    pt, dt = line(c, top)
    pl, dl = line(c, left)
    pr, dr = line(c, right)
    if dt[0] < 0:
        dt = -dt
    if dl[1] < 0:
        dl = -dl
    tl = intersect(pt, dt, pl, dl)
    tr = intersect(pt, dt, pr, dr)
    width = float(np.linalg.norm(tr - tl))
    offset = np.array([pos["left"], pos["top"]], np.float32)
    return tl + offset, dt, dl, width


def flat_rect(mask_bbox_layer):
    return mask_bbox_layer


def rounded_mask(shape, x0, y0, x1, y1, r):
    m = np.zeros(shape, np.uint8)
    cv2.rectangle(m, (x0 + r, y0), (x1 - r, y1), 255, -1)
    cv2.rectangle(m, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for cx, cy in [(x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)]:
        cv2.circle(m, (cx, cy), r, 255, -1, lineType=cv2.LINE_AA)
    return m


def compose(layer, content, region, edges=()):
    """Put content into the layer where region (0..255) and the layer is opaque, keeping a 2px rim."""
    opaque = (layer[:, :, 3] >= 250).astype(np.uint8)
    # Where a phone runs off the page, its last few pixels are soft; treat them as screen too.
    if "left" in edges:
        opaque[:, :3] |= opaque[:, 3:4]
    if "right" in edges:
        opaque[:, -3:] |= opaque[:, -4:-3]
    if "bottom" in edges:
        opaque[-3:, :] |= opaque[-4:-3, :]
    inner = cv2.erode(opaque, np.ones((5, 5), np.uint8), borderType=cv2.BORDER_REPLICATE)
    a = (inner * (region.astype(np.float32) / 255) * (content[:, :, 3].astype(np.float32) / 255))[..., None]
    out = layer.copy()
    out[..., :3] = (content[..., :3] * a + layer[..., :3] * (1 - a)).astype(np.uint8)
    out[..., 3] = np.maximum(layer[..., 3], (a[..., 0] * 255).astype(np.uint8))
    return out


def build(lang, shots, out_dir):
    pos = json.load(open(os.path.join(LAYERS, "positions.json")))
    page_w = 1290
    tl, ex, ey, width = rotated_geometry(lang)
    for page in range(1, 7):
        name = f"phone_{lang}{page}.png"
        if page == 6:
            layer = cv2.imread(os.path.join(LAYERS, f"phone_{lang}5.png"), cv2.IMREAD_UNCHANGED)
            layer = layer[: 2796 - PAGE6_TOP]
            p = dict(pos[f"{lang}5"], top=PAGE6_TOP)
        else:
            layer = cv2.imread(os.path.join(LAYERS, name), cv2.IMREAD_UNCHANGED)
            p = pos[f"{lang}{page}"]
        h, w = layer.shape[:2]
        edges = [e for e, hit in (("left", p["left"] == 0), ("right", p["left"] + w == page_w),
                                  ("bottom", p["top"] + h == 2796)) if hit]
        shot = shots[PAGES[page]]
        full = np.full((h, w), 255, np.uint8)
        if page == 1:
            o = tl - np.array([p["left"], p["top"]])
            content = warp(shot, o, ex, ey, width, (w, h))
            out = compose(layer, content, full, edges)
        else:
            opaque = (layer[:, :, 3] >= 250).astype(np.uint8)
            if page == 2:
                # the front phone is fully visible: x 140-1149, y 42-2226 in this layer
                x0, x1, y0, y1 = 140, 1149, 42, 2226
            else:
                ys, xs = np.nonzero(opaque)
                x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            pw = x1 - x0 + 1
            content = warp(shot, (x0, y0), (1, 0), (0, 1), pw, (w, h))
            r = int(round(pw * 0.135))
            front = rounded_mask((h, w), x0, y0, x1, max(y1, y0 + int(pw * 2.2)), r)
            if page == 2:
                # page 1's tilted phone lies on top of the front phone here
                back_shot = shots[PAGES[1]]
                sh, sw = back_shot.shape[:2]
                o = tl - np.array([page_w + p["left"], p["top"]])
                back = warp(back_shot, o, ex, ey, width, (w, h))
                body = np.zeros((sh, sw, 4), np.uint8)
                body[..., 3] = rounded_mask((sh, sw), 0, 0, sw - 1, sh - 1, int(round(sw * 0.135)))
                tilted = warp(body, o, ex, ey, width, (w, h))[..., 3]
                # its soft shadow falls on the front screen, down and to the right
                shadow = np.zeros_like(tilted)
                shadow[18:, 10:] = tilted[:-18, :-10]
                shadow = cv2.GaussianBlur(shadow.astype(np.float32) / 255, (0, 0), 26)
                content = content.copy()
                content[..., :3] = (content[..., :3] * (1 - 0.55 * shadow)[..., None]).astype(np.uint8)
                front = cv2.min(front, 255 - cv2.dilate(tilted, np.ones((5, 5), np.uint8)))
                out = compose(layer, content, front, edges)
                out = compose(out, back, tilted, edges)
            else:
                out = compose(layer, content, front, edges)
        cv2.imwrite(os.path.join(out_dir, name), out)
        print("wrote", name)


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    for lang in ("en", "pl"):
        shots = {}
        for f in glob.glob(os.path.join(src, f"{lang}_*.png")):
            n = int(os.path.basename(f).split("_")[1])
            img = cv2.imread(f, cv2.IMREAD_UNCHANGED)
            if img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            shots[n] = img
        if all(PAGES[p] in shots for p in PAGES):
            build(lang, shots, out_dir)
        else:
            print("skipping", lang, "missing screenshots", sorted(shots))


if __name__ == "__main__":
    main()
