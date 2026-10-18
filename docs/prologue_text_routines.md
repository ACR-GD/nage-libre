# Nage Libre — Moteur de texte du prologue

Analyse statique (`scripts/disasm_text_routines.py`) + dumps mémoire
(`mesen_dumps/*_PC_838103_*`) croisés avec `Screenshots/Prologue/`.

> **Correction d'un modèle antérieur.** Il n'y a **pas** de « texte cuit dans une
> tilemap » d'un côté et « typewriter » de l'autre. En réalité il existe **un seul
> moteur de glyphes** (`$80:F433`, à base de sprites/OBJ, à chasse variable), alimenté
> par **deux pilotes** différents. La narration est un **interpréteur de bytecode**.

---

## 1. Vue d'ensemble

```
                       ┌─────────────────────────────────────────┐
   NARRATION           │  Interpréteur de script  $83:8103        │
   (écrans 1–24)  ───► │  lit des opcodes dans $7F:64C0 (le bloc  │
                       │  décompressé) ; 66 opcodes (0x01–0x42)   │
                       └───────────────┬─────────────────────────┘
                                       │ opcodes « texte »
                                       ▼
                       ┌─────────────────────────────────────────┐
   moteur typewriter   │  $80:F4CA / $80:F4A7  →  boucle qui lit  │
   (commun)            │  des IDs 16-bit à [$09], fin = $FFFF     │
                       └───────────────┬─────────────────────────┘
                                       │ 1 glyphe
                                       ▼
                       ┌─────────────────────────────────────────┐
   plotter de glyphe   │  $80:F433  → 1 sprite OBJ, chasse        │
   (commun)            │  variable (VWF) via $80:F390             │
                       └─────────────────────────────────────────┘
                                       ▲
   UI INTERACTIVE       ┌──────────────┴──────────────────────────┐
   (anniversaire,  ───► │  boucle  $87:D70C  (driver $87:D63B)     │
    pierre)             │  lit des chaînes en ROM (tables $87:xx)  │
                       └─────────────────────────────────────────┘
```

| Capture | Écran | Pilote |
|---|---|---|
| `screen-1` (étoiles, *« In a distant world… »*) | narration | script `$83:8103` |
| `screen-2` (nuages, 「この世界を…」) | narration | script `$83:8103` |
| `screen-3` (horodatage `AM06:12`) | narration | script `$83:8103` |
| `screen-4` (dojo, 「よーし!!…」) | narration | script `$83:8103` |
| saisie anniversaire / pierre (jamais atteinte) | UI | boucle `$87:D70C` |

---

## 2. Le plotter de glyphe `$80:F433` (commun)

Rend **un** ID de caractère 16-bit (dans A) en **sprite OBJ**, en chasse variable :

```
LDX $0240               ; index dans un buffer OBJ en anneau (pas 6, wrap à $00C0 = 32 glyphes)
JSR $F390               ; ID → n° de tuile ; CARRY = largeur (set=2 pleine chasse / clear=1 demi-chasse)
STA $0812,X             ; n° de tuile
... $0814,X = largeur   ;  ← VWF
... $0816,X = attributs/position (palette, X/Y dérivés de $1141)
; avance le curseur de la largeur ; retour à la ligne si dépassement de $1144
```

Curseur / marges (mêmes registres pour les deux pilotes) :

| Reg | Rôle |
|---|---|
| `$1141` (octet bas) | colonne X courante |
| `$1142` (octet haut de `$1141`) | rangée Y courante |
| `$1143` | colonne de retour (marge gauche) |
| `$1144` | limite basse/droite (souvent `$1E`/`$1F`) |
| `$0240` | index du buffer OBJ (anneau de 32 glyphes) |

## 3. La boucle typewriter `$80:F4A7` / `$80:F4CA`

Deux entrées quasi identiques (`F4A7 → F4AB`, `F4CA → F4CE`). Le cœur :

```
$80:F4B3  LDA [$09]            ; ID 16-bit au pointeur $09/$0A/$0B
          CMP #$FFFF
          BEQ fin              ; $FFFF = terminateur
          JSR $F433            ; trace le glyphe
          INC $09 / INC $09    ; +2 octets
          BRA $F4B3
```

**Format d'une chaîne de texte** = suite d'**IDs 16-bit**, terminée par **`$FFFF`**.
`$03FE` = espace (chasse pleine). Les IDs correspondent à `docs/kanji_font_index.csv`.

---

## 4. Pilote NARRATION — interpréteur de script `$83:8103`

### Mise en place (`$83:80E0`)

```
$83:80F0  $06 = $C0          ; pointeur de script $06/$07/$08 = $7F:64C0
$83:80F4  $07 = $64
$83:80F8  $08 = $7F
$83:80FF  JSL $80F8D8        ; décompresse le SCRIPT de la scène dans $7F:64C0
$83:8103  ── boucle d'interprétation ──
```

Le bloc décompressé en `$7F:64C0` **n'est pas une tilemap** : c'est un **programme
d'opcodes**. Confirmé par dump (`zp_direct.txt` : `$06=64C0`, `$07=7F64`, `$08=…7F`).

### Boucle d'interprétation

```
$83:8103  LDA [$06]          ; lit un opcode 16-bit
          CMP #$0001 .. #$0042 → JSR handler ; BRL $8103   (66 opcodes)
          CMP #$FFFF → fin du script ($83:83E5 : JSL $8088BB ; RTS)
          (chaque handler avance $06 de son nombre d'opérandes via INC $06)
$83:83E2  BRL $8103          ; opcode suivant
```

### Opérande des opcodes « texte »

Les handlers de texte lisent un mot **offset**, calculent `$09 = $64C0 + offset`
(`bank $0B = $7F`) puis appellent `$80:F4CA`. Le texte est donc une **chaîne d'IDs
stockée plus loin dans le même bloc décompressé** — c'est exactement la zone qu'on
patche (`$7F:65E2`, `$7F:66E2`…).

```
$83:83EE (opcode 1)   curseur col=8, marge 8..1E
          LDA [$06] (offset) ; +$64C0 → $09 ; $0B=$7F
          JSL $80F4CA        ; ← rend la ligne de texte
          (avance la rangée, INC $06 ×2)
$83:8444 (opcode 0x0B) idem mais col=1, marge 1..1F
```

### Table complète des 66 opcodes (`python3 scripts/disasm_text_routines.py opcodes`)

| Catégorie | Opcodes | Rôle |
|---|---|---|
| **Texte** (F4CA/F4A7 + `+64C0`) | `01 0B 10 11 12 13` | rendre une ligne (offset → chaîne d'IDs dans le bloc) |
| **Texte** (F4A7) | `02 03 04 05 06 07 0C 0D 1C 1D 1E 1F 20 21 22 3C` | rendre / positionner du texte (variantes de boîte, vitesse) |
| **Texte + ptr** | `07 0D 3A 3B` | texte avec pointeur calculé |
| **Pointeur** (`+64C0`) | `08 09 0A 23 24 25 26 27 28 29 2A 2B` | charger une adresse/offset dans le bloc (sprite, palette, table) |
| **Décompression** (FA63) | `17 19 1A 1B 3D 3E 3F 40 41 42` | charger un nouveau décor / banc de tuiles (change d'écran) |
| **Contrôle** | `0E 0F 14 15 16 18 2C–3B (reste)` | timing, fades, scroll, drapeaux, synchro |

> Le tableau ci-dessus est généré automatiquement ; il classe par signature
> d'appel (`JSL $80F4CA`, `JSL $80F4A7`, `ADC #$64C0`, `JSL $80FA63`). La colonne
> « Contrôle » regroupe les handlers sans signature texte/decomp (animation, attente,
> palette, défilement des nuages, etc.).

### Taille des opcodes (décompilation)

La taille (octets consommés sur `$06`) de chaque opcode est dérivée en comptant les
`INC $06` du handler (en suivant les `JSR` internes). **Validée** contre les deltas de
`$06` observés dans les dumps successifs (`mesen_dumps/*_PC_838103_*`) :

| opcode | taille | dyn. observé |
|---|---|---|
| `20` | 2 o | 2 ✓ |
| `23` | 4 o | 4 ✓ |
| `29` | 4 o (délègue à `23` via `JSR $958C`) | 4 ✓ |
| `2B` | 4 o | 4 ✓ |
| `2C` | 2 o | 2 ✓ |

### Sémantique des opcodes (confirmée par décompilation du prologue)

Le **bloc `$7F:64C0` contient tout le script de narration** (les 24 écrans), pas un
écran à la fois. Programme en `+0000…+0120`, puis **données de chaînes** à partir de
`+0122`. Opcodes réellement utilisés :

| opcode | taille | rôle observé |
|---|---|---|
| `2B` | 4 o | **ligne de texte plein écran** (étoiles/nuages/horodatage) ; opérande = offset → chaîne, rendu via `$80:F5AC` |
| `26` | 4 o | **ligne de dialogue** (perso) ; opérande = offset → chaîne |
| `29` | 4 o | positionnement / setup de ligne (param, pas un offset) |
| `24` / `25` | 6 o | charge / libère un portrait de perso (2 params) |
| `2C` | 2 o | pause / attente d'appui en fin de ligne |
| `20` | 2 o | invite « continuer » (texte ROM fixe `$83:86B3`, ex. flèche ▼) |
| `27` / `3A` | 2 o | contrôle (synchro / effet) |
| `23` | 4 o | pointeur de table de données (même addressing `$09=+64C0`, **pas** du texte) |
| `FFFF` | — | fin du programme (les données de chaînes suivent) |

> Les opcodes « ligne de texte » se reconnaissent au motif `ADC #$64C0 / STA $09`
> (`69 C0 64 85 09`) : l'opérande est un **offset** dans le bloc, vers une chaîne d'IDs
> terminée `$FFFF`. Le listing complet décodé est dans **`docs/prologue_scene_script.md`**.

### Déroulé d'un écran de narration

1. Un opcode **décompression** (`17/19/1A/1B/3D…`) charge le décor (étoiles, nuages, dojo…).
2. Un ou plusieurs opcodes **texte** (`01/0B/…`) rendent les lignes de la boîte, chacune
   pointant via offset vers une chaîne d'IDs dans le bloc `$7F:64C0`.
3. Des opcodes **contrôle** gèrent l'attente d'appui (`$0214`), les fades, le défilement.
4. À la fin de la scène : `$FFFF` → retour ; l'écran suivant relance `$80:F8D8` avec un
   nouveau script.

### Validation par dump (`mesen_dumps/..._PC_838103_001`)

Chaînes lues à `$7F:64C0 + offset` (terminées `$FFFF`, `$03FE` = espace) :

```
+0142 : 16E 434 436 438 43A 43C 46C 46E 470 3FE…   ← fragment ASCII (0x4xx) = texte anglais patché
+0162 : 2E6 032 068 33A 33C 0AE 304 058 330 …      ← chaîne d'IDs japonais (à transcrire)
```

Les IDs `0x4xx` sont nos glyphes ASCII (patch écran 1) ; les IDs `0x0xx–0x3xx` sont
les kana/kanji à mapper dans `docs/kanji_font_index.csv`.

---

## 5. Pilote UI — boucle `$87:D70C` (création de personnage)

Lancé par le driver `$87:D63B` après la narration (`$87:D6C0  JSR $D70C`). Pour chaque
acte : `$87:D9D7` décompresse le décor, charge les params de scène (`$17D6`→`$17D4/5`),
puis rend du texte issu de **tables ROM** via `$80:F4A7` :

| Routine | `$1141` | Source de la chaîne |
|---|---|---|
| `$87:DA8C` | `$0E11` | table `$87:DABB` (pas 4 octets) → chaînes de 8 IDs (`$87:89F1`, `8A01`, …) |
| `$87:DA3B` | `$0C0F` | `$87:8965` (月), `$87:8969` (日), conversion nombre via `$80:F6E8` |
| `$87:D990` | `$0405` | `$87:896D` = 「誕生日をおしえてね」 (9 IDs) |

Chaînes ROM confirmées : `$87:896D = 02DE 01DA 02C8 00AE 0020 003A 001C 0058 0066`
(= 9 glyphes 誕生日をおしえてね).

---

## 6. Le bug de fin de prologue — cause racine

**Graphe d'appels du prologue** (séquenceur maître en banque `$80`) :

```
$80:9626/963A  LDA #scene ; JSL $83:80D7   ← narration (interpréteur $83:8103, 24 lignes)
        …
$80:9393       JSL $87:D63B                ← driver création perso (anniversaire)
$87:D63B  …    JSR $D70C  (×5 héroïnes)    ← saisie anniversaire (boucle)
$87:D6D4       JSR $DCCB                    ← transition vers le jeu (après 5 saisies)
```

« `$87:DCCB` ne hit jamais » ⇒ le freeze survient **avant** la fin de la boucle birthday,
typiquement pendant/juste après la narration.

### Cause racine identifiée (ancien patch écran 1)

L'ancien `patch_nl_prologue_en.py` écrivait la chaîne anglaise à l'offset **`+0122`**
(`$7F:65E2`) alors que l'opcode `0x2B` lit la chaîne à **`+0124`** (`$7F:65E4`), et il
écrivait **30 mots sans terminateur `$FFFF` explicite**. Or la chaîne japonaise d'origine
finit par `$FFFF` au mot 29, soit exactement **`+015E`** — que le 30ᵉ mot écrit **écrase
avec un espace**. Résultat : le moteur de texte (`$80:F5AC`/`F4CE`) **ne trouve plus le
terminateur** et déborde sur la chaîne suivante (`+0162` = écran 2…), d'où la boîte qui
bave puis se fige. Le « clear `$7F:66E2` » était un pansement sur ce débordement.

### Correctif

`build_prologue_translation.py` (§8) écrit chaque ligne **au bon offset** (issu du
décompilateur) et **ajoute un terminateur `$FFFF`** juste après l'anglais → arrêt propre,
aucun débordement. La nouvelle `nl-prologue-en.sfc` devrait donc **ne plus figer** sur ce
chemin. À tester en premier.

> Si un freeze subsiste, le tracer **`scripts/mesen_transition_trace.lua`** logue chaque
> étape du hand-off + échantillonne le PC : le dernier `REACHED` atteint et le PC qui se
> répète pendant le gel localisent la cause exacte (narration `$83:8xxx`, séquenceur
> `$80:9xxx`, ou driver `$87:Dxxx`).

---

## 7. Adresses clés

| Adresse | Rôle |
|---|---|
| `$80:F433` | plotter d'un glyphe (sprite OBJ, VWF) — **commun** |
| `$80:F390` | ID → tuile + largeur (carry) |
| `$80:F4A7→F4AB` / `$80:F4CA→F4CE` | boucle typewriter (IDs à `[$09]`, fin `$FFFF`) |
| `$80:F8D8→F8DC` | décompresseur du script de scène → `$7F:64C0` |
| `$80:FA63` | décompresseur de tuiles/décor (opcodes décor) |
| `$83:80E0` | init du pointeur de script `$06/$07/$08 = $7F:64C0` |
| `$83:8103` | **interpréteur de script** (66 opcodes, fin `$FFFF`) |
| `$83:83EE` / `$83:8444` | handlers « ligne de texte » (opcodes 1 / 0x0B) |
| `$7F:64C0` | base du bloc décompressé = **script + chaînes de la scène** |
| `$1141`–`$1144`, `$0240` | curseur / marges / index OBJ |
| `$87:D63B` | driver d'init du prologue |
| `$87:D70C` | boucle UI (création perso / anniversaire) |
| `$87:DA8C` / `$87:DA3B` / `$87:D990` | rendu texte UI (tables `$87:DABB`, `$87:896x`) |
| `$87:DABB` | table de pointeurs de chaînes UI |
| `$0214` | drapeau d'attente d'appui |

---

## 8. Workflow de traduction (réinjection pilotée par table)

Plutôt que de patcher des positions tilemap en dur, on réinjecte chaque ligne à son
**offset** dans le bloc décompressé. Deux fichiers :

- **`docs/prologue_translation.csv`** — table de travail (générée). Colonnes :
  `offset_hex, n_ids, slot_words, jp_decoded, en`. On remplit la colonne **`en`**
  ligne par ligne ; `slot_words` = nombre max de paires (≈ 2 caractères chacune).
- **`build_prologue_translation.py`** — lit le CSV, encode l'anglais (paires VWF +
  glyphes via `ScatterAllocator`), construit une **table ROM** `{offset, count, ids…}`
  et un **hook** en `$83:F8E3` qui, après `JSL $80F8D8`, recopie chaque chaîne anglaise
  vers `$7F:64C0 + offset`, terminée par `$FFFF` (aucun résidu japonais ne s'affiche).

```bash
python3 scripts/decompile_prologue_script.py csv   # (re)génère la table de travail
# … remplir la colonne `en` du CSV …
python3 build_prologue_translation.py              # produit nl-prologue-en.sfc
```

Mécanisme du hook (généré) :

```
$83:F8E3  JSL $80F8D8            ; décompression d'origine
          (sauvegarde registres + $0C)
          LDX #table             ; parcourt la table en banque $83
boucle :  LDA.l table,X          ; offset ; $FFFF → fin
          ADC #$64C0 → $09/$0A/$0B = $7F:64C0+offset
          count → $0C (octets) ; copie count mots via STA [$09],Y
          → ligne suivante
          (restaure) RTL → $8103 (interpréteur)
```

**Limites à respecter**
- `en` encodé ≤ `slot_words` (sinon le builder s'arrête avec une erreur explicite ;
  la chaîne suivante serait écrasée).
- Budget police : ~160 paires VWF libres au total (`ScatterAllocator`). Réutiliser les
  digrammes (le cache `p2id` dédoublonne automatiquement).
- Espace ROM : hook + table ≤ ~1.8 Ko en banque `$83` (`$F8E3`–`$FFE0`). Suffisant pour
  les 24 lignes.
- **Bug de fin de prologue** (transition narration → UI) : **non couvert** par cette
  voie ; voir §6. Ce builder ne traite que le contenu des chaînes de narration.

> `build_prologue_translation.py` **généralise** l'ancien `patch_nl_prologue_en.py`
> (écran 1 seul, positions en dur). Utiliser l'un *ou* l'autre, pas les deux.

## 9. Reproduire l'analyse

```bash
python3 scripts/disasm_text_routines.py opcodes        # table des 66 opcodes classés
python3 scripts/disasm_text_routines.py 83 8103 40      # début de l'interpréteur
python3 scripts/disasm_text_routines.py 80 F433 55      # plotter de glyphe
python3 scripts/disasm_text_routines.py 87 D70C 80      # boucle UI
python3 scripts/decompile_prologue_script.py            # décompile le script $7F:64C0 d'un dump
```

Sortie de référence : **`docs/prologue_scene_script.md`** (les 24 lignes décodées).
Table de traduction : **`docs/prologue_translation.csv`**.
