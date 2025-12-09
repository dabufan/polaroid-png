# polaroid-png

**Polaroid PNG** is a backward-compatible PNG extension that embeds a **back face**
and optional metadata inside a normal PNG file.

- Anywhere you open it, it behaves like a normal PNG (shows the **front**).
- In Polaroid-aware viewers, you can click left/right to flip to the **back**.

## Install

```bash
pip install polaroid-png
```

## CLI usage

### Encode (front + back -> polaroid PNG)

```bash
polaroid-encode front.png back.png -o card.polaroid.png \
  --meta '{"front_title":"Type here","front_date":"2025/12/02","back_hint":"write your secret"}'
```

### Decode (extract back + meta)

```bash
polaroid-decode card.polaroid.png --back-out back.png
```

## Python usage

```python
from polaroid_png import make_polaroid_png_v2, extract_polaroid_png

make_polaroid_png_v2("front.png", "back.png", "card.polaroid.png",
                     meta={"front_title":"Type here"})
back_info, meta = extract_polaroid_png("card.polaroid.png")
```

## Viewer demo
Open `viewer/polaroid_viewer.html` in a browser and load a `.polaroid.png`.

## Spec
See `SPEC.md`.

## License
MIT.
