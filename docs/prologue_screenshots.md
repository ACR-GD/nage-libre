# Prologue complet — 24 écrans (captures `Screenshots/Prologue/`)

> Source : captures Mesen sur `nage-libre-en-prologue-test.sfc` (écran 1 patché EN, reste JP).  
> Driver : `$87:D63B` → boucle ×5 `$87:D70C` → `$83:BA46` / `$80:F8D8` (tilemap `$7F:64C0`) + `$80:F4A7` (typewriter ROM).

---

## Structure narrative

| Acte | Écrans | Visuel | Contenu |
|------|--------|--------|---------|
| **Cosmos** | 1–2 | Étoiles / nuages | Ouverture + voix du « maître des nuages » |
| **Horodatages** | 3, 6, 9, 13 | Fond noir + boîte | Timestamps pleine largeur entre vignettes |
| **Perso 1** | 4–5 | Dojo, cheveux violets | Réveil matinal |
| **Perso 2** | 7–8 | École, cheveux blonds | Arrivée à l'heure |
| **Perso 3** | 10–12 | Campagne, couettes roses | Chanson + surprise |
| **Perso 4** | 14–24 | École, queue de cheval brune | Retard + gag brosse à dents + arrivée |
| **→ Suite attendue** | — | UI pierres / dates | **5× saisie anniversaire + pierre de naissance** |

---

## Écrans détaillés

### Écran 1 — Étoiles *(patché EN)*

| L1 | `In a distant world,` |
| L2 | `a voice echoes …` |
| JP original | 「遠くの世界で……声が響く……」 |
| WRAM | `$7F:65E2` (30 mots), signature `075A` @ `$7F:6602` |

---

### Écran 2 — Nuages (antagoniste)

| L1 | 「この世界を全て私の物に……」 |
| L2 | 「心に闇を持つ者を集めて……」 |
| ROM | `$87:89C5`, `$89DF` + `$8A51/61/71` via `$87:EA20` → `$80:F4A7` |

*(Variante légère vs doc précédente : **持つ** au lieu de **抱く**, **集めて** au lieu de **集え**.)*

---

### Écran 3 — Horodatage AM06:12

| Texte | `……　ＡＭ０６：１２　……` |
| Pipeline | Tilemap WRAM post-`$80:F8D8` (fond noir, pas de portrait) |
| Note | Ce n'est **pas** de l'ASCII — ce sont des tuiles alphanumériques pleine largeur + `：` |

---

### Écran 4 — Perso 1 (dojo, cheveux violets)

| L1 | `よーし！！　今日は一番乗りだ！！` |
| L2 | `気合い入れて行くぞぉ！！` |
| ROM | **Non trouvé** en banque `$87` (probablement WRAM décompressée ou banque `$84`) |

---

### Écran 5 — Perso 1 (suite)

| L1 | `……あれ……今何か……` |

---

### Écran 6 — Horodatage AM08:35

| Texte | `……　ＡＭ０８：３５　……` |

---

### Écran 7 — Perso 2 (blonde, campus)

| L1 | `さて、時間もちょうどですわね♥` |

---

### Écran 8 — Perso 2 (suite)

| L1 | `ふあ？　今ふわっとした感覚が` |
| L2 | `走りましたわね……何でしょう？` |

---

### Écran 9 — Horodatage AM10:28

| Texte | `……　ＡＭ１０：２８　……` |

---

### Écran 10 — Perso 3 (rose, campagne)

| L1 | `♪たーらららん、たーらららん♪` |
| L2 | `学校に♪　行ーこぉ♪` |

---

### Écran 11 — Perso 3 (chanson suite)

| L1 | `いーまから♪　行ーけば♪` |
| L2 | `お昼まーえには♪　つーくぞ♪` |

---

### Écran 12 — Perso 3 (surprise)

| L1 | `きゃん！！　なんか起こったよ今！！` |

---

### Écran 13 — Horodatage AM11:37

| Texte | `……　ＡＭ１１：３７　……` |

---

### Écrans 14–18 — Perso 4 (brune, retard)

**14**
| L1 | `やああああああああん！！` |
| L2 | `力いっぱい` |
| L3 | `遅刻してるぅぅぅぅ！！　　きゃん！！` |

**15**
| L1 | `おやくそくのように、` |
| L2 | `ハブラシとトーストなんて` |
| L3 | `くわえちゃったりして、` |

**16**
| L1 | `しかも、さっきまでガリガリと` |
| L2 | `かじってたのは、どうやら` |
| L3 | `ハブラシのほうだったみたい！！` |

**17**
| L1 | `この、あたしの、とぎすまされた` |
| L2 | `キバのような美しい歯が` |
| L3 | `ボロボロになっちゃうわ！！` |

**18**
| L1 | `……はあはあ。それにしても` |
| L2 | `しゃべりながら、走るってのは` |
| L3 | `何だかつかれちゃうわね。` |

---

### Écrans 19–24 — Perso 4 (arrivée école)

**19**
| L1 | `でもま、着いたからには、` |
| L2 | `アトは寝てりゃぁいいんだから` |
| L3 | `ラクと言えばラクなんだけどね♥` |

**20**
| L1 | `……ありり？　今なんかヘンな` |
| L2 | `感じがしたような気が…` |
| L3 | `…何だろ？` |

**21**
| L1 | `うーん……えーと……` |
| L2 | `……判んないからいいや！！` |

**22**
| L1 | `…なんて言ってるうちにどうやら` |
| L2 | `ギリギリで学校には、間にあった` |
| L3 | `みたい！！　イヤッホォ！！` |

**23**
| L1 | `ホントによかったぁ！！　今日は` |
| L2 | `４時間目で学校終わりだもんね♪` |
| L3 | `休みになるところだったわ♥` |

**24** *(dernier écran — bug signalé après celui-ci)*

| L1 | `さあて、着いたぞぉ！！` |
| L2 | `……でも、学校が、いつもより` |
| L3 | `静かだな…何だろ？` |

---

## Suite attendue (non atteinte)

Après l'écran 24, le jeu devrait enchaîner sur la **création de personnage** :

1. Saisie **mois / jour** pour chaque héroïne (`$87:8965` 月, `$87:8969` 日)
2. Prompt **「誕生日をおしえてね」** (`$87:896D` via `$87:D990` → `$80:F4A7`)
3. Confirmation **「これで誕生日はいいかな　」** (`$87:8981`)
4. Sélection **pierre de naissance** (table `$87:DABB` : améthyste, aquamarine, etc.)

Chaînes UI confirmées dans `docs/extracted_scripts.csv` entrées #43–44 de la table `$87:8697`.

---

## Bug post-écran 24

### Symptômes (rapportés)

- Personnage **disparaît**
- **Boîte de texte vide**
- **Musique continue**, **nuages défilent** (fond scène nuages / couche BG animée)
- Pas de transition vers l'UI anniversaire / pierres

### Interprétation technique

| Hypothèse | Détail |
|-----------|--------|
| **Machine à états bloquée** | Le moteur dialogue attend un texte suivant (`$80:F4A7` / phases `$83:8103`) dont le pointeur est vide ou `FFFF` |
| **Boucle `$87:D70C` non terminée** | Tant que le compteur ≠ 5 et carry clear, `$87:DCCB` (fin prologue → gameplay) n'est **pas** appelé |
| **Fond nuages persistant** | La couche BG animée de l'écran 2 reste active alors que le sprite portrait a été effacé — état incohérent |
| **Patch écran 1** | Le hook `$83:80FF` ne devrait toucher que la signature `075A`+`002A` ; peu probable sur l'écran 24, mais à valider sur **ROM originale** vs patchée |

### Pistes de debug Mesen

1. Break `$87:DCCB` — est-il atteint après l'écran 24 ?
2. Break `$83:8103` — valeur du compteur de phase `$06` et `$17D6` (index scène)
3. Break `$80:F4AB` — adresse source (`$09-$0B`) au moment du blocage : texte vide ?
4. Dump WRAM `$7F:64C0` au blocage vs après écran 24 normal (ROM JP)
5. Comparer **ROM originale** et **`nage-libre-en-prologue-test.sfc`** pour isoler le patch

### Flow CPU rappel

```
$87:D63B
  → $87:D955 (init UI anniversaire — sons + pointeurs)
  → boucle: $87:D70C × N  (N→5 via compteur @ $87:D6BC)
       → $83:BA46 → $83:80FF → $80:F8D8
       → phases $83:8103 (7 handlers)
  → $87:DCCB (transition fin prologue)
```

Les **24 écrans** tiennent dans les **5 itérations** `$87:D70C`, chaque itération comportant plusieurs avancées dialogue (phases + `$80:F4A7`).

---

## Corrections vs hypotheses antérieures

| Ancienne hypothèse | Réalité (captures) |
|--------------------|-------------------|
| Écran 3 = narration 西暦 / 地球 | **Infirmé** — c'est un **horodatage** `ＡＭ０６：１２` |
| `$87:896D` = texte prologue 西暦 | **Infirmé** — c'est **「誕生日をおしえてね」** (UI post-prologue) |
| 「よーし」 introuvable | **Écran 4** : `よーし！！　今日は一番乗りだ！！` |

---

*2026-06-07 — Captures : `Screenshots/Prologue/nage-libre-prologue-screen-{1..24}.jpg`*
