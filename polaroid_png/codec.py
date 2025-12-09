import struct, binascii, json, io, zlib
from PIL import Image

PNG_SIG = b"\x89PNG\r\n\x1a\n"

COMP_RAW = 0
COMP_RLE = 1
COMP_DEFLATE = 2  # optional stronger lossless

def _crc(chunk_type: bytes, data: bytes) -> int:
    return binascii.crc32(chunk_type + data) & 0xffffffff

def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xffffffff

# -------- PNG chunk IO --------
def _read_chunks(png_bytes: bytes):
    if not png_bytes.startswith(PNG_SIG):
        raise ValueError("Not a PNG")
    off = 8
    chunks = []
    while off < len(png_bytes):
        length = struct.unpack(">I", png_bytes[off:off+4])[0]; off += 4
        ctype  = png_bytes[off:off+4]; off += 4
        data   = png_bytes[off:off+length]; off += length
        ccrc   = struct.unpack(">I", png_bytes[off:off+4])[0]; off += 4
        chunks.append((ctype, data, ccrc))
        if ctype == b"IEND":
            break
    return chunks

def _write_chunks(chunks):
    out = bytearray(PNG_SIG)
    for ctype, data in chunks:
        out += struct.pack(">I", len(data))
        out += ctype
        out += data
        out += struct.pack(">I", _crc(ctype, data))
    return bytes(out)

# -------- Lossless RLE --------
def _rle_encode(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        run_val = data[i]
        run_len = 1
        while i + run_len < n and data[i+run_len] == run_val and run_len < 128:
            run_len += 1

        if run_len >= 3:
            out.append(0x80 | (run_len - 1))
            out.append(run_val)
            i += run_len
        else:
            lit_start = i
            lit_len = 0
            while i < n and lit_len < 128:
                run_val2 = data[i]
                run_len2 = 1
                while i + run_len2 < n and data[i+run_len2] == run_val2 and run_len2 < 128:
                    run_len2 += 1
                if run_len2 >= 3:
                    break
                i += 1
                lit_len += 1

            out.append(lit_len - 1)
            out.extend(data[lit_start:lit_start+lit_len])
    return bytes(out)

def _rle_decode(data: bytes, expected_size: int) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n and len(out) < expected_size:
        h = data[i]; i += 1
        is_run = (h & 0x80) != 0
        length = (h & 0x7f) + 1
        if is_run:
            if i >= n:
                raise ValueError("RLE run packet missing value")
            val = data[i]; i += 1
            out.extend([val] * length)
        else:
            if i + length > n:
                raise ValueError("RLE literal packet truncated")
            out.extend(data[i:i+length]); i += length
    if len(out) != expected_size:
        raise ValueError("RLE decoded size mismatch")
    return bytes(out)

# -------- pOLR v2 pack/unpack (v1 compatible) --------
def _pack_pOLR_v2(raw_pixels: bytes, width, height, channels=4, bpc=8, compression=COMP_RLE):
    raw_size = len(raw_pixels)
    if compression == COMP_RLE:
        comp_pixels = _rle_encode(raw_pixels)
    elif compression == COMP_RAW:
        comp_pixels = raw_pixels
    elif compression == COMP_DEFLATE:
        comp_pixels = zlib.compress(raw_pixels, level=9)
    else:
        raise ValueError("unknown compression")

    comp_size = len(comp_pixels)
    c = _crc32(raw_pixels)

    header = struct.pack(
        ">BBBBHHIII",
        2, channels, bpc, compression,
        width, height,
        raw_size, comp_size, c
    )
    return header + comp_pixels

def _unpack_pOLR(data: bytes):
    # v1: embedded PNG
    if data.startswith(PNG_SIG):
        return {"version": 1, "back_png_bytes": data}

    view = memoryview(data)
    (ver, ch, bpc, comp, w, h, raw_size, comp_size, stored_crc) = \
        struct.unpack_from(">BBBBHHIII", view, 0)
    if ver != 2:
        raise ValueError("unknown pOLR version")

    hdr_sz = struct.calcsize(">BBBBHHIII")
    comp_pixels = view[hdr_sz: hdr_sz + comp_size].tobytes()

    if comp == COMP_RLE:
        raw = _rle_decode(comp_pixels, raw_size)
    elif comp == COMP_RAW:
        raw = comp_pixels
    elif comp == COMP_DEFLATE:
        raw = zlib.decompress(comp_pixels)
    else:
        raise ValueError("unknown compression in pOLR")

    if len(raw) != raw_size or _crc32(raw) != stored_crc:
        raise ValueError("back payload corrupted")

    return {
        "version": 2,
        "width": w, "height": h,
        "channels": ch, "bits_per_channel": bpc,
        "raw_pixels": raw
    }

# -------- Public API --------
def make_polaroid_png_v2(front_path, back_path, out_path, meta=None,
                         compression=COMP_RLE):
    """
    Create a valid PNG that displays the front image everywhere,
    with a pOLR chunk containing the back face (v2 by default).
    """
    front = Image.open(front_path).convert("RGBA")
    back  = Image.open(back_path).convert("RGBA")

    # front -> standard PNG bytes
    buf_f = io.BytesIO()
    front.save(buf_f, format="PNG")
    front_png = buf_f.getvalue()

    # back -> raw pixels
    w, h = back.size
    raw_back = back.tobytes()  # RGBA 8-bit row-major
    polr_data = _pack_pOLR_v2(raw_back, w, h, channels=4, bpc=8, compression=compression)

    chunks = _read_chunks(front_png)
    new_chunks = []
    for ctype, data, _ in chunks:
        if ctype == b"IEND":
            new_chunks.append((b"pOLR", polr_data))
            if meta is not None:
                text = json.dumps(meta, ensure_ascii=False).encode("utf-8")
                pmet = struct.pack(">II", 1, len(text)) + text
                new_chunks.append((b"pMET", pmet))
        new_chunks.append((ctype, data))

    out_png = _write_chunks(new_chunks)
    with open(out_path, "wb") as f:
        f.write(out_png)

def extract_polaroid_png(path, back_out_png="back_extracted.png"):
    """
    Extract back face (as PNG) and metadata from a polaroid PNG.
    Returns (back_info, meta).
    """
    png_bytes = open(path, "rb").read()
    chunks = _read_chunks(png_bytes)

    back_info = None
    meta = None

    for ctype, data, _ in chunks:
        if ctype == b"pOLR":
            back_info = _unpack_pOLR(data)
        elif ctype == b"pMET":
            meta_format, text_len = struct.unpack(">II", data[:8])
            text = data[8:8+text_len].decode("utf-8")
            meta = json.loads(text)

    if back_info:
        if back_info["version"] == 1:
            open(back_out_png, "wb").write(back_info["back_png_bytes"])
        else:
            mode = {1:"L", 3:"RGB", 4:"RGBA"}[back_info["channels"]]
            im = Image.frombytes(mode, (back_info["width"], back_info["height"]),
                                 back_info["raw_pixels"])
            im.save(back_out_png)

    return back_info, meta
