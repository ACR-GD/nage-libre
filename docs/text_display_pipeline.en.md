# Text display: Nage Libre (SNES)

*English version of [`text_display_pipeline.md`](text_display_pipeline.md).*

## Encoding (important)

The text in the ROM **is not Shift-JIS**. It uses the classic SNES approach:

- **1 byte = 1 glyph** (an index into the 16×16 font in ROM).
- The VRAM tile shown is about `index + 0xFB` (e.g. こ → index `0x0D` → tile `$108`).
- **Control codes**: `01` start of line, `02` pause, `8D xx` explicit glyph, `20 xx yy` variant (often `20 XX 96`), `FF xx` end, `FE` alternative end.

Shift-JIS only shows up if you **force** an SJIS decoder onto bytes that are really indexes, which gives garbage like `ｨｩｬｩ` (bytes `A8 A9 AC A9` are four glyphs, not two half-width kana).

## Pipeline

```
Script (bank $84, opcodes + lo/hi/84 pointers)
        ↓
Text data = stream of glyph indexes + control codes
        ↓
16×16 font in ROM → VRAM tileset $5000.w
        ↓
Layer 3, tilemap $7C00.w
```

## Extraction (without playing)

```bash
cd NageLibre.Tools
dotnet run -- extract-all
```

Produces:

| File | Purpose |
|------|---------|
| `game_strings.csv` | Extracted text: `glyph_ids`, `glyph_display`, `japanese` (〓 = unmapped kanji) |
| `glyph_unicode.csv` | Bytes with identified hiragana/katakana (gojūon + こ anchor) |
| `glyph_index.csv` | The 256 possible bytes → font offset in ROM (to complete by hand) |

```bash
dotnet run -- map-glyphs    # regenerates glyph_unicode.csv + glyph_index.csv
dotnet run -- extract-all   # applies the table to the Japanese text
```

## Translation

1. Translate using `glyph_ids` / the `charset_atlas.bmp` atlas.
2. Reinsert **the same bytes** (same length, same `FF xx`).
3. Repoint the scripts if the text moves (`script_commands.csv`).
