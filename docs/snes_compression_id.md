# Identifier les graphismes à traduire et les compressions custom (SNES)

Guide pratique, utilisable sur n'importe quel jeu, qui accompagne
`scripts/snes_re_toolkit.py`. Objectif : trouver les **graphismes contenant du
texte** (logos, « PUSH START », libellés de menu, écrans-titres) et déterminer
**comment ils sont stockés/compressés** pour pouvoir les extraire, traduire et
réinjecter.

---

## 0. Vocabulaire express

| Terme | Sens |
|---|---|
| Tuile (tile) | 8×8 pixels. Formats SNES : **2bpp** (16 o), **3bpp** (24 o), **4bpp** (32 o), **8bpp** (64 o), **Mode7** (64 o linéaire). |
| Tilemap | Grille d'indices de tuiles (le « quoi afficher où »). |
| CHR / VRAM | Mémoire vidéo où vivent les tuiles à l'affichage (64 Ko). |
| DMA | Transfert rapide ROM/WRAM → VRAM (registres `$43xx`, déclenché par `$420B`). |

---

## 1. Le graphisme est-il compressé ? (test en 30 s)

Rends la zone **directement** comme tuiles brutes :

```bash
python3 scripts/snes_re_toolkit.py jeu.sfc --gfx 0xOFFSET,0x2000,4,16 --out test.png
```

- L'image montre des **tuiles propres** (lettres, dessins nets) → **non compressé**.
  Ajuste `bpp` (2/4/8) et l'offset si c'est décalé/brouillé mais régulier.
- L'image est un **bruit structuré** quel que soit le bpp → **compressé** (ou
  c'est du code/des données). Passe à l'étape 2.

> Astuce : les écrans-titres et logos sont presque toujours compressés ; les
> petites polices de texte sont souvent **non** compressées (accès direct rapide).

---

## 2. Localiser les blobs compressés

```bash
python3 scripts/snes_re_toolkit.py jeu.sfc --find-tables --entropy
```

- **Tables de pointeurs** (`--find-tables`) : les assets compressés sont presque
  toujours indexés par une table de pointeurs 2 ou 3 octets. Une table juste
  avant une grande zone « bruitée » pointe souvent vers les blobs compressés.
- **Entropie** (`--entropy`) : régions denses = candidates. ⚠️ Indice faible :
  une compression **à nibbles/bits** (fréquente) reste à entropie modérée
  (~6.5–7.1 par octet), et des tuiles 4bpp brutes peuvent être denses aussi.
  Ne jamais conclure sur l'entropie seule.

---

## 3. Trouver le décompresseur (la vraie clé)

### 3a. Statique (rapide, bruité)

```bash
python3 scripts/snes_re_toolkit.py jeu.sfc --find-decompressors
```

Repère les boucles `décalages (lecteur de bits) + copie fenêtre (LZ) + boucle`.
**Limite** : les décompresseurs à **table de saut** (`JSR (table,X)`) sont
éclatés en sous-routines et passent sous le radar. Utiliser alors 3b.

### 3b. Dynamique (méthode fiable, émulateur)

C'est LA technique qui marche à tous les coups (Mesen / bsnes-plus / no$sns) :

1. **Repérer la destination.** Le graphisme finit en VRAM. Cherche d'où vient le
   DMA :
   ```bash
   python3 scripts/snes_re_toolkit.py jeu.sfc --find-dma
   ```
   À l'écriture de `$420B` (MDMAEN), lis la **source DMA** (`$4302/$4303` adresse,
   `$4304` banque) :
   - banque **ROM** ($80–$FF, $00–$7D) → graphisme **non compressé**, DMA direct.
   - banque **WRAM** ($7E/$7F) → il a été **décompressé** en RAM d'abord.
2. **Breakpoint en écriture** sur le tampon WRAM destination (ex. `$7F:0000`).
   Le code qui s'y arrête **est** le décompresseur (sa boucle d'écriture).
3. **Remonter** : pose un breakpoint à l'entrée de cette routine, regarde le
   `JSL/JSR` appelant et **comment la source est mise en place** (souvent
   `$xx/$xx+1/$xx+2` en page directe juste avant l'appel) → c'est le pointeur de
   l'asset compressé (à indexer via la table de l'étape 2).

### 3c. Tracer le pointeur source

Beaucoup de jeux font : `index → table de pointeurs → source → décompresseur →
WRAM → DMA → VRAM`. Une fois la table (2) et le décompresseur (3) connus, tu as
toute la chaîne. (Exemple concret dans ce dépôt : table `$8A:8000` →
`$80:F8D8` → `$7F:64C0`, cf. `docs/prologue_text_routines.md`.)

---

## 4. Classer l'algorithme en lisant la boucle

Désassemble le décompresseur (`--disasm SNES,80`) et cherche ces signatures :

| Indices au désassemblage | Type probable |
|---|---|
| Octet de **compte** puis recopie répétée du même octet/mot | **RLE** |
| **Bits de drapeau** (`LSR`/`ROL` sur un octet de contrôle) qui choisissent *littéral* vs *(offset,longueur)* ; copie depuis le **tampon de sortie** récent | **LZSS / LZ77** (la famille la plus courante) |
| Lecteur de **bits** décodant des codes de **longueur variable** ; table de symboles | **Huffman / codes à longueur variable** |
| Lecture par **nibbles** (`>>4`, `&0x0F`) + fenêtre 4 octets | **LZ custom à nibbles** (ex. Nage Libre) |
| `JSR (table,X)` dispatchant une commande par nibble/octet | **codec à opcodes** (custom) |

Repères opcodes 65816 utiles : `4A` LSR, `0A` ASL, `2A` ROL, `6A` ROR (lecteur de
bits) ; `B7/A7` `LDA [dp],Y/[dp]` (lecture source) ; `97/87` `STA [dp],Y/[dp]`
(écriture dest) ; copie fenêtre = `LDA dest,X` puis `STA dest,Y`.

### Formats « connus » à reconnaître avant de crier au custom
- **LZSS / LZ77** générique (drapeaux 8 bits, back-reference offset+len).
- **Nintendo LZ** (« type $10 », en-tête `10 SS SS SS` = taille décompressée) —
  réutilisé sur GB/GBA, parfois SNES.
- **LC_LZ1…LZ5** (Lunar Compress) — très répandu sur les hacks SNES.
- **RLE16** / RLE par plan.
Si la structure colle à l'un d'eux, des outils existent (Lunar Compress, etc.)
et inutile de tout réécrire.

---

## 5. Réimplémenter et **valider bit-à-bit**

1. Porte le décompresseur en Python (suis la boucle pas à pas).
2. **Valide** contre la vérité terrain : dans l'émulateur, **dumpe le tampon
   décompressé** (WRAM) après un appel réel, et compare octet par octet à ta
   sortie Python. Tant que ce n'est pas identique, le portage est faux.
   > Modèle de référence dans ce dépôt : `scripts/nl_decompress.py` (reverse de
   > `$80:F8D8`, validé bit-à-bit contre le buffer `$7F:64C0`).
3. Une fois le décompresseur fidèle, écris le **compresseur** (ou réinjecte en
   non-compressé si la place le permet) puis remets à jour la table de pointeurs.

---

## 6. Extraire / re-rendre les graphismes

```bash
# rendre un dump décompressé (binaire) en planche de tuiles
python3 scripts/snes_re_toolkit.py jeu.sfc --gfx-bin dump.bin,4,16 --out dump.png

# rendre une zone ROM brute (asset non compressé)
python3 scripts/snes_re_toolkit.py jeu.sfc --gfx 0x38000,0x1000,2,16 --out logo.png
```

Pour traduire un graphisme : repère la/les tuile(s) de texte sur la planche,
redessine-les (éditeur de tuiles : YY-CHR, Tilemolester, ou pixels à la main),
ré-encode au bon bpp, recompresse si nécessaire, réinjecte.

---

## 7. Récapitulatif des commandes

| Étape | Commande |
|---|---|
| Compressé ou pas ? | `--gfx OFF,LEN,BPP,W` |
| Trouver les tables d'assets | `--find-tables` |
| Repérer les blobs denses | `--entropy` |
| Décompresseurs candidats (statique) | `--find-decompressors` |
| Localiser les uploads VRAM | `--find-dma` |
| Désassembler une routine | `--disasm SNES,N` ou projet `--save-project` |
| Rendre un dump décompressé | `--gfx-bin PATH,BPP,W` |

Le **trace dynamique DMA→WRAM (3b)** reste la méthode reine pour les compressions
custom ; les heuristiques statiques ne servent qu'à **cibler** où regarder.
