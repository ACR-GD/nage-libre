# Nage Libre: the prologue text engine

*English version of [`prologue_text_routines.md`](prologue_text_routines.md).*

Static analysis (`scripts/disasm_text_routines.py`) plus memory dumps
(`mesen_dumps/*_PC_838103_*`), cross-checked with `Screenshots/Prologue/`.

> **Correction of an earlier model.** There is **no** "text baked into a
> tilemap" on one side and "typewriter" on the other. In reality there is **a
> single glyph engine** (`$80:F433`, sprite/OBJ based, variable width), fed by
> **two different drivers**. The narration is a **bytecode interpreter**.

---

## 1. Overview

```
                       ┌─────────────────────────────────────────┐
   NARRATION           │  Script interpreter  $83:8103            │
   (screens 1–24) ───► │  reads opcodes from $7F:64C0 (the        │
                       │  decompressed block); 66 opcodes (01–42) │
                       └───────────────┬─────────────────────────┘
                                       │ "text" opcodes
                                       ▼
                       ┌─────────────────────────────────────────┐
   typewriter engine   │  $80:F4CA / $80:F4A7  →  loop reading    │
   (shared)            │  16-bit IDs at [$09], end = $FFFF        │
                       └───────────────┬─────────────────────────┘
                                       │ 1 glyph
                                       ▼
                       ┌─────────────────────────────────────────┐
   glyph plotter       │  $80:F433  → 1 OBJ sprite, variable      │
   (shared)            │  width (VWF) via $80:F390                │
                       └─────────────────────────────────────────┘
                                       ▲
   INTERACTIVE UI      ┌──────────────┴──────────────────────────┐
   (birthday,     ───► │  loop  $87:D70C  (driver $87:D63B)       │
    birthstone)        │  reads strings from ROM (tables $87:xx)  │
                       └─────────────────────────────────────────┘
```

| Capture | Screen | Driver |
|---|---|---|
| `screen-1` (stars, *"In a distant world…"*) | narration | script `$83:8103` |
| `screen-2` (clouds, 「この世界を…」) | narration | script `$83:8103` |
| `screen-3` (timestamp `AM06:12`) | narration | script `$83:8103` |
| `screen-4` (dojo, 「よーし!!…」) | narration | script `$83:8103` |
| birthday / birthstone entry (never reached at the time) | UI | loop `$87:D70C` |

---

## 2. The glyph plotter `$80:F433` (shared)

Renders **one** 16-bit character ID (in A) as an **OBJ sprite**, with variable width:

```
LDX $0240               ; index into a ring buffer of OBJs (step 6, wraps at $00C0 = 32 glyphs)
JSR $F390               ; ID → tile number; CARRY = width (set = 2 full width / clear = 1 half width)
STA $0812,X             ; tile number
... $0814,X = width     ;  ← VWF
... $0816,X = attributes/position (palette, X/Y derived from $1141)
; advances the cursor by the width; wraps to a new line past $1144
```

Cursor / margins (the same registers for both drivers):

| Reg | Role |
|---|---|
| `$1141` (low byte) | current X column |
| `$1142` (high byte of `$1141`) | current Y row |
| `$1143` | return column (left margin) |
| `$1144` | bottom/right limit (often `$1E`/`$1F`) |
| `$0240` | OBJ buffer index (ring of 32 glyphs) |

## 3. The typewriter loop `$80:F4A7` / `$80:F4CA`

Two nearly identical entry points (`F4A7 → F4AB`, `F4CA → F4CE`). The core:

```
$80:F4B3  LDA [$09]            ; 16-bit ID at pointer $09/$0A/$0B
          CMP #$FFFF
          BEQ end              ; $FFFF = terminator
          JSR $F433            ; draws the glyph
          INC $09 / INC $09    ; +2 bytes
          BRA $F4B3
```

**Text string format** = a sequence of **16-bit IDs**, terminated by **`$FFFF`**.
`$03FE` = space (full width). The IDs match `docs/kanji_font_index.csv`.

---

## 4. NARRATION driver: the script interpreter `$83:8103`

### Setup (`$83:80E0`)

```
$83:80F0  $06 = $C0          ; script pointer $06/$07/$08 = $7F:64C0
$83:80F4  $07 = $64
$83:80F8  $08 = $7F
$83:80FF  JSL $80F8D8        ; decompresses the scene SCRIPT into $7F:64C0
$83:8103  ── interpreter loop ──
```

The decompressed block at `$7F:64C0` **is not a tilemap**: it's an **opcode
program**. Confirmed by a dump (`zp_direct.txt`: `$06=64C0`, `$07=7F64`, `$08=…7F`).

### Interpreter loop

```
$83:8103  LDA [$06]          ; reads a 16-bit opcode
          CMP #$0001 .. #$0042 → JSR handler ; BRL $8103   (66 opcodes)
          CMP #$FFFF → end of script ($83:83E5: JSL $8088BB ; RTS)
          (each handler advances $06 by its operand count with INC $06)
$83:83E2  BRL $8103          ; next opcode
```

### Operand of the "text" opcodes

Text handlers read an **offset** word, compute `$09 = $64C0 + offset`
(`bank $0B = $7F`), then call `$80:F4CA`. So the text is a **string of IDs
stored further down the same decompressed block**, which is exactly the area we
patch (`$7F:65E2`, `$7F:66E2`…).

```
$83:83EE (opcode 1)   cursor col=8, margin 8..1E
          LDA [$06] (offset) ; +$64C0 → $09 ; $0B=$7F
          JSL $80F4CA        ; ← renders the text line
          (advances the row, INC $06 ×2)
$83:8444 (opcode 0x0B) same but col=1, margin 1..1F
```

### Full table of the 66 opcodes (`python3 scripts/disasm_text_routines.py opcodes`)

| Category | Opcodes | Role |
|---|---|---|
| **Text** (F4CA/F4A7 + `+64C0`) | `01 0B 10 11 12 13` | render a line (offset → ID string in the block) |
| **Text** (F4A7) | `02 03 04 05 06 07 0C 0D 1C 1D 1E 1F 20 21 22 3C` | render / position text (box variants, speed) |
| **Text + ptr** | `07 0D 3A 3B` | text with a computed pointer |
| **Pointer** (`+64C0`) | `08 09 0A 23 24 25 26 27 28 29 2A 2B` | load an address/offset in the block (sprite, palette, table) |
| **Decompression** (FA63) | `17 19 1A 1B 3D 3E 3F 40 41 42` | load a new background / tile set (screen change) |
| **Control** | `0E 0F 14 15 16 18 2C–3B (rest)` | timing, fades, scrolling, flags, sync |

> The table above is generated automatically; it classifies handlers by call
> signature (`JSL $80F4CA`, `JSL $80F4A7`, `ADC #$64C0`, `JSL $80FA63`). The
> "Control" row groups handlers with no text/decompression signature (animation,
> waiting, palette, cloud scrolling, etc.).

### Opcode sizes (decompilation)

The size (bytes consumed from `$06`) of each opcode is derived by counting the
handler's `INC $06` (following internal `JSR`s). **Validated** against the
`$06` deltas seen in successive dumps (`mesen_dumps/*_PC_838103_*`):

| opcode | size | observed |
|---|---|---|
| `20` | 2 bytes | 2 ✓ |
| `23` | 4 bytes | 4 ✓ |
| `29` | 4 bytes (delegates to `23` via `JSR $958C`) | 4 ✓ |
| `2B` | 4 bytes | 4 ✓ |
| `2C` | 2 bytes | 2 ✓ |

### Opcode meanings (confirmed by decompiling the prologue)

The **`$7F:64C0` block holds the whole narration script** (all 24 screens), not
one screen at a time. The program is at `+0000…+0120`, then the **string data**
starts at `+0122`. Opcodes actually used:

| opcode | size | observed role |
|---|---|---|
| `2B` | 4 bytes | **full-screen text line** (stars/clouds/timestamp); operand = offset → string, rendered via `$80:F5AC` |
| `26` | 4 bytes | **dialogue line** (character); operand = offset → string |
| `29` | 4 bytes | line positioning / setup (a parameter, not an offset) |
| `24` / `25` | 6 bytes | load / release a character portrait (2 params) |
| `2C` | 2 bytes | pause / wait for a button press at the end of a line |
| `20` | 2 bytes | "continue" prompt (fixed ROM text `$83:86B3`, e.g. the ▼ arrow) |
| `27` / `3A` | 2 bytes | control (sync / effect) |
| `23` | 4 bytes | data-table pointer (same `$09=+64C0` addressing, **not** text) |
| `FFFF` | — | end of program (the string data follows) |

> "Text line" opcodes can be recognised by the `ADC #$64C0 / STA $09` pattern
> (`69 C0 64 85 09`): the operand is an **offset** into the block, pointing to
> an ID string terminated by `$FFFF`. The full decoded listing is in
> **`docs/prologue_scene_script.md`**.

### How a narration screen plays out

1. A **decompression** opcode (`17/19/1A/1B/3D…`) loads the background (stars, clouds, dojo…).
2. One or more **text** opcodes (`01/0B/…`) render the lines of the box, each
   pointing by offset to an ID string in the `$7F:64C0` block.
3. **Control** opcodes handle waiting for a button (`$0214`), fades and scrolling.
4. At the end of the scene: `$FFFF` → return; the next screen calls `$80:F8D8`
   again with a new script.

### Validation from a dump (`mesen_dumps/..._PC_838103_001`)

Strings read at `$7F:64C0 + offset` (terminated by `$FFFF`, `$03FE` = space):

```
+0142 : 16E 434 436 438 43A 43C 46C 46E 470 3FE…   ← ASCII fragment (0x4xx) = patched English text
+0162 : 2E6 032 068 33A 33C 0AE 304 058 330 …      ← Japanese ID string (to transcribe)
```

IDs `0x4xx` are our ASCII glyphs (screen 1 patch); IDs `0x0xx–0x3xx` are the
kana/kanji to map in `docs/kanji_font_index.csv`.

---

## 5. UI driver: the `$87:D70C` loop (character creation)

Started by the `$87:D63B` driver after the narration (`$87:D6C0  JSR $D70C`).
For each step: `$87:D9D7` decompresses the background, loads the scene params
(`$17D6`→`$17D4/5`), then renders text from **ROM tables** via `$80:F4A7`:

| Routine | `$1141` | String source |
|---|---|---|
| `$87:DA8C` | `$0E11` | table `$87:DABB` (4-byte step) → 8-ID strings (`$87:89F1`, `8A01`, …) |
| `$87:DA3B` | `$0C0F` | `$87:8965` (月, month), `$87:8969` (日, day), number conversion via `$80:F6E8` |
| `$87:D990` | `$0405` | `$87:896D` = 「誕生日をおしえてね」 ("tell me your birthday", 9 IDs) |

Confirmed ROM strings: `$87:896D = 02DE 01DA 02C8 00AE 0020 003A 001C 0058 0066`
(= the 9 glyphs 誕生日をおしえてね).

---

## 6. The end-of-prologue bug: root cause

**Prologue call graph** (master sequencer in bank `$80`):

```
$80:9626/963A  LDA #scene ; JSL $83:80D7   ← narration (interpreter $83:8103, 24 lines)
        …
$80:9393       JSL $87:D63B                ← character-creation driver (birthday)
$87:D63B  …    JSR $D70C  (×5 heroines)    ← birthday entry (loop)
$87:D6D4       JSR $DCCB                    ← transition to the game (after 5 entries)
```

"`$87:DCCB` is never hit" ⇒ the freeze happens **before** the end of the
birthday loop, typically during or just after the narration.

### Root cause found (old screen-1 patch)

The old `patch_nl_prologue_en.py` wrote the English string at offset
**`+0122`** (`$7F:65E2`), while opcode `0x2B` reads the string at **`+0124`**
(`$7F:65E4`), and it wrote **30 words with no explicit `$FFFF` terminator**.
The original Japanese string ends with `$FFFF` at word 29, which is exactly
**`+015E`**, and the 30th word written **overwrote it with a space**. Result:
the text engine (`$80:F5AC`/`F4CE`) **no longer finds the terminator** and runs
on into the next string (`+0162` = screen 2…), so the box spills over and then
freezes. The "clear `$7F:66E2`" was a band-aid over that overflow.

### Fix

`build_prologue_translation.py` (§8) writes each line **at the right offset**
(from the decompiler) and **adds a `$FFFF` terminator** right after the English
→ a clean stop, no overflow. The new `nl-prologue-en.sfc` should therefore
**no longer freeze** on this path. Test this first.

> If a freeze remains, the **`scripts/mesen_transition_trace.lua`** tracer logs
> each step of the hand-off and samples the PC: the last `REACHED` step and the
> PC that repeats during the freeze locate the exact cause (narration
> `$83:8xxx`, sequencer `$80:9xxx`, or driver `$87:Dxxx`).

---

## 7. Key addresses

| Address | Role |
|---|---|
| `$80:F433` | glyph plotter (OBJ sprite, VWF), **shared** |
| `$80:F390` | ID → tile + width (carry) |
| `$80:F4A7→F4AB` / `$80:F4CA→F4CE` | typewriter loop (IDs at `[$09]`, end `$FFFF`) |
| `$80:F8D8→F8DC` | scene-script decompressor → `$7F:64C0` |
| `$80:FA63` | tile/background decompressor (background opcodes) |
| `$83:80E0` | init of the script pointer `$06/$07/$08 = $7F:64C0` |
| `$83:8103` | **script interpreter** (66 opcodes, end `$FFFF`) |
| `$83:83EE` / `$83:8444` | "text line" handlers (opcodes 1 / 0x0B) |
| `$7F:64C0` | base of the decompressed block = **the scene's script + strings** |
| `$1141`–`$1144`, `$0240` | cursor / margins / OBJ index |
| `$87:D63B` | prologue init driver |
| `$87:D70C` | UI loop (character creation / birthday) |
| `$87:DA8C` / `$87:DA3B` / `$87:D990` | UI text rendering (tables `$87:DABB`, `$87:896x`) |
| `$87:DABB` | UI string pointer table |
| `$0214` | waiting-for-button flag |

---

## 8. Translation workflow (table-driven reinsertion)

Rather than patching hard-coded tilemap positions, each line is reinserted at
its **offset** in the decompressed block. Two files:

- **`docs/prologue_translation.csv`**: the working table (generated). Columns:
  `offset_hex, n_ids, slot_words, jp_decoded, en`. Fill in the **`en`** column
  line by line; `slot_words` = maximum number of pairs (≈ 2 characters each).
- **`build_prologue_translation.py`**: reads the CSV, encodes the English (VWF
  pairs + glyphs via `ScatterAllocator`), builds a **ROM table**
  `{offset, count, ids…}` and a **hook** at `$83:F8E3` that, after
  `JSL $80F8D8`, copies each English string to `$7F:64C0 + offset`, terminated
  by `$FFFF` (no leftover Japanese is shown).

```bash
python3 scripts/decompile_prologue_script.py csv   # (re)generates the working table
# … fill in the CSV's `en` column …
python3 build_prologue_translation.py              # produces nl-prologue-en.sfc
```

How the (generated) hook works:

```
$83:F8E3  JSL $80F8D8            ; original decompression
          (save registers + $0C)
          LDX #table             ; walk the table in bank $83
loop:     LDA.l table,X          ; offset; $FFFF → end
          ADC #$64C0 → $09/$0A/$0B = $7F:64C0+offset
          count → $0C (bytes); copy count words via STA [$09],Y
          → next line
          (restore) RTL → $8103 (interpreter)
```

**Limits to respect**
- The encoded `en` must be ≤ `slot_words` (otherwise the builder stops with an
  explicit error; the next string would be overwritten).
- Font budget: ~160 free VWF pairs in total (`ScatterAllocator`). Reuse
  digrams (the `p2id` cache deduplicates automatically).
- ROM space: hook + table ≤ ~1.8 KB in bank `$83` (`$F8E3`–`$FFE0`). Enough
  for the 24 lines.
- **End-of-prologue bug** (narration → UI transition): **not covered** by this
  path; see §6. This builder only handles the content of the narration strings.

> `build_prologue_translation.py` **generalises** the old
> `patch_nl_prologue_en.py` (screen 1 only, hard-coded positions). Use one *or*
> the other, not both.

## 9. Reproducing the analysis

```bash
python3 scripts/disasm_text_routines.py opcodes        # table of the 66 classified opcodes
python3 scripts/disasm_text_routines.py 83 8103 40      # start of the interpreter
python3 scripts/disasm_text_routines.py 80 F433 55      # glyph plotter
python3 scripts/disasm_text_routines.py 87 D70C 80      # UI loop
python3 scripts/decompile_prologue_script.py            # decompiles the $7F:64C0 script from a dump
```

Reference output: **`docs/prologue_scene_script.md`** (the 24 decoded lines).
Translation table: **`docs/prologue_translation.csv`**.
