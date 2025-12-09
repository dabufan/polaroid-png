import argparse, json
from .codec import make_polaroid_png_v2, extract_polaroid_png, COMP_RLE, COMP_RAW, COMP_DEFLATE

def encode_main():
    ap = argparse.ArgumentParser("polaroid-encode")
    ap.add_argument("front")
    ap.add_argument("back")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--meta", default=None, help="JSON string")
    ap.add_argument("--raw", action="store_true", help="use RAW instead of RLE")
    ap.add_argument("--deflate", action="store_true", help="use DEFLATE instead of RLE")
    args = ap.parse_args()

    meta = json.loads(args.meta) if args.meta else None
    if args.deflate:
        comp = COMP_DEFLATE
    else:
        comp = COMP_RAW if args.raw else COMP_RLE

    make_polaroid_png_v2(args.front, args.back, args.out, meta=meta, compression=comp)
    print("Wrote", args.out)

def decode_main():
    ap = argparse.ArgumentParser("polaroid-decode")
    ap.add_argument("input")
    ap.add_argument("--back-out", default="back.png")
    args = ap.parse_args()

    back_info, meta = extract_polaroid_png(args.input, back_out_png=args.back_out)
    print("Back written to", args.back_out)
    print("Back version:", back_info["version"] if back_info else "(none)")
    print("Meta:", json.dumps(meta, ensure_ascii=False, indent=2) if meta else "(none)")
