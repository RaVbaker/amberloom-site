"""Put the full-resolution phone and doodle layers back over the Canva exports in images/<lang>/.

Canva resamples placed images when it exports, so the phone screens come out soft. This keeps the
export's background and live headline text, and re-draws every layer from the phone up (in the
order of design/canva/amberloom-app-store-<lang>.html) from design/canva-layers/ at its position.
Run it after saving a fresh Canva export:  python3 design/sharpen_exports.py
"""
import json, os, re
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAYERS = os.path.join(HERE, 'canva-layers')
IMAGES = os.path.join(HERE, '..', 'images')
pos = json.load(open(os.path.join(LAYERS, 'positions.json')))

for lang in ['en', 'pl']:
    html = open(os.path.join(HERE, 'canva', f'amberloom-app-store-{lang}.html')).read()
    order = list(dict.fromkeys(re.findall(r'(?:phone|doodle|books|bg)_' + lang + r'\d(?:_\d)?', html)))
    for p in range(1, 7):
        page = [o for o in order if re.fullmatch(r'\w+_' + lang + str(p) + r'(_\d)?', o)]
        top = page[page.index(f'phone_{lang}{p}'):]
        path = os.path.join(IMAGES, lang, f'image{p}.png')
        out = cv2.imread(path).astype(np.float32)
        H, W = out.shape[:2]
        for name in top:
            q = pos[name.replace('phone_', '') if name.startswith('phone') else name]
            lay = cv2.imread(os.path.join(LAYERS, name + '.png'), cv2.IMREAD_UNCHANGED)
            x, y = q['left'], q['top']
            h, w = min(lay.shape[0], H - y), min(lay.shape[1], W - x)
            a = lay[:h, :w, 3:4].astype(np.float32) / 255
            out[y:y + h, x:x + w] = out[y:y + h, x:x + w] * (1 - a) + lay[:h, :w, :3] * a
        cv2.imwrite(path, np.clip(out + 0.5, 0, 255).astype(np.uint8))
        print(path, top)
