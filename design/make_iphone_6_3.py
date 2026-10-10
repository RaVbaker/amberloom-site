"""Make the 6.3" iPhone App Store screenshots (1206 x 2622) from the 6.9" ones (1290 x 2796).

App Store Connect only accepts 1206 x 2622 / 1179 x 2556 in the 6.3" slot. The 6.9" images are a
hair wider, so they are scaled to 2622 px tall and 2 px are trimmed from each side.
Run after changing images/<lang>/image*.png:  python3 design/make_iphone_6_3.py
"""
import glob, os
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(HERE, '..', 'images')
W, H = 1206, 2622

for lang in ['en', 'pl']:
    out_dir = os.path.join(IMAGES, 'iphone-6.3', lang)
    os.makedirs(out_dir, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(IMAGES, lang, 'image*.png'))):
        img = cv2.imread(path)
        w = round(img.shape[1] * H / img.shape[0])
        small = cv2.resize(img, (w, H), interpolation=cv2.INTER_AREA)
        x = (w - W) // 2
        out = os.path.join(out_dir, os.path.basename(path))
        cv2.imwrite(out, small[:, x:x + W])
        print(out)
