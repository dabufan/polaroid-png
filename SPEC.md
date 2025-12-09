# Polaroid PNG Spec (v1/v2)

Polaroid PNG is a backward-compatible extension of standard PNG.
A `.polaroid.png` file is a valid PNG that displays the **front** image everywhere.
It optionally embeds a **back** face and metadata via private PNG chunks.

## Compatibility
- PNG decoders that don't know these chunks MUST ignore them.
- Therefore any viewer can display the front image as normal PNG.
- Polaroid-aware viewers can decode and flip to the back face.

## Private chunks

### 1. `pOLR` — Back face payload

Chunk type: ASCII `pOLR` (private chunk)

Two versions exist:

#### v1 (legacy)
`pOLR` data is a complete PNG byte stream (starts with PNG signature).
Viewers can treat it as an embedded PNG file.

#### v2 (recommended)
`pOLR` data layout (big-endian numbers):

```
u8  polr_version = 2
u8  channels          // 1=Gray, 3=RGB, 4=RGBA
u8  bits_per_channel  // 8 or 16
u8  compression       // 0=RAW, 1=RLE, 2=DEFLATE(optional)
u16 width
u16 height
u32 raw_size
u32 comp_size
u32 crc32_raw
bytes comp_pixels     // comp_size bytes
```

- raw_size = width * height * channels * (bits/8)
- crc32_raw is CRC32 of the uncompressed raw pixels.
- Pixel order is row-major, channel order Gray/RGB/RGBA.
- bits=16 stores each channel as uint16 little-endian in raw pixels.

##### RLE compression (lossless)
RLE encodes the raw byte stream into packets:

- Literal packet:
  - header: `0b0LLLLLLL` (MSB=0)
  - length = L + 1 (1..128)
  - followed by `length` literal bytes

- Run packet:
  - header: `0b1LLLLLLL` (MSB=1)
  - length = L + 1 (1..128)
  - followed by 1 byte value repeated `length` times

Encoding rule:
- Any run length >= 3 should be encoded as a Run packet.
- Otherwise use Literal packets.

### 2. `pMET` — Metadata

Chunk type: ASCII `pMET`

Data layout:

```
u32 meta_format = 1   // 1 = UTF-8 JSON
u32 text_len
bytes utf8_json        // text_len bytes
```

Example JSON:
```json
{
  "front_title": "Type here",
  "front_date": "2025/12/02",
  "back_hint": "write your secret"
}
```

Unknown fields must be ignored.

## Versioning rules
- New versions must remain backward compatible.
- Future extensions should add new private chunks or append fields guarded by version tags.
