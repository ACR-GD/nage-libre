# Nage Libre — outils de traduction (SNES)

Projet d'analyse pour traduire **Nage Libre: Seijaku no Suishin** (スーパーファミコン, Varie, 1995).

## Fichiers attendus

- `Nage Libre - Seijaku no Suishin (Japan).sfc` — ROM LoROM, 1,5 Mio
- `*_1.mss` (optionnel) — savestate Mesen2 au moment du premier texte

## Outils C# (`NageLibre.Tools`)

Prérequis : .NET 8 (`brew install dotnet@8`).

```bash
cd NageLibre.Tools
export DOTNET_ROOT="/opt/homebrew/opt/dotnet@8/libexec"
export PATH="$DOTNET_ROOT:$PATH"

dotnet run -- export
dotnet run -- catalog-font      # atlas + inventaire glyphes
dotnet run -- map-glyphs        # table octet → hiragana/katakana (glyph_unicode.csv)
dotnet run -- extract-all       # texte + script + japonais (〓 si kanji non mappé)

Prologue New Game (encodage **16 bits**, bank `$87`) : voir `docs/prologue_text_engine.md` ([EN](docs/prologue_text_engine.en.md)).
dotnet run -- decompress-scan   # scan LZ01/10/11/12
dotnet run -- extract-mesen
dotnet run -- decompress 101000
dotnet run -- tile 50000 2
```

Les CSV sont écrits dans `docs/` :

| Fichier | Contenu |
|---------|---------|
| `rom_info.csv` | En-tête, taille, encodage texte |
| `memory_map.csv` | Régions ROM |
| `bank_entropy.csv` | Entropie par banque 32 Ko |
| `compression_candidates.csv` | Blocs LZ10/LZ01 possibles |
| `script_events_bank04.csv` | Scripts banque `$84` @ `0x20000` |
| `text_8d_encoding.csv` | Chaînes préfixe `0x8D` (encodage custom) |
| `font_metrics.csv` | Table `81 87 XX` @ `0xAFDD` |
| `palettes_from_savestate.csv` | CGRAM BGR555 (savestate) |
| `mesen_savestate_fields.csv` | Champs MSS Mesen2 |
| `tcrf_notes.csv` | Easter eggs [TCRF](https://tcrf.net/Nage_Libre) |

## Découvertes utilisateur (`Screenshots/`)

- Police **16×16** = **4 tuiles 2bpp 8×8** (coin HG +1, +16, +17 en VRAM).
- **こ** (ko), quadrant HG : tuile **$108**, VRAM **$5840.w** (= octet **$B080**), tileset **$5000.w**.
- Même glyphe en ROM @ **0x28540** (`$85:8540`) — 4 tuiles **contiguës** en fichier.
- Tilemap dialogue : **$7C00.w**, couche 3, format **2bpp**.
- Voir `docs/user_findings.csv` et captures Mesen2 dans `Screenshots/`.

## Comparaison Varie (`varie-games/`)

ROMs fournies : Super F-1 Hero, Putty Moon, Stardust Suplex, Undercover Cops.  
Même motif de pointeurs `0x84` sur plusieurs titres ; la signature du こ n’apparaît que dans Nage Libre.  
Détails : `docs/varie_games_comparison.csv`.

## Découvertes principales

- **LoROM**, titre `NAGE LIBRE`, little-endian.
- Le texte **n'est pas en Shift-JIS** : **1 octet = index glyphe** (+ contrôles `01`/`02`/`8D`/`20`/`FF`). Voir `docs/text_display_pipeline.md`.
- Les **scripts / événements** sont en banque **`$84`** avec pointeurs `lo, hi, 0x84` (données vers `0x20000+`).
- **Compression** : nombreux en-têtes `0x10` / `0x01` (formats Nintendo courants) — à valider par essai `decompress`.
- **Graphismes** : tuiles 2bpp présentes en ROM et en VRAM (savestate) ; dialogue = tuiles + CGRAM.
- **TCRF** : messages développeur (anniversaires 11/25) — texte à extraire après reverse de l'encodage.

## Limitations SNES (rappel)

- VRAM 64 Ko, CGRAM 512 octets (256 couleurs × BGR555).
- Tuiles 8×8 en 2bpp (16 o) ou 4bpp (32 o) ; tilemaps 16 bits (VHPPTTTT TTTTTTTT).
- WRAM 128 Ko ; banques 24 bits `$BB:OOOO`.

## Prochaines étapes suggérées

1. Identifier le **décompresseur exact** (tracer JSL fréquents depuis le code `@ $008xxx`).
2. Construire la **table glyphe ↔ ID** via corrélations savestate / première ligne de dialogue.
3. Étendre l'export des **chaînes décompressées** une fois le format confirmé.
