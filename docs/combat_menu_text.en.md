# Battle & menu text: bank `$87`

*English version of [`combat_menu_text.md`](combat_menu_text.md).*

> Found by scanning the ROM for 16-bit ID strings terminated by `FFFF`, then
> **reading them visually** by rendering the glyphs (`scripts/render_text.py`),
> since the automatic Unicode mapping was incomplete. Captures in
> `docs/menu_strings/page*.png`.

## Location

All **interface, battle and system** text is stored **uncompressed** in bank
`$87`, as little-endian 16-bit font IDs terminated by `FFFF`, **the same format
as the narration block**. Unlike the prologue narration (compressed → WRAM
`$7F:64C0`), these strings are read straight from ROM by the `$80:F4A7`
typewriter engine.

| Area | File range | SNES | Contents |
|------|------------|------|----------|
| Names | `0x038077`–`0x0385xx` | `$87:8077`+ | ~230 names (surname + given name), character creation |
| Clubs | within the block | — | Basketball, Tennis, Kendo, Karate, Kyūdō, Lacrosse, gym, occult, science, dance, ikebana, music, drama, manga, sewing… + `一般生徒` (ordinary student), `ボス` (Boss) = **enemy types** |
| **Battle** | `0x0386D9`–`0x03886B` | `$87:86D9`+ | Battle messages (attack, damage, stats…) |
| **Menus/system** | `0x038879`–`0x0389EB` | `$87:8879`+ | Save / load / shop / birthday |
| Birthstones | `0x0389F1`–`0x038AA1` | `$87:89F1`+ | 12 birthstones |
| **Hub** | `0x038AB1`–`0x038B31` | `$87:8AB1`+ | Main menu (Save, Shop…) + the 6 *Libération* gems |

> Full table of offsets + JP + proposed EN: **`docs/combat_menu_translation.csv`** (67 strings).

## Battle messages (`$87:86D9`+)

| SNES | JP | Proposed EN |
|------|----|-------------|
| `$87:86DF` | `[name]の攻撃！！` | `[name]'s attack!!` |
| `$87:86ED` | `[n]のダメージ！！` | `[n] damage!!` |
| `$87:86FB` | `回復した` | `recovered!` |
| `$87:8705` | `防御がアップ！！` | `Defense up!!` |
| `$87:8797` | `ダメージをあたえられない！！` | `Cannot deal damage!!` |
| `$87:87EB` | `[name]を倒した！！` | `Defeated [name]!!` |
| `$87:87F7` | `[n]ゴールド手に入れた！！` | `Got [n] Gold!!` |
| `$87:8897` | `[name]の超必殺技だ！！` | `[name]'s ultimate move!!` |
| `$87:8749` | `逃げろぉ！！` | `Run away!!` |
| `$87:87B3` | `逃げるな　待てぇ！！` | `Don't run, wait!!` |
| `$87:8755` | `…おいつかれてしまった！！` | `...got caught!!` |
| `$87:87C7` | `…おいついた` | `...caught up` |
| `$87:876F` | `…なんとか、逃げられた…` | `...barely got away...` |
| `$87:87D5` | `…逃げられてしまった` | `...they got away` |
| `$87:8731` | `ただいま着がえ中です…` | `Changing outfit now...` |
| `$87:8715` | `入れかえるカードを選んでね` | `Pick a card to swap` |

### Stat increases
`[stat] が [n] に上がった！！` / `… 選べるようになった！！` (assembled at run time).

| SNES | JP | EN | SNES | JP | EN |
|------|----|----|------|----|----|
| `$87:8819` | `体力` | Stamina | `$87:8833` | `精神力` | Spirit |
| `$87:8821` | `腕力` | Power | `$87:883D` | `素早さ` | Speed |
| `$87:8829` | `防御力` | Defense | `$87:8847` | `レベル` | Level |

## System menus (`$87:8879`+)

| SNES | JP | EN |
|------|----|----|
| `$87:899B` | `どのファイルにセーブする？` | `Which file to save?` |
| `$87:88BF` | `どのファイルをロードする？` | `Which file to load?` |
| `$87:89C5` | `まえのデータをけしますよ` | `Old data will be erased` |
| `$87:88A7` | `このデータでいいかな？` | `Is this data OK?` |
| `$87:89B7` | `ファイル` | `File` |
| `$87:89EB` | `なし` | `Empty` |
| `$87:8885` | `はい / いいえ` | `Yes / No` |
| `$87:89DF` | `だめ / よい` | `No / Yes` |
| `$87:896D` | `誕生日をおしえてね` | `Tell me your birthday` |
| `$87:8981` | `これで誕生日はいいかな？` | `Is this birthday OK?` |
| `$87:8879` | `誕生石効果` | `Birthstone effect` |
| `$87:88F7` | `キャラクターを入れかえます` | `Swap character` |

### Shop
| SNES | JP | EN |
|------|----|----|
| `$87:88DB` | `カードを買います` | `Buy a card` |
| `$87:8913` | `カードをうります` | `Sell a card` |
| `$87:892F` | `お金がたりません！！` | `Not enough money!!` |
| `$87:8949` | `これ以上買えません` | `Can't buy more` |

## Main menu / Hub (`$87:8AB1`+)

| SNES | JP | EN |
|------|----|----|
| `$87:8AB1` | `どうしますか？` | `What will you do?` |
| `$87:8AC1` | `買い物` | `Shop` |
| `$87:8AC9` | `部活選択` | `Clubs` |
| `$87:8AD3` | `セーブ` | `Save` |
| `$87:8ADB` | `スタート` | `Start` |
| `$87:8AE5` | `EX` | `EX` |

*Libération* gems (`$87:8AEB`+): `「リ」「ベ」「ラ」「ジ」「オ」「ン」の宝玉` → **リベラジオン** = *Libération*.

## Birthstones (`$87:89F1`+)

Garnet, Amethyst, Aquamarine, Diamond, Emerald, Moonstone, Ruby,
Agate, Sapphire, Opal, Topaz, Lapis lazuli (`ガーネット`…`ラピスラズリ`).

## Injection builder

`build_combat_menu_translation.py` rewrites these strings **in place** (VWF
pair encoding, like the prologue). No hook is needed because the text is read
straight from ROM.

```bash
python3 build_combat_menu_translation.py            # hub menu only → nl-menu-en.sfc
python3 build_combat_menu_translation.py --cat hub,menu,combat
python3 build_combat_menu_translation.py --all      # every category
```

- Constraint: `english_words ≤ slot_words` (the `FFFF` stays in the original
  slot), i.e. **≤ `slot_words × 2` letters**. The builder refuses and lists any
  overflow.
- The font allocator excludes **every** ID referenced in the `$87` block
  (`0x038077`–`0x038C01`): no name/club/birthstone glyph gets overwritten
  (verified).
- **Shared font pool**: this builder and `build_prologue_translation.py`
  allocate from the same pool of free IDs. For a single ROM, use the **unified
  builder** `build_full_translation.py`, which shares one allocator:

  ```bash
  python3 build_full_translation.py        # prologue + battle + menus → nl-full-en.sfc
  ```

  Output `nl-full-en.sfc`: prologue (hook in $83 → WRAM) **+** battle/menus (in
  place in $87), **295 unique pairs** out of 651 available, no collisions (a
  single `ScatterAllocator`). The separate outputs `nl-menu-en.sfc` /
  `nl-prologue-en.sfc` are still available to test each part on its own.

## Font reserve (collision avoidance): IMPORTANT

The font is **dense**: almost every tile is a real glyph, with hardly any empty
tiles. The English pairs therefore reuse **unused kanji**. To avoid overwriting
a glyph that is displayed, the allocator excludes:

1. the `$87` text block (`0x038077`–`0x038C01`);
2. the **prologue IDs** (compressed script → WRAM `$7F:64C0`), frozen in
   `docs/reserved_font_ids.txt` (generated from a WRAM dump of the prologue);
3. every **uncompressed text table** pointed to by code
   (`dump_all_scripts.find_all_script_pointers`);
4. the **odd neighbour** `N-1`/`N+1` of each pair (a 16×16 tile at `N`
   overlaps the half-glyphs of `N±1`).

> **Regression fixed** (timestamps `ＡＭ０６：１２` shown as `keup : adsc`):
> the timestamp glyphs, used by the compressed prologue, were being
> reallocated for English. The reserve above protects them. After the fix:
> 295 pairs / 394 free IDs, **0 collisions**.

> ⚠ If you translate new **compressed** scenes (battles, dialogue), regenerate
> `reserved_font_ids.txt` from a WRAM dump of that scene, otherwise its glyphs
> may be overwritten.

## Battle command menu (待機/攻撃/アイテム/交換/ポケベル/アニメ/セーブ)

*(This section was written before the menu was translated; the solution below
is what was implemented.)* Analysis of the battle dumps
(`nl-full-en-battle-menu-SnesWorkRam.dmp` + `…VideoRam.dmp`):

### What the dumps prove

1. **Not in WRAM as 16-bit IDs.** The sequence `セーブ` (`00E4 0092 011A`) and
   `アイ` (`00B2 00B6`) **cannot be found** in the battle WRAM. Scanning every
   `FFFF`-terminated string only finds the dialogue buffer `$7F:64C0` (region
   `0x16xxx`) plus a few fragments: **no menu**.
2. **The battle menu uses a DEDICATED 8×8 FONT**, separate from the 16-bit ID
   system. Rendering the VRAM (`docs/menu_strings/battle_vram_2bpp.png` and
   `…_band.png`) clearly shows, loaded together:
   - **the full Latin alphabet** `ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`;
   - the **names** `SYOKO MEI YUI MIKI RYOKO`;
   - the labels `TIME SPEED`, `command`, `item`;
   - a row of **kanji/katakana** = the menu commands (待機/攻撃/…).
3. This font doesn't appear **byte for byte** in the ROM → it's stored in
   another format (expanded 1bpp, or compressed) and then DMA'd to VRAM.

### What it means for the translation: good news

Since **the Latin alphabet is already in** the battle font, translating the
menu needs **NO font editing**: it's enough to rewrite the **menu's source
string** (sequence of tile indexes/codes) with Latin codes (`S`,`A`,`V`,`E`…).
A system completely separate from the existing `$87` builder → no risk of
colliding with the existing work.

### Full mechanism (VRAM/WRAM traces + disassembly)

The menu is drawn by the **shared text engine** in bank `$80`:

- Entry `$80:F8DC` (via `$80:F8D8`). Reads a **compressed** stream (nibble
  commands) through the 24-bit pointer `[$09]/$0A/$0B` (the **same** text
  pointer as the prologue). Loop: `LDA [$09]` → `JSR ($F909,X)` (nibble
  dispatch).
- Jump table `$80:F909`, commands `0x0`–`0xF`:
  - `0x0`–`0x7` → `$F92B`: **decodes the glyph pixels** (nibbles via `$FA42`)
    into the font buffer `[$06]` (= `$7E:2000+`, tile N at `+N*16`),
    **allocates** the tile index **dynamically** (counter `$02DD`), and stores
    the 4 indexes of the 16×16 glyph in `$02DF`–`$02E2`.
  - `0xC`–`0xF` (`$F9F1`/`$F9F9`/`$FA01`/`$FA09`): **write the 4 tilemap
    entries** (via `$FA11`) into the BG3 shadow at `$7E:4000+`.
- The font shadow `$7E:2000+` and the tilemap shadow `$7E:4000+` are then
  **DMA'd** to VRAM (font char base `0xA000`, BG3 tilemap word `0x7C00`).
- The menu is drawn **only once** when it opens (≈ frame 95/96).

PCs seen in the trace: font `$80:F948`, tilemap `$80:F9C7`/`$80:F9D2`.

### Exact menu layout (from the `$7E:4000` tilemap shadow)

Window: border tx21 (`$68`) / tx29 (`$69`), **inner = tx22–28 (7 cells)**.
Each command = 2 tilemap rows (top/bottom, 16×16 glyphs). Palette `$20`
(normal) / `$24` (selected line).

| Rows (ty) | JP | top tiles | Proposed EN |
|-----------|----|-----------|-------------|
| 5–6   | 待機     | `90–94`/`A0–A4` | WAIT |
| 7–8   | 攻撃     | `B5–B9`/`C5–C9` | ATTACK |
| 9–10  | アイテム | `95–99`/`A5–A9` | ITEM |
| 11–12 | 交換     | `9A–9E`/`AA–AE` | SWAP |
| 13–14 | ポケベル | `B0–B4`/`C0–C4` | PAGER |
| 15–16 | アニメ   | `D0–D4`/`E0–E4` | ANIME |
| 17–18 | セーブ   | `BA–BE`/`CA–CE` | SAVE |

### Chosen solution: tilemap rewrite (NO font editing)

The battle font **already contains the Latin alphabet** loaded in VRAM:
`0x40`–`0x5A` = `A`–`Z`, `0x5B`–`0x64` = `0`–`9` (verified:
`docs/menu_strings/combatfont_full.png`). Letter `c` → tile `0x40 + (c-'A')`.

→ **Implemented** (`build_combat_command_menu.py`, part of
`build_full_translation.py`): the `$80:F8D8` wrapper (`JSR $F8DC ; RTL`) is
redirected to `JML $80:FA80` (free area, 878 bytes). The hook runs the original
rendering, then, if the menu's signature is present in the font buffer
(`$7E:2904`==`$3718` **and** `$7E:2B56`==`$7E01`), copies with **MVN
$7E,$7E** the Latin tiles (letters already loaded at `$40`–`$5A`) over the
glyph tiles of the 7 commands (letters in the **top** tile, the bottom left
empty). The tilemap references those tiles → an English menu whatever the
position/animation/selection. **No font editing, no recompression.**

**Limit**: 5 tiles (8 px) per command → 5 letters max. `攻撃` becomes **FIGHT**
(ATTACK = 6 letters doesn't fit). Labels: WAIT / FIGHT / ITEM / SWAP / PAGER /
ANIME / SAVE.

> Two-point signature + Latin letters already present → the hook only fires
> on the battle menu. To watch during testing: that no other text screen is
> affected.

## Translation notes

- **Same format as the prologue**: 16-bit IDs + `FFFF`. Reinserted in place
  (VWF pair encoding, ≤ `slot_words×2` Latin letters).
- **Strings assembled at run time**: `[name]の攻撃`, `[stat]が[n]に上がった`.
  The Japanese order (particle `の` / `が`) doesn't match English → plan a small
  change to the assembly code, or phrasings that work in both orders.
- **Space**: each string has a fixed `slot_words` (see the CSV). Names/clubs
  share substrings, handle them separately.
