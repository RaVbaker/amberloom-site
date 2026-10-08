# App Store marketing images

The App Store screenshots (`images/en/image1-5.png`, `images/pl/image1-5.png`) are made in Canva, with one design per language:

| Language | Edit | View |
| --- | --- | --- |
| English | [Edit in Canva](https://www.canva.com/d/NUTdoh-m_W7zUof) | [View](https://www.canva.com/d/69nWigVpgrzWGtv) |
| Polish | [Edit in Canva](https://www.canva.com/d/I2lWr8au-V_aY6-) | [View](https://www.canva.com/d/41wFXY8ecGOhZFp) |

Each design has 5 pages in App Store order (page 1 is `image1.png`, and so on). Every page is **1290 × 2796 px**.

## Size Apple requires

App Store Connect needs iPhone screenshots for the **6.9" display** (iPhone with Dynamic Island, large display). When those are provided, it scales them down for every smaller iPhone automatically. It accepts these portrait sizes for the 6.9" slot:

- 1260 × 2736
- **1290 × 2796** (what these designs use)
- 1320 × 2868

Other rules:
- File type: PNG or JPEG.
- **No alpha channel or transparency.**
- 1 to 10 screenshots per device size and language.

Source: [Apple screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications) (checked 2026-10-06). Check it again before a big release, because Apple adds sizes when new iPhones ship. If the 6.9" sizes change, use Canva's **Resize** to make a copy at the new size, then nudge the layers.

### iPad

Apps that run on iPad also need **13" iPad** screenshots. The accepted portrait sizes are 2064 × 2752 and 2048 × 2732, and Apple scales them down for smaller iPads. The App Store currently shows plain simulator screenshots for iPad, with no marketing frame. They're archived in `images/ipad/<lang>/` in App Store order:

| File | Screen | Source (iPad Pro 13-inch (M5) simulator) |
| --- | --- | --- |
| `images/ipad/en/image1.png` | Empty journal (Claire) | Simulator Screenshot 2026-06-26 at 23.28.51 |
| `images/ipad/en/image2.png` | Timeline (Emma) | Simulator Screenshot 2026-06-26 at 23.28.23 |
| `images/ipad/pl/image1.png` | Empty journal (Lena) | Simulator Screenshot 2026-06-26 at 23.30.33 |
| `images/ipad/pl/image2.png` | Timeline (Ania) | Simulator Screenshot 2026-06-26 at 23.30.49 |

They're 2064 × 2752, so they upload as they are. The PNGs carry an alpha channel, but it's fully opaque, and App Store Connect accepted them that way. If an upload is ever rejected for alpha, flatten them as described in "Exporting" below. To make iPad marketing pages later, create a 2064 × 2752 Canva design and follow the iPhone pages' layout.

## App Store header (product page artwork)

[Edit in Canva](https://www.canva.com/d/y3vpwRP1loiEwOa) · [View](https://www.canva.com/d/NUCIEkgcYzydvNE)

One design with two pages, **English** and **Polski**, each **4320 × 1080 px**. That is the size Apple uses for the wide header at the top of a featured product page and for featuring artwork. Apple sends the exact template and safe area in App Store Connect once an app is under consideration for featuring, so check it then; the key content here (the two middle phones) sits in the centre, and the outer phones and doodles can be cropped away on narrow screens.

Apple's rules for this artwork (from third-party guides, since Apple's help page wasn't reachable when this was made, checked 2026-10-08): no text or taglines, no app icon or logo, no prices, no URLs, and no mention of Apple or the App Store. That's why the header has no headline. Apple asks for the layered file (PSD) when it requests artwork; upload it only once you're sure, because uploads are one-time.

Layers, back to front: `header_bg.png` (the gradient, orange on the left to dark red on the right), four phones (pages 4, 2, 3 and 5 of the screenshots, with a fresh soft shadow), and the white doodles in the corners. `design/canva-header/build_header.py` rebuilds every layer and `positions.json` from `design/canva-layers/`, and writes previews to `design/canva-header/preview/`. To swap a phone, re-run the script after updating the screenshot layer and use **Replace** on that phone in Canva.

## Layers on each page

From back to front:

1. **Background**: a full-page image of the original gradient. Canva can't make this kind of gradient natively, so to change the colour, replace this image or put a Canva gradient on top of it.
2. **Phone**: the device frame with the app screenshot and drop shadow, as one image. The shadow it casts on the background is part of this layer, so replacing it replaces the shadow too. On page 2 this layer also includes the tilted phone on the left.
3. **Decorations**: separate images for the doodles (circles, underlines, rays, the heart, the frames on page 3, the asterisk on page 2) and the books on page 3.
4. **Text**: the headlines, the "Amberloom" pill on page 2, and the "Start with one moment…" line on page 4. All of these are live, editable Canva text.

## Common updates

### Change a headline or translate it

1. Double-click the text and type the new wording. Use line breaks to keep the lines balanced, as in the current pages.
2. Keep the text inside the safe area: about 60 px from the left and right edges, and clear of the phone.
3. Headlines use bold, centred text with letter spacing −40 (−0.04 em). Canva didn't recognise the original font, Bricolage Grotesque Bold, so the headlines use a close Canva substitute. If Bricolage Grotesque is in your Canva account, select the text and switch to it (Bold) for an exact match, then check the line widths against the original PNG and adjust the letter spacing if needed.

### Replace an app screenshot

The screenshot is part of the phone image, so swapping it takes one of two routes:

- **Quick:** take a new screenshot in the simulator. The current ones are 1206 × 2622 from an iPhone 16 Pro (`images/screenshot-*.png`), and an iPhone 15 Pro Max gives 1290 × 2796. Upload it, drop it onto the page above the phone layer, and size it to the phone's screen. Then round its corners with a Canva frame (*Elements → Frames → rounded rectangle*) so they match the device. The phone's outer edge sits at x 140–1149 on pages 2, 3 and 5, and x 126–1163 on page 4. Top edges: page 2 y 154, page 3 y 666, page 4 y 961, page 5 y 823. `design/canva-layers/positions.json` lists every layer's box.
- **Clean:** make a new phone image (device frame plus screenshot, transparent outside the phone, with a soft shadow) at the same size as the matching `design/canva-layers/phone_<lang><page>.png`. Then use **Replace** on the phone layer in Canva so its position stays the same.

On page 4, the dark "Start with one moment…" text sits on top of the screenshot as editable text. It has been removed from the phone image, so keep it as a separate text layer.

### Add a page or a language

- **New page:** duplicate the nearest existing page, then swap the text and phone. Apple allows up to 10 screenshots.
- **New language:** make a copy of the English design (*File → Make a copy*), rename it (for example "Amberloom App Store screenshots (Dutch)"), translate the text, and replace the screenshots with localised ones. Add the new links to the table above and to the README in the `amberloom` app repo.

## Exporting for App Store Connect

1. In Canva, go to *Share → Download → PNG*. Choose all pages, size ×1, and leave **Transparent background unticked**. JPG at the highest quality also works.
2. Check that the files are 1290 × 2796 with no alpha channel. On macOS, `sips -g pixelWidth -g pixelHeight -g hasAlpha *.png` shows this. If `hasAlpha` is `yes`, flatten the files with `sips -s format jpeg -s formatOptions 100 image1.png --out image1.jpg`, or with ImageMagick: `magick image1.png -background white -alpha remove -alpha off image1.png`.
3. Save them as `images/<lang>/image1-5.png` in this repo, so the site and the App Store use the same files.
4. Upload them to App Store Connect, in your app → the version → *Previews and Screenshots* → iPhone 6.9" display, once for each localisation.

## Files in this folder

- `canva-layers/`: the layer images the Canva designs were built from, cut from the original PNGs, and `positions.json` with each layer's position on its page.
- `canva-header/`: the header layers, the script that builds them, and full-size previews.
- `canva/amberloom-app-store-{en,pl}.html` and `canva/amberloom-app-store-header.html`: the HTML pages imported into Canva with *Import from URL* to create the designs. They load the layers from raw.githubusercontent.com at a fixed commit. You only need them to rebuild a design from scratch, because day-to-day edits happen in Canva.
