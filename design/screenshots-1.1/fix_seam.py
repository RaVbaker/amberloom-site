"""Redo the shadows where page 1's tilted phone overlaps page 2's front phone.

out = tilted phone on top of (front phone + background), with one consistent Canva-style
halo (measured on this page: darkness 0.67 at the edge, gone by ~80 px) cast by the tilted
phone onto everything behind it, and the front phone's own halo on the background.

usage: fix_seam.py <site repo> <lang> <out.png>
  front phone pixels come from 65ed02a (front phone fully visible, sharp),
  tilted phone pixels from 3a291d0 (tilted on top).
"""
import io
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

repo, lang, out_path = sys.argv[1:4]
sys.path.insert(0, os.path.join(repo, "design", "screenshots-1.1"))
os.environ["LAYERS"] = os.path.join(repo, "design", "canva-layers")
import build_phones as bp  # noqa: E402

W, H = 1290, 2796
SIGMA, K = 35.0, 1.34  # fitted to the page's existing phone shadows
X_END, FEATHER = 520, 40  # only touch the seam area, left of the Amberloom pill


def git_img(rev, path):
    data = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], check=True, capture_output=True).stdout
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.float32)


A = git_img("65ed02a", f"images/{lang}/image2.png")
B = git_img("3a291d0", f"images/{lang}/image2.png")
bg = np.asarray(Image.open(os.path.join(repo, "design", "canva-layers", f"bg_{lang}2.png")).convert("RGB")).astype(np.float32)

# tilted phone body in page-2 coordinates (same geometry build_phones.py uses)
tl, ex, ey, width = bp.rotated_geometry(lang)
sw, sh = 1320, 2868
body = np.zeros((sh, sw, 4), np.uint8)
body[..., 3] = bp.rounded_mask((sh, sw), 0, 0, sw - 1, sh - 1, int(round(sw * 0.135)))
DX = -38  # where the tilted phone actually sits on page 2 (fitted to its edge in the export)
o = tl - np.array([W - DX, 0], np.float32)
T = bp.warp(body, o, ex, ey, width, (W, H))[..., 3].astype(np.float32) / 255

# front phone body: x 140-1149 in the layer, layer at top 112
x0, x1, y0 = 140, 1149, 42 + 112
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 2343
F = bp.rounded_mask((H, W), x0, y0, x1, y1, int(round((x1 - x0 + 1) * 0.135))).astype(np.float32) / 255


def halo(mask):
    g = cv2.GaussianBlur(mask, (0, 0), SIGMA)
    return 1 - np.clip(K * g, 0, 1)


# the tilted phone's screen, drawn once at its real position from the full-resolution shot
shot = cv2.imread(os.path.join(repo, "design", "screenshots-1.1", f"{lang}_1_timeline.png"), cv2.IMREAD_UNCHANGED)
if shot.shape[2] == 3:
    shot = cv2.cvtColor(shot, cv2.COLOR_BGR2BGRA)
tilted = cv2.cvtColor(bp.warp(shot, o, ex, ey, width, (W, H)), cv2.COLOR_BGRA2RGB).astype(np.float32)
chk = (cv2.erode((T > 0.99).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0) & (F < 0.01)
chk[:1000] = False
chk[:, 480:] = False
print("tilted vs export outside the front phone: mean abs diff %.1f over %d px" % (np.abs(tilted - B)[chk].mean(), chk.sum()))

sT, sF = halo(T)[..., None], halo(F)[..., None]
Fm, Tm = F[..., None], T[..., None]
background = bg * sT * sF
front = A * sT
base = front * Fm + background * (1 - Fm)
new = B * Tm + base * (1 - Tm)  # keep the tilted content as exported: it lines up with page 1

xs = np.arange(W, dtype=np.float32)
blend = np.clip((X_END - xs) / FEATHER, 0, 1)[None, :, None]
out = new * blend + B * (1 - blend)
Image.fromarray(out.round().clip(0, 255).astype(np.uint8)).save(out_path)
print("wrote", out_path)
