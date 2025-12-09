from polaroid_png import make_polaroid_png_v2, extract_polaroid_png
from PIL import Image
import tempfile, os

def test_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        front = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
        back  = Image.new("RGBA", (64, 64), (0, 255, 0, 255))
        fp = os.path.join(d, "front.png")
        bp = os.path.join(d, "back.png")
        out = os.path.join(d, "card.polaroid.png")
        front.save(fp); back.save(bp)

        meta_in = {"a": 1, "b": "hi"}
        make_polaroid_png_v2(fp, bp, out, meta=meta_in)
        back_info, meta_out = extract_polaroid_png(out)

        assert meta_out == meta_in
        assert back_info["width"] == 64 and back_info["height"] == 64
