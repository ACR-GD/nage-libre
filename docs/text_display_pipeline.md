# Affichage du texte — Nage Libre (SNES)

## Encodage (important)

**Ce n’est pas du Shift-JIS** dans la ROM. C’est l’encodage classique SNES :

- **1 octet = 1 glyphe** (index dans la police 16×16 en ROM).
- Tuile VRAM affichée ≈ `index + 0xFB` (ex. こ → index `0x0D` → tuile `$108`).
- **Contrôles** : `01` début de ligne, `02` pause, `8D xx` glyphe explicite, `20 xx yy` variante (souvent `20 XX 96`), `FF xx` fin, `FE` fin alternative.

Shift-JIS n’apparaît que si on **force** un décodeur SJIS sur des octets qui sont en réalité des index — d’où du charabia type `ｨｩｬｩ` (octets `A8 A9 AC A9` = quatre glyphes, pas deux kana demi-chasse).

## Pipeline

```
Script (banque $84, opcodes + pointeurs lo/hi/84)
        ↓
Données texte = flux d’index glyphe + contrôles
        ↓
Police 16×16 en ROM → VRAM tileset $5000.w
        ↓
Layer 3, tilemap $7C00.w
```

## Extraction (sans jouer)

```bash
cd NageLibre.Tools
dotnet run -- extract-all
```

Produit :

| Fichier | Rôle |
|---------|------|
| `game_strings.csv` | Texte extrait : `glyph_ids`, `glyph_display`, `japanese` (〓 si kanji non mappé) |
| `glyph_unicode.csv` | Octets avec hiragana/katakana identifiés (gojuon + ancre こ) |
| `glyph_index.csv` | Les 256 octets possibles → offset ROM police (à compléter à la main) |

```bash
dotnet run -- map-glyphs    # régénère glyph_unicode.csv + glyph_index.csv
dotnet run -- extract-all   # applique la table au japonais
```

## Traduction

1. Traduire via `glyph_ids` / atlas `charset_atlas.bmp`.
2. Réinjecter **les mêmes octets** (même longueur, mêmes `FF xx`).
3. Repointer les scripts si le texte change de place (`script_commands.csv`).
