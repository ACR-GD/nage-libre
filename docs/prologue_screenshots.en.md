# Full prologue: 24 screens (captures in `Screenshots/Prologue/`)

*English version of [`prologue_screenshots.md`](prologue_screenshots.md). Research notes from June 2026: the Japanese lines below are what the screens showed before translation; the end-of-prologue bug described here has since been fixed.*

> Source: Mesen captures of `nage-libre-en-prologue-test.sfc` (screen 1 patched to EN, the rest still JP).
> Driver: `$87:D63B` → loop ×5 `$87:D70C` → `$83:BA46` / `$80:F8D8` (tilemap `$7F:64C0`) + `$80:F4A7` (ROM typewriter).

---

## Narrative structure

| Act | Screens | Visual | Contents |
|-----|---------|--------|----------|
| **Cosmos** | 1–2 | Stars / clouds | Opening + voice of the "master of the clouds" |
| **Timestamps** | 3, 6, 9, 13 | Black background + box | Full-width timestamps between vignettes |
| **Character 1** | 4–5 | Dojo, purple hair | Early morning |
| **Character 2** | 7–8 | School, blonde hair | Arrives on time |
| **Character 3** | 10–12 | Countryside, pink pigtails | Song + surprise |
| **Character 4** | 14–24 | School, brown ponytail | Late + toothbrush gag + arrival |
| **→ Expected next** | — | Birthstone / date UI | **5× birthday + birthstone entry** |

---

## Screens in detail

### Screen 1: stars *(patched to EN)*

| L1 | `In a distant world,` |
| L2 | `a voice echoes …` |
| Original JP | 「遠くの世界で……声が響く……」 |
| WRAM | `$7F:65E2` (30 words), signature `075A` @ `$7F:6602` |

---

### Screen 2: clouds (antagonist)

| L1 | 「この世界を全て私の物に……」 ("This whole world shall be mine…") |
| L2 | 「心に闇を持つ者を集めて……」 ("Gather those with darkness in their hearts…") |
| ROM | `$87:89C5`, `$89DF` + `$8A51/61/71` via `$87:EA20` → `$80:F4A7` |

*(Slight variation from the earlier doc: **持つ** instead of **抱く**, **集めて** instead of **集え**.)*

---

### Screen 3: timestamp AM06:12

| Text | `……　ＡＭ０６：１２　……` |
| Pipeline | WRAM tilemap after `$80:F8D8` (black background, no portrait) |
| Note | This is **not** ASCII: these are full-width alphanumeric tiles + `：` |

---

### Screen 4: character 1 (dojo, purple hair)

| L1 | `よーし！！　今日は一番乗りだ！！` |
| L2 | `気合い入れて行くぞぉ！！` |
| ROM | **Not found** in bank `$87` (probably decompressed WRAM or bank `$84`) |

---

### Screen 5: character 1 (continued)

| L1 | `……あれ……今何か……` |

---

### Screen 6: timestamp AM08:35

| Text | `……　ＡＭ０８：３５　……` |

---

### Screen 7: character 2 (blonde, campus)

| L1 | `さて、時間もちょうどですわね♥` |

---

### Screen 8: character 2 (continued)

| L1 | `ふあ？　今ふわっとした感覚が` |
| L2 | `走りましたわね……何でしょう？` |

---

### Screen 9: timestamp AM10:28

| Text | `……　ＡＭ１０：２８　……` |

---

### Screen 10: character 3 (pink, countryside)

| L1 | `♪たーらららん、たーらららん♪` |
| L2 | `学校に♪　行ーこぉ♪` |

---

### Screen 11: character 3 (song continued)

| L1 | `いーまから♪　行ーけば♪` |
| L2 | `お昼まーえには♪　つーくぞ♪` |

---

### Screen 12: character 3 (surprise)

| L1 | `きゃん！！　なんか起こったよ今！！` |

---

### Screen 13: timestamp AM11:37

| Text | `……　ＡＭ１１：３７　……` |

---

### Screens 14–18: character 4 (brown hair, late)

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

### Screens 19–24: character 4 (arriving at school)

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

**24** *(last screen; the bug was reported right after it)*

| L1 | `さあて、着いたぞぉ！！` |
| L2 | `……でも、学校が、いつもより` |
| L3 | `静かだな…何だろ？` |

---

## Expected next (not reached at the time)

After screen 24 the game should move on to **character creation**:

1. **Month / day** entry for each heroine (`$87:8965` 月, `$87:8969` 日)
2. The prompt **「誕生日をおしえてね」** (`$87:896D` via `$87:D990` → `$80:F4A7`)
3. The confirmation **「これで誕生日はいいかな　」** (`$87:8981`)
4. **Birthstone** selection (table `$87:DABB`: amethyst, aquamarine, etc.)

UI strings confirmed in `docs/extracted_scripts.csv`, entries #43–44 of table `$87:8697`.

---

## Bug after screen 24

### Reported symptoms

- The character **disappears**
- **Empty text box**
- **Music keeps playing**, **clouds keep scrolling** (cloud scene background / animated BG layer)
- No transition to the birthday / birthstone UI

### Technical interpretation

| Hypothesis | Detail |
|------------|--------|
| **Stuck state machine** | The dialogue engine waits for a next text (`$80:F4A7` / phases `$83:8103`) whose pointer is empty or `FFFF` |
| **`$87:D70C` loop not finished** | As long as the counter ≠ 5 and carry is clear, `$87:DCCB` (end of prologue → gameplay) is **not** called |
| **Clouds background persists** | The animated BG layer from screen 2 stays active while the portrait sprite has been cleared, an inconsistent state |
| **Screen 1 patch** | The `$83:80FF` hook should only touch the `075A`+`002A` signature; unlikely on screen 24, but to check on the **original ROM** vs the patched one |

### Mesen debugging leads

1. Break on `$87:DCCB`: is it reached after screen 24?
2. Break on `$83:8103`: value of the phase counter `$06` and of `$17D6` (scene index)
3. Break on `$80:F4AB`: source address (`$09-$0B`) when it freezes: empty text?
4. Dump WRAM `$7F:64C0` at the freeze vs after a normal screen 24 (JP ROM)
5. Compare the **original ROM** and **`nage-libre-en-prologue-test.sfc`** to isolate the patch

### CPU flow reminder

```
$87:D63B
  → $87:D955 (birthday UI init: sounds + pointers)
  → loop: $87:D70C × N  (N→5 via the counter @ $87:D6BC)
       → $83:BA46 → $83:80FF → $80:F8D8
       → phases $83:8103 (7 handlers)
  → $87:DCCB (end-of-prologue transition)
```

The **24 screens** fit within the **5 iterations** of `$87:D70C`, each iteration containing several dialogue advances (phases + `$80:F4A7`).

---

## Corrections to earlier hypotheses

| Earlier hypothesis | Reality (captures) |
|--------------------|--------------------|
| Screen 3 = 西暦 / 地球 narration | **Disproved**: it's a **timestamp** `ＡＭ０６：１２` |
| `$87:896D` = 西暦 prologue text | **Disproved**: it's **「誕生日をおしえてね」** (post-prologue UI) |
| 「よーし」 can't be found | **Screen 4**: `よーし！！　今日は一番乗りだ！！` |

---

*2026-06-07. Captures: `Screenshots/Prologue/nage-libre-prologue-screen-{1..24}.jpg`*
