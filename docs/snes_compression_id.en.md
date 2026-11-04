# Finding graphics to translate and custom compression (SNES)

*English version of [`snes_compression_id.md`](snes_compression_id.md).*

A practical guide, usable on any game, that goes with
`scripts/snes_re_toolkit.py`. Goal: find the **graphics that contain text**
(logos, "PUSH START", menu labels, title screens) and work out **how they are
stored/compressed**, so you can extract, translate and reinsert them.

---

## 0. Quick vocabulary

| Term | Meaning |
|---|---|
| Tile | 8×8 pixels. SNES formats: **2bpp** (16 bytes), **3bpp** (24 bytes), **4bpp** (32 bytes), **8bpp** (64 bytes), **Mode 7** (64 bytes, linear). |
| Tilemap | Grid of tile indexes ("what to show where"). |
| CHR / VRAM | Video memory where tiles live while displayed (64 KB). |
| DMA | Fast transfer from ROM/WRAM to VRAM (registers `$43xx`, triggered by `$420B`). |

---

## 1. Is the graphic compressed? (30-second test)

Render the area **directly** as raw tiles:

```bash
python3 scripts/snes_re_toolkit.py game.sfc --gfx 0xOFFSET,0x2000,4,16 --out test.png
```

- The image shows **clean tiles** (letters, crisp drawings) → **not compressed**.
  Adjust `bpp` (2/4/8) and the offset if it looks shifted/scrambled but regular.
- The image is **structured noise** whatever the bpp → **compressed** (or it's
  code/data). Go to step 2.

> Tip: title screens and logos are almost always compressed; small text fonts
> are often **not** compressed (fast direct access).

---

## 2. Locate the compressed blobs

```bash
python3 scripts/snes_re_toolkit.py game.sfc --find-tables --entropy
```

- **Pointer tables** (`--find-tables`): compressed assets are almost always
  indexed by a table of 2- or 3-byte pointers. A table right before a large
  "noisy" area often points to the compressed blobs.
- **Entropy** (`--entropy`): dense regions are candidates. ⚠️ Weak signal:
  **nibble/bit-level** compression (common) keeps a moderate entropy
  (~6.5–7.1 per byte), and raw 4bpp tiles can be dense too. Never conclude
  from entropy alone.

---

## 3. Find the decompressor (the real key)

### 3a. Static (fast, noisy)

```bash
python3 scripts/snes_re_toolkit.py game.sfc --find-decompressors
```

Looks for `shifts (bit reader) + window copy (LZ) + loop` patterns.
**Limit**: decompressors that use a **jump table** (`JSR (table,X)`) are split
into subroutines and slip under the radar. Use 3b instead.

### 3b. Dynamic (the reliable method, in an emulator)

This technique works every time (Mesen / bsnes-plus / no$sns):

1. **Find the destination.** The graphic ends up in VRAM. Find where the DMA
   comes from:
   ```bash
   python3 scripts/snes_re_toolkit.py game.sfc --find-dma
   ```
   When `$420B` (MDMAEN) is written, read the **DMA source** (`$4302/$4303`
   address, `$4304` bank):
   - **ROM** bank ($80–$FF, $00–$7D) → **uncompressed** graphic, direct DMA.
   - **WRAM** bank ($7E/$7F) → it was **decompressed** into RAM first.
2. **Write breakpoint** on the destination WRAM buffer (e.g. `$7F:0000`). The
   code that stops there **is** the decompressor (its write loop).
3. **Walk back**: put a breakpoint on the entry of that routine, look at the
   calling `JSL/JSR` and **how the source is set up** (often
   `$xx/$xx+1/$xx+2` in direct page just before the call). That's the pointer
   to the compressed asset (to index through the table from step 2).

### 3c. Trace the source pointer

Many games do: `index → pointer table → source → decompressor → WRAM → DMA →
VRAM`. Once you know the table (2) and the decompressor (3), you have the whole
chain. (Concrete example in this repo: table `$8A:8000` → `$80:F8D8` →
`$7F:64C0`, see `docs/prologue_text_routines.md`.)

---

## 4. Classify the algorithm by reading the loop

Disassemble the decompressor (`--disasm SNES,80`) and look for these signatures:

| Clues in the disassembly | Likely type |
|---|---|
| A **count** byte, then the same byte/word copied repeatedly | **RLE** |
| **Flag bits** (`LSR`/`ROL` on a control byte) choosing *literal* vs *(offset, length)*; copying from the recent **output buffer** | **LZSS / LZ77** (the most common family) |
| A **bit** reader decoding **variable-length** codes; a symbol table | **Huffman / variable-length codes** |
| Reading by **nibbles** (`>>4`, `&0x0F`) + a 4-byte window | **Custom nibble LZ** (e.g. Nage Libre) |
| `JSR (table,X)` dispatching a command per nibble/byte | **Opcode-based codec** (custom) |

Useful 65816 opcodes: `4A` LSR, `0A` ASL, `2A` ROL, `6A` ROR (bit reader);
`B7/A7` `LDA [dp],Y/[dp]` (source read); `97/87` `STA [dp],Y/[dp]`
(destination write); window copy = `LDA dest,X` then `STA dest,Y`.

### "Known" formats to rule out before calling it custom
- Generic **LZSS / LZ77** (8-bit flags, offset+length back-references).
- **Nintendo LZ** ("type $10", header `10 SS SS SS` = decompressed size),
  reused on GB/GBA, sometimes on SNES.
- **LC_LZ1…LZ5** (Lunar Compress), very common in SNES hacks.
- **RLE16** / per-plane RLE.
If the structure matches one of these, tools already exist (Lunar Compress,
etc.) and there's no need to rewrite everything.

---

## 5. Reimplement and **validate bit for bit**

1. Port the decompressor to Python (follow the loop step by step).
2. **Validate** against ground truth: in the emulator, **dump the decompressed
   buffer** (WRAM) after a real call, and compare it byte for byte with your
   Python output. Until they're identical, the port is wrong.
   > Reference model in this repo: `scripts/nl_decompress.py` (reverse of
   > `$80:F8D8`, validated bit for bit against the `$7F:64C0` buffer).
3. Once the decompressor is faithful, write the **compressor** (or reinsert
   uncompressed if there's room), then update the pointer table.

---

## 6. Extract / re-render graphics

```bash
# render a decompressed (binary) dump as a tile sheet
python3 scripts/snes_re_toolkit.py game.sfc --gfx-bin dump.bin,4,16 --out dump.png

# render a raw ROM area (uncompressed asset)
python3 scripts/snes_re_toolkit.py game.sfc --gfx 0x38000,0x1000,2,16 --out logo.png
```

To translate a graphic: find the text tile(s) on the sheet, redraw them (tile
editor: YY-CHR, Tilemolester, or by hand), re-encode at the right bpp,
recompress if needed, and reinsert.

---

## 7. Command summary

| Step | Command |
|---|---|
| Compressed or not? | `--gfx OFF,LEN,BPP,W` |
| Find asset tables | `--find-tables` |
| Spot dense blobs | `--entropy` |
| Candidate decompressors (static) | `--find-decompressors` |
| Locate VRAM uploads | `--find-dma` |
| Disassemble a routine | `--disasm SNES,N` or the `--save-project` project |
| Render a decompressed dump | `--gfx-bin PATH,BPP,W` |

**Dynamic DMA→WRAM tracing (3b)** remains the best method for custom
compression; the static heuristics only help **target** where to look.
