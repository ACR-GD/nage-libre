# Texte de combat & menus — banque `$87`

> Découvert en scannant la ROM pour des chaînes d'IDs 16-bit terminées par `FFFF`,
> **lues visuellement** en rendant les glyphes (`scripts/render_text.py`), car le
> mapping unicode auto est incomplet. Captures dans `docs/menu_strings/page*.png`.

## Localisation

Tout le texte d'**interface, combat et système** est stocké **en clair** (pas
compressé) dans la banque `$87`, en IDs de police 16-bit little-endian terminés
par `FFFF` — **le même format que le bloc narration**. Contrairement à la
narration du prologue (compressée → WRAM `$7F:64C0`), ces chaînes sont lues
directement depuis la ROM par le moteur typewriter `$80:F4A7`.

| Zone | Plage fichier | SNES | Contenu |
|------|---------------|------|---------|
| Noms | `0x038077`–`0x0385xx` | `$87:8077`+ | ~230 noms (nom de famille + prénom) — création de perso |
| Clubs | dans le bloc | — | Basket, Tennis, Kendo, Karaté, Kyūdō, Lacrosse, gym, occulte, sciences, danse, ikebana, musique, théâtre, manga, couture… + `一般生徒` (élève lambda), `ボス` (Boss) = **types d'ennemis** |
| **Combat** | `0x0386D9`–`0x03886B` | `$87:86D9`+ | Messages de combat (attaque, dégâts, stats…) |
| **Menus/système** | `0x038879`–`0x0389EB` | `$87:8879`+ | Sauvegarde / chargement / boutique / anniversaire |
| Pierres | `0x0389F1`–`0x038AA1` | `$87:89F1`+ | 12 pierres de naissance |
| **Hub** | `0x038AB1`–`0x038B31` | `$87:8AB1`+ | Menu principal (Save, Shop…) + 6 joyaux *Libération* |

> Table complète offsets + JP + EN proposé : **`docs/combat_menu_translation.csv`** (67 chaînes).

## Messages de combat (`$87:86D9`+)

| SNES | JP | EN proposé |
|------|----|-----------|
| `$87:86DF` | `[nom]の攻撃！！` | `[name]'s attack!!` |
| `$87:86ED` | `[n]のダメージ！！` | `[n] damage!!` |
| `$87:86FB` | `回復した` | `recovered!` |
| `$87:8705` | `防御がアップ！！` | `Defense up!!` |
| `$87:8797` | `ダメージをあたえられない！！` | `Cannot deal damage!!` |
| `$87:87EB` | `[nom]を倒した！！` | `Defeated [name]!!` |
| `$87:87F7` | `[n]ゴールド手に入れた！！` | `Got [n] Gold!!` |
| `$87:8897` | `[nom]の超必殺技だ！！` | `[name]'s ultimate move!!` |
| `$87:8749` | `逃げろぉ！！` | `Run away!!` |
| `$87:87B3` | `逃げるな　待てぇ！！` | `Don't run, wait!!` |
| `$87:8755` | `…おいつかれてしまった！！` | `...got caught!!` |
| `$87:87C7` | `…おいついた` | `...caught up` |
| `$87:876F` | `…なんとか、逃げられた…` | `...barely got away...` |
| `$87:87D5` | `…逃げられてしまった` | `...they got away` |
| `$87:8731` | `ただいま着がえ中です…` | `Changing outfit now...` |
| `$87:8715` | `入れかえるカードを選んでね` | `Pick a card to swap` |

### Montée de stats
`[stat] が [n] に上がった！！` / `… 選べるようになった！！` (assemblé à l'exécution).

| SNES | JP | EN | SNES | JP | EN |
|------|----|----|------|----|----|
| `$87:8819` | `体力` | Stamina | `$87:8833` | `精神力` | Spirit |
| `$87:8821` | `腕力` | Power | `$87:883D` | `素早さ` | Speed |
| `$87:8829` | `防御力` | Defense | `$87:8847` | `レベル` | Level |

## Menus système (`$87:8879`+)

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

### Boutique
| SNES | JP | EN |
|------|----|----|
| `$87:88DB` | `カードを買います` | `Buy a card` |
| `$87:8913` | `カードをうります` | `Sell a card` |
| `$87:892F` | `お金がたりません！！` | `Not enough money!!` |
| `$87:8949` | `これ以上買えません` | `Can't buy more` |

## Menu principal / Hub (`$87:8AB1`+)

| SNES | JP | EN |
|------|----|----|
| `$87:8AB1` | `どうしますか？` | `What will you do?` |
| `$87:8AC1` | `買い物` | `Shop` |
| `$87:8AC9` | `部活選択` | `Clubs` |
| `$87:8AD3` | `セーブ` | `Save` |
| `$87:8ADB` | `スタート` | `Start` |
| `$87:8AE5` | `EX` | `EX` |

Joyaux *Libération* (`$87:8AEB`+) : `「リ」「ベ」「ラ」「ジ」「オ」「ン」の宝玉` → **リベラジオン** = *Libération*.

## Pierres de naissance (`$87:89F1`+)

Grenat, Améthyste, Aigue-marine, Diamant, Émeraude, Pierre de Lune, Rubis,
Agate, Saphir, Opale, Topaze, Lapis-lazuli (`ガーネット`…`ラピスラズリ`).

## Builder d'injection

`build_combat_menu_translation.py` réécrit ces chaînes **sur place** (encodage
paires VWF, comme le prologue) — pas de hook nécessaire car le texte est lu
directement depuis la ROM.

```bash
python3 build_combat_menu_translation.py            # menu hub seul → nl-menu-en.sfc
python3 build_combat_menu_translation.py --cat hub,menu,combat
python3 build_combat_menu_translation.py --all      # toutes les catégories
```

- Contrainte : `mots_anglais ≤ slot_words` (le `FFFF` tient dans le slot d'origine),
  soit **≤ `slot_words × 2` lettres**. Le builder refuse et liste les dépassements.
- L'allocateur de police exclut **tous** les IDs référencés dans le bloc `$87`
  (`0x038077`–`0x038C01`) : aucun glyphe de nom/club/pierre n'est écrasé (vérifié).
- **Pool de police partagé** : ce builder et `build_prologue_translation.py`
  allouent depuis le même pool d'IDs libres. Pour une ROM unique, utiliser le
  **builder unifié** `build_full_translation.py` qui partage un seul allocateur :

  ```bash
  python3 build_full_translation.py        # prologue + combat + menus → nl-full-en.sfc
  ```

  Sortie `nl-full-en.sfc` : prologue (hook $83 → WRAM) **+** combat/menus (sur
  place $87), **295 paires** uniques sur 651 dispo, aucune collision (un seul
  `ScatterAllocator`). Les sorties séparées `nl-menu-en.sfc` /
  `nl-prologue-en.sfc` restent disponibles pour tester chaque partie isolément.

## Réserve de police (anti-collision) — IMPORTANT

La police est **dense** : presque toutes les tuiles sont des glyphes réels, il n'y a
quasi aucune tuile vide. Les paires anglaises réutilisent donc des **kanji inutilisés**.
Pour ne pas écraser un glyphe affiché, l'allocateur exclut :

1. le bloc texte `$87` (`0x038077`–`0x038C01`) ;
2. les **IDs du prologue** (script compressé → WRAM `$7F:64C0`), figés dans
   `docs/reserved_font_ids.txt` (généré depuis un dump WRAM du prologue) ;
3. toutes les **tables de texte non compressées** pointées par du code
   (`dump_all_scripts.find_all_script_pointers`) ;
4. le **voisin impair** `N-1`/`N+1` de chaque paire (une tuile 16×16 en `N`
   chevauche les demi-glyphes de `N±1`).

> **Régression corrigée** (horodatages `ＡＭ０６：１２` affichés `keup : adsc`) :
> les glyphes des horodatages, utilisés par le prologue compressé, étaient
> réalloués pour l'anglais. La réserve ci-dessus les protège. Après correctif :
> 295 paires / 394 IDs libres, **0 collision**.

> ⚠ Si tu traduis de nouvelles scènes **compressées** (combats, dialogues), pense à
> regénérer `reserved_font_ids.txt` à partir d'un dump WRAM de la scène concernée,
> sinon ses glyphes risquent d'être écrasés.

## Menu de commande en combat (待機/攻撃/アイテム/交換/ポケベル/アニメ/セーブ)

**Non encore traduit.** Analyse des dumps de combat
(`nl-full-en-battle-menu-SnesWorkRam.dmp` + `…VideoRam.dmp`) :

### Ce que les dumps prouvent

1. **Pas dans la WRAM en IDs 16-bit.** La séquence `セーブ` (`00E4 0092 011A`) et
   `アイ` (`00B2 00B6`) sont **introuvables** dans la WRAM de combat. Le scan de
   toutes les chaînes terminées `FFFF` ne donne que le buffer dialogue
   `$7F:64C0` (région `0x16xxx`) + quelques fragments — **aucun menu**.
2. **Le menu de combat utilise une POLICE DÉDIÉE 8×8**, distincte du système
   d'IDs 16-bit. En rendant la VRAM (`docs/menu_strings/battle_vram_2bpp.png` et
   `…_band.png`) on voit nettement, chargés ensemble :
   - **l'alphabet latin complet** `ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789` ;
   - les **noms** `SYOKO MEI YUI MIKI RYOKO` ;
   - les libellés `TIME SPEED`, `command`, `item` ;
   - une rangée de **kanji/katakana** = les commandes du menu (待機/攻撃/…).
3. Cette police n'apparaît pas **octet-pour-octet** dans la ROM → elle est
   stockée dans un autre format (1bpp étendu, ou compressée) puis DMA'd en VRAM.

### Conséquence pour la traduction — bonne nouvelle

Comme **l'alphabet latin est déjà présent** dans la police de combat, traduire
le menu **ne demandera AUCune édition de police** : il suffira de réécrire la
**chaîne source du menu** (séquence d'indices/codes de tuiles) avec des codes
latins (`S`,`A`,`V`,`E`…). Système totalement séparé du builder `$87` actuel →
pas de risque de collision avec le travail existant.

### Mécanisme complet (traces VRAM/WRAM + désassemblage)

Le menu est dessiné par le **moteur de texte commun** banque `$80` :

- Entrée `$80:F8DC` (via `$80:F8D8`). Lit un flux **compressé** (commandes
  nibble) via le pointeur 24-bit `[$09]/$0A/$0B` (le **même** pointeur texte que
  le prologue). Boucle : `LDA [$09]` → `JSR ($F909,X)` (dispatch nibble).
- Table de saut `$80:F909`, commandes `0x0`–`0xF` :
  - `0x0`–`0x7` → `$F92B` : **décode les pixels du glyphe** (nibbles via `$FA42`)
    dans le buffer de police `[$06]` (= `$7E:2000+`, tuile N à `+N*16`), **alloue
    dynamiquement** l'indice de tuile (compteur `$02DD`), et stocke les 4 indices
    du glyphe 16×16 dans `$02DF`–`$02E2`.
  - `0xC`–`0xF` (`$F9F1`/`$F9F9`/`$FA01`/`$FA09`) : **écrivent les 4 entrées de
    tilemap** (via `$FA11`) dans le shadow BG3 `$7E:4000+`.
- Le shadow police `$7E:2000+` et le shadow tilemap `$7E:4000+` sont ensuite
  **DMA'd** en VRAM (police char base `0xA000`, tilemap BG3 mot `0x7C00`).
- Le menu est dessiné **une seule fois** à l'ouverture (≈frame 95/96).

PC observés (trace) : police `$80:F948`, tilemap `$80:F9C7`/`$80:F9D2`.

### Layout exact du menu (depuis le shadow tilemap `$7E:4000`)

Fenêtre : bordure tx21 (`$68`) / tx29 (`$69`), **inner = tx22–28 (7 cellules)**.
Chaque commande = 2 lignes de tilemap (haut/bas, glyphes 16×16). Palette `$20`
(normal) / `$24` (ligne sélectionnée).

| Lignes (ty) | JP | tuiles haut | EN proposé |
|-------------|----|-------------|-----------|
| 5–6   | 待機     | `90–94`/`A0–A4` | WAIT |
| 7–8   | 攻撃     | `B5–B9`/`C5–C9` | ATTACK |
| 9–10  | アイテム | `95–99`/`A5–A9` | ITEM |
| 11–12 | 交換     | `9A–9E`/`AA–AE` | SWAP |
| 13–14 | ポケベル | `B0–B4`/`C0–C4` | PAGER |
| 15–16 | アニメ   | `D0–D4`/`E0–E4` | ANIME |
| 17–18 | セーブ   | `BA–BE`/`CA–CE` | SAVE |

### Solution retenue : réécriture tilemap (AUCUNE édition de police)

La police de combat contient **déjà l'alphabet latin** chargé en VRAM :
`0x40`–`0x5A` = `A`–`Z`, `0x5B`–`0x64` = `0`–`9` (vérifié :
`docs/menu_strings/combatfont_full.png`). Lettre `c` → tuile `0x40 + (c-'A')`.

→ **Implémenté** (`build_combat_command_menu.py`, intégré à
`build_full_translation.py`) : on détourne l'enveloppe `$80:F8D8`
(`JSR $F8DC ; RTL`) en `JML $80:FA80` (zone libre, 878 o). Le hook exécute le
rendu original, puis — si la signature du menu est présente dans le buffer de
police (`$7E:2904`==`$3718` **et** `$7E:2B56`==`$7E01`) — recopie par **MVN
$7E,$7E** les tuiles latines (lettres déjà chargées en `$40`–`$5A`) par-dessus
les tuiles de glyphe des 7 commandes (lettres dans la tuile du **haut**, bas
laissé vide). La tilemap référence ces tuiles → menu anglais quelles que soient
position/animation/sélection. **Aucune édition de police, aucune recompression.**

**Limite** : 5 tuiles (8px) par commande → 5 lettres max. `攻撃` rendu **FIGHT**
(ATTACK = 6 ne tient pas). Libellés : WAIT / FIGHT / ITEM / SWAP / PAGER / ANIME
/ SAVE.

> Signature à 2 points + lettres latines déjà présentes → le hook ne se
> déclenche que sur le menu de combat. À surveiller au test : qu'aucun autre
> écran de texte ne soit affecté.

## Notes pour la traduction

- **Format identique au prologue** : IDs 16-bit + `FFFF`. Réinjection sur place
  (encodage paires VWF, ≤ `slot_words×2` lettres latines).
- **Chaînes assemblées à l'exécution** : `[nom]の攻撃` , `[stat]が[n]に上がった`.
  L'ordre japonais (particule `の` / `が`) ne correspond pas à l'anglais → prévoir
  un léger ajustement du code d'assemblage ou des formulations qui marchent dans
  les deux ordres.
- **Espace** : chaque chaîne a un `slot_words` fixe (voir CSV). Les noms/clubs
  partagent des sous-chaînes — à traiter à part.
