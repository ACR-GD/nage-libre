#!/usr/bin/env python3
"""Pré-remplit docs/kanji_manual.csv avec une première passe de lecture de l'atlas.

Ne remplit que les glyphes lus avec une confiance raisonnable (kana, ponctuation,
kanji clairs). Les glyphes ambigus restent vides (à compléter à la main).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "docs" / "kanji_manual.csv"

# char_id (hex int) -> caractère lu sur l'atlas (première passe)
READ = {
    # --- ponctuation / parenthèses ---
    0x02FA: "、", 0x02F8: "。", 0x02E6: "「", 0x02E8: "」",
    # --- hiragana ---
    0x0094: "も", 0x00AC: "わ", 0x004E: "ち", 0x0046: "そ", 0x0026: "き",
    0x008A: "み", 0x003C: "じ", 0x00A0: "ょ", 0x0096: "や", 0x006C: "ば",
    0x0082: "は", 0x0048: "ぞ", 0x0034: "ご", 0x0040: "ず", 0x0038: "ざ",
    0x0044: "ぜ", 0x002C: "ぐ", 0x0028: "ぎ", 0x0056: "づ", 0x006E: "ぱ",
    0x0098: "ゃ", 0x0090: "ぁ", 0x0072: "び", 0x0076: "ふ", 0x0078: "ぶ",
    0x007C: "へ", 0x0012: "ぃ", 0x0016: "ぅ",
    # --- petit katakana ---
    0x0138: "ュ",
    # --- katakana ---
    0x00FA: "テ", 0x00D4: "コ", 0x00F0: "チ", 0x0102: "ナ",
    # --- kanji (confiance haute) ---
    0x0318: "何", 0x034A: "行", 0x03BC: "人", 0x0206: "入", 0x0250: "来",
    0x0308: "倒", 0x033E: "言", 0x0324: "見", 0x0340: "今", 0x0348: "出",
    0x0316: "気", 0x0304: "全", 0x0188: "回", 0x01AC: "手", 0x0214: "勝",
    0x04FC: "方", 0x018C: "力", 0x03AE: "本", 0x0266: "誰", 0x0498: "開",
    0x030A: "所", 0x01CA: "体", 0x03C8: "戦", 0x01A0: "思", 0x02B2: "部",
    0x031C: "帰", 0x04E8: "通", 0x031E: "侍", 0x0548: "事", 0x070A: "持",
    0x01D0: "学", 0x030E: "宝", 0x050C: "目", 0x0356: "元", 0x025E: "子",
    0x0480: "戻", 0x038E: "姫", 0x04B2: "先", 0x039E: "舞", 0x0390: "求",
    0x04B6: "自", 0x0512: "分", 0x0312: "敵", 0x0212: "間", 0x031A: "逃",
    0x0252: "最", 0x01A8: "道", 0x0284: "美", 0x01D6: "一", 0x01F2: "上",
    0x0482: "太", 0x053A: "知", 0x0244: "心", 0x01B6: "物", 0x03C4: "進",
    0x02C6: "場", 0x04C6: "女", 0x0350: "聞", 0x04B0: "向", 0x0216: "飛",
    0x0208: "時", 0x04DE: "下", 0x019E: "空", 0x0360: "考", 0x0302: "件",
    0x0376: "強", 0x0518: "室", 0x03B0: "当", 0x034E: "同", 0x03AA: "木",
    0x04B4: "現", 0x01EA: "和", 0x04D0: "玉", 0x0320: "街", 0x04E4: "呼",
    0x0358: "助", 0x035E: "教", 0x0620: "書", 0x0634: "集", 0x04F8: "階",
    0x027E: "達", 0x04AC: "高", 0x0682: "立", 0x01A4: "動", 0x055A: "前",
    0x01E0: "使", 0x077C: "引", 0x054C: "少", 0x0534: "起", 0x03C6: "選",
    0x02EA: "石", 0x0710: "読", 0x0374: "他", 0x0366: "原", 0x0510: "運",
    0x035C: "外", 0x0104: "二", 0x030C: "話", 0x0364: "草", 0x032C: "月",
    0x0708: "止", 0x0738: "地", 0x0314: "天", 0x0392: "無", 0x032A: "正",
    0x0610: "直", 0x0566: "追",
}


def main():
    rows = list(csv.DictReader(MANUAL.open()))
    n = 0
    for r in rows:
        cid = int(r["char_id_hex"], 16)
        if cid in READ and not (r.get("unicode") or "").strip():
            r["unicode"] = READ[cid]
            n += 1
    with MANUAL.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "char_id_hex", "occ", "unicode"])
        w.writeheader()
        w.writerows(rows)
    print(f"{n} glyphes pré-remplis sur {len(READ)} proposés ; CSV mis à jour.")


if __name__ == "__main__":
    main()
