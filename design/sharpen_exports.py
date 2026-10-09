"""Put the full-resolution phone and doodle layers back over the Canva exports in images/<lang>/.

Canva keeps a downsampled copy of every placed image, so the phone screens in its PNG export come
out soft. This keeps the export (background, headlines, the Amberloom pill, the page 4 caption) and
re-draws the phone and the doodles above it from design/canva-layers/, at the exact box Canva draws
them in (Canva stretches each phone by a fraction of a percent, so the boxes below come from
read-design's imageBox, not from positions.json). Areas covered by Canva-only elements that sit
above the phone (text, the pill) are left as exported.
Run it right after saving a fresh Canva export:  python3 design/sharpen_exports.py
"""
import json, os
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAYERS = os.path.join(HERE, 'canva-layers')
IMAGES = os.path.join(HERE, '..', 'images')
pos = json.load(open(os.path.join(LAYERS, 'positions.json')))

# phone imageBox in Canva (page coordinates): top offset and drawn height; left/width match positions.json
PHONE_BOX = {1: (-0.1485, 2156.297), 2: (-1.4783, 2686.957), 3: (-2.4084, 2208.817),
             4: (-0.2811, 1940.562), 5: (-1.4680, 2174.936), 6: (-1.1071, 1898.214)}
# layers drawn above the phone in Canva, back to front
ABOVE = {1: ['doodle_{l}1_0', 'doodle_{l}1_1'], 2: [], 3: ['books_{l}3', 'doodle_{l}3_0', 'doodle_{l}3_1'],
         4: ['doodle_{l}4_0', 'doodle_{l}4_1', 'doodle_{l}4_2'], 5: ['doodle_{l}5_0'], 6: ['doodle_{l}6_0']}
# Canva-only elements above the phone (left, top, right, bottom): keep the export there
KEEP = {2: [(556, 2493, 1247, 2728)],          # Amberloom pill
        4: [(0, 2420, 1290, 2700)]}            # "Start with one moment..." caption

def draw(out, lay, x, y, w, h, solid_only=False):
    """Alpha-composite lay resized to w x h (float) at (x, y) (float) onto out.
    solid_only: draw only the (near) opaque phone body and screen, not the baked soft shadow,
    which Canva renders softer than the layer file; the export keeps its shadow there."""
    M = np.float32([[w / lay.shape[1], 0, x], [0, h / lay.shape[0], y]])
    H, W = out.shape[:2]
    warped = cv2.warpAffine(lay, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = warped[..., 3:4].astype(np.float32) / 255
    if solid_only:
        a = np.clip((a - 0.9) / 0.1, 0, 1)
    return out * (1 - a) + warped[..., :3].astype(np.float32) * a

for lang in ['en', 'pl']:
    for p in range(1, 7):
        path = os.path.join(IMAGES, lang, f'image{p}.png')
        exp = cv2.imread(path).astype(np.float32)
        out = exp.copy()
        q = pos[f'{lang}{p}']
        top, hgt = PHONE_BOX[p]
        phone = cv2.imread(os.path.join(LAYERS, f'phone_{lang}{p}.png'), cv2.IMREAD_UNCHANGED)
        out = draw(out, phone, q['left'], q['top'] + top, q['width'], hgt, solid_only=True)
        for name in ABOVE[p]:
            name = name.format(l=lang)
            if name not in pos:
                continue
            d = pos[name]
            out = draw(out, cv2.imread(os.path.join(LAYERS, name + '.png'), cv2.IMREAD_UNCHANGED),
                       d['left'], d['top'], d['width'], d['height'])
        for (x0, y0, x1, y1) in KEEP.get(p, []):
            out[y0:y1, x0:x1] = exp[y0:y1, x0:x1]
        cv2.imwrite(path, np.clip(out + 0.5, 0, 255).astype(np.uint8))
        print(path)
