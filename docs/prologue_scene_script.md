# Nage Libre — Script de scène du prologue (décompilé)

Généré par `python3 scripts/decompile_prologue_script.py` depuis un dump WRAM.
Le bloc $7F:64C0 contient **tout** le script de narration du prologue (24 lignes).
Les □ = kanji non encore mappés dans `docs/kanji_font_index.csv` (transcription manuelle en cours).

```
# Décompilation du script $7F:64C0  (dump : 20260608_092959_PC_838103_001)

+0000  op 23 [4o] data-ptr     0012
+0004  op 20 [2o] texte-ROM    
+0006  op 2B [4o] TEXTE        0124   → @+0124 (29 IDs) : «□□□□□□□□□□     □□□□□□□□□     »
+000A  op 2C [2o] ctrl         
+000C  op 20 [2o] texte-ROM    
+000E  op 29 [4o] data-ptr     0011
+0012  op 2B [4o] TEXTE        0162   → @+0162 (30 IDs) : «この世界をてのに……  にをつをめて……»
+0016  op 2C [2o] ctrl         
+0018  op 20 [2o] texte-ROM    
+001A  op 29 [4o] data-ptr     0012
+001E  op 2B [4o] TEXTE        01A2   → @+01A2 (29 IDs) : «                …… AM ……»
+0022  op 2C [2o] ctrl         
+0024  op 20 [2o] texte-ROM    
+0026  op 29 [4o] data-ptr     0002
+002A  op 24 [6o] data-ptr     0000 0000
+0030  op 26 [4o] TEXTE        063E   → @+063E (26 IDs) : «よをし‼ 日はりだ‼ いれてくぉ‼»
+0034  op 27 [2o] data-ptr     
+0036  op 20 [2o] texte-ROM    
+0038  op 3A [2o] data-ptr     
+003A  op 26 [4o] TEXTE        0676   → @+0676 (11 IDs) : «……あれ……か……»
+003E  op 27 [2o] data-ptr     
+0040  op 20 [2o] texte-ROM    
+0042  op 25 [6o] data-ptr     0000 0000
+0048  op 29 [4o] data-ptr     0012
+004C  op 2B [4o] TEXTE        01E0   → @+01E0 (29 IDs) : «                …… AM ……»
+0050  op 2C [2o] ctrl         
+0052  op 20 [2o] texte-ROM    
+0054  op 29 [4o] data-ptr     0000
+0058  op 24 [6o] data-ptr     0004 0000
+005E  op 26 [4o] TEXTE        0690   → @+0690 (15 IDs) : «さてうどですね»
+0062  op 27 [2o] data-ptr     
+0064  op 20 [2o] texte-ROM    
+0066  op 3A [2o] data-ptr     
+0068  op 26 [4o] TEXTE        06B2   → @+06B2 (30 IDs) : «あ　 っとしたが りほしたね……でしう　»
+006C  op 27 [2o] data-ptr     
+006E  op 20 [2o] texte-ROM    
+0070  op 25 [6o] data-ptr     0004 0000
+0076  op 29 [4o] data-ptr     0012
+007A  op 2B [4o] TEXTE        021E   → @+021E (29 IDs) : «                   AM ……»
+007E  op 2C [2o] ctrl         
+0080  op 20 [2o] texte-ROM    
+0082  op 29 [4o] data-ptr     0006
+0086  op 24 [6o] data-ptr     0001 0000
+008C  op 26 [4o] TEXTE        06F4   → @+06F4 (25 IDs) : «たをらららんたをらららんに をこぉ»
+0090  op 27 [2o] data-ptr     
+0092  op 20 [2o] texte-ROM    
+0094  op 26 [4o] TEXTE        072A   → @+072A (29 IDs) : «いをほから をけ   おほをえには つをく»
+0098  op 27 [2o] data-ptr     
+009A  op 20 [2o] texte-ROM    
+009C  op 3A [2o] data-ptr     
+009E  op 26 [4o] TEXTE        0768   → @+0768 (15 IDs) : «ん‼ なんかこったよ‼»
+00A2  op 27 [2o] data-ptr     
+00A4  op 20 [2o] texte-ROM    
+00A6  op 25 [6o] data-ptr     0001 0000
+00AC  op 29 [4o] data-ptr     0012
+00B0  op 2B [4o] TEXTE        025C   → @+025C (29 IDs) : «                …… AM ……»
+00B4  op 2C [2o] ctrl         
+00B6  op 20 [2o] texte-ROM    
+00B8  op 29 [4o] data-ptr     0000
+00BC  op 24 [6o] data-ptr     0002 0000
+00C2  op 26 [4o] TEXTE        029A   → @+029A (45 IDs) : «あああん‼      いっい          してる‼ ん‼»
+00C6  op 27 [2o] data-ptr     
+00C8  op 20 [2o] texte-ROM    
+00CA  op 26 [4o] TEXTE        02F8   → @+02F8 (41 IDs) : «おくくのように     ブラシとトをストなんて   くえったりして»
+00CE  op 27 [2o] data-ptr     
+00D0  op 20 [2o] texte-ROM    
+00D2  op 26 [4o] TEXTE        034E   → @+034E (44 IDs) : «しかさっほでガリガリと かってたのはどうら   ブラシのうだったたい‼»
+00D6  op 27 [2o] data-ptr     
+00D8  op 20 [2o] texte-ROM    
+00DA  op 26 [4o] TEXTE        03AA   → @+03AA (42 IDs) : «このあたしのとすほされたキのようなしいが    ロロになっう‼»
+00DE  op 27 [2o] data-ptr     
+00E0  op 20 [2o] texte-ROM    
+00E2  op 26 [4o] TEXTE        0402   → @+0402 (42 IDs) : «……はあはあれにして  しべりながらるってのは だかつかれうね»
+00E6  op 27 [2o] data-ptr     
+00E8  op 20 [2o] texte-ROM    
+00EA  op 26 [4o] TEXTE        045A   → @+045A (45 IDs) : «でほいたからには   アトはてりいいんだから ラクとえラクなんだけどね»
+00EE  op 27 [2o] data-ptr     
+00F0  op 20 [2o] texte-ROM    
+00F2  op 3A [2o] data-ptr     
+00F4  op 26 [4o] TEXTE        04B8   → @+04B8 (35 IDs) : «……ありり　 なんかンな がしたようなが…    …だろ　»
+00F8  op 27 [2o] data-ptr     
+00FA  op 20 [2o] texte-ROM    
+00FC  op 26 [4o] TEXTE        0502   → @+0502 (27 IDs) : «うをん……えをと……     ……んないからいい‼»
+0100  op 27 [2o] data-ptr     
+0102  op 20 [2o] texte-ROM    
+0104  op 26 [4o] TEXTE        053C   → @+053C (41 IDs) : «…なんてってるうにどうらリリでにはにあったたい‼ イヤツ‼»
+0108  op 27 [2o] data-ptr     
+010A  op 20 [2o] texte-ROM    
+010C  op 26 [4o] TEXTE        0592   → @+0592 (43 IDs) : «ントによかった‼ 日は でりだんねになるところだった»
+0110  op 27 [2o] data-ptr     
+0112  op 20 [2o] texte-ROM    
+0114  op 26 [4o] TEXTE        05EC   → @+05EC (39 IDs) : «さあていたぉ‼     ……でがいつより かだな…だろ　»
+0118  op 27 [2o] data-ptr     
+011A  op 20 [2o] texte-ROM    
+011C  op 25 [6o] data-ptr     0002 0000
+0122  03FE  ?? opcode inconnu — arrêt

## 24 chaîne(s) de texte référencée(s) :
  opcode @+0006 → +0124 : «□□□□□□□□□□     □□□□□□□□□     »
      IDs: 16C 16E 170 172 174 176 178 17A 17C 36C 3FE 3FE 3FE 3FE 3FE 16E 434 436 438 43A 43C 46C 46E 470 3FE 3FE 3FE 3FE 3FE
  opcode @+0012 → +0162 : «この世界をてのに……  にをつをめて……»
      IDs: 2E6 032 068 33A 33C 0AE 304 058 330 068 1B6 062 2AA 2AA 3FE 3FE 244 062 4C0 0AE 70A 054 22A 0AE 634 08E 058 2AA 2AA 2E8
  opcode @+001E → +01A2 : «                …… AM ……»
      IDs: 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 2AA 2AA 3FE 400 418 158 164 3DE 15A 15C 3FE 2AA 2AA
  opcode @+0030 → +063E : «よをし‼ 日はりだ‼ いれてくぉ‼»
      IDs: 09E 092 03A 2E0 3FE 340 2C8 06A 1D6 382 1FE 0A4 04C 2E0 3FE 316 5F2 014 3BC 0A8 058 34A 02A 048 01E 2E0
  opcode @+003A → +0676 : «……あれ……か……»
      IDs: 2AA 2AA 010 0A8 2AA 2AA 340 318 022 2AA 2AA
  opcode @+004C → +01E0 : «                …… AM ……»
      IDs: 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 2AA 2AA 3FE 400 418 158 168 3DE 15E 162 3FE 2AA 2AA
  opcode @+005E → +0690 : «さてうどですね»
      IDs: 036 058 2FA 208 212 094 04E 0A0 018 05E 05A 03E 0AC 066 3D0
  opcode @+0068 → +06B2 : «あ　 っとしたが りほしたね……でしう　»
      IDs: 076 010 346 3FE 340 076 0AC 052 05C 03A 04A 342 722 024 3FE 680 0A4 088 03A 04A 0AC 066 2AA 2AA 318 05A 03A 0A0 018 346
  opcode @+007A → +021E : «                   AM ……»
      IDs: 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 400 418 15A 158 3DE 15C 168 3FE 2AA 2AA
  opcode @+008C → +06F4 : «たをらららんたをらららんに をこぉ»
      IDs: 3CE 04A 092 0A2 0A2 0A2 0B0 2FA 04A 092 0A2 0A2 0A2 0B0 3CE 1D0 310 062 3CE 3FE 34A 092 032 01E 3CE
  opcode @+0094 → +072A : «いをほから をけ   おほをえには つをく»
      IDs: 014 092 088 022 0A2 3CE 3FE 34A 092 02E 06C 3CE 3FE 3FE 3FE 020 782 088 092 01C 062 06A 3CE 3FE 054 092 02A 048 3CE
  opcode @+009E → +0768 : «ん‼ なんかこったよ‼»
      IDs: 026 098 0B0 2E0 3FE 060 0B0 022 534 032 052 04A 09E 340 2E0
  opcode @+00B0 → +025C : «                …… AM ……»
      IDs: 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 2AA 2AA 3FE 400 418 15A 15A 3DE 15E 166 3FE 2AA 2AA
  opcode @+00C2 → +029A : «あああん‼      いっい          してる‼ ん‼»
      IDs: 096 010 010 010 090 090 090 0B0 2E0 3FE 3FE 3FE 3FE 3FE 3FE 18C 014 052 06E 014 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 3FE 510 7AC 03A 058 0A6 016 016 016 016 2E0 3FE 026 098 0B0 2E0
  opcode @+00CA → +02F8 : «おくくのように     ブラシとトをストなんて   くえったりして»
      IDs: 020 096 02A 046 02A 068 09E 018 062 2FA 3FE 3FE 3FE 3FE 3FE 10C 11A 140 0DC 05C 0FE 092 0E0 0FE 060 0B0 058 3FE 3FE 3FE 02A 0AC 01C 04E 098 052 04A 0A4 03A 058 2FA
  opcode @+00D2 → +034E : «しかさっほでガリガリと かってたのはどうら   ブラシのうだったたい‼»
      IDs: 03A 022 094 2FA 036 052 026 088 05A 0C6 142 0C6 142 05C 3FE 022 03C 052 058 04A 068 06A 2FA 05E 018 096 0A2 3FE 3FE 3FE 10C 11A 140 0DC 068 082 018 04C 052 04A 08A 04A 014 2E0
  opcode @+00DA → +03AA : «このあたしのとすほされたキのようなしいが    ロロになっう‼»
      IDs: 032 068 2FA 010 04A 03A 068 2FA 05C 028 03E 088 036 0A8 04A 0C8 10E 068 09E 018 060 284 03A 014 3F6 024 3FE 3FE 3FE 3FE 126 148 126 148 062 060 052 04E 098 018 0AC 2E0
  opcode @+00E2 → +0402 : «……はあはあれにして  しべりながらるってのは だかつかれうね»
      IDs: 2AA 2AA 06A 010 06A 010 2F8 046 0A8 062 03A 058 094 3FE 3FE 03A 098 07E 0A4 060 024 0A2 2FA 680 0A6 052 058 068 06A 3FE 318 04C 022 054 022 0A8 04E 098 018 0AC 066 2F8
  opcode @+00EA → +045A : «でほいたからには   アトはてりいいんだから ラクとえラクなんだけどね»
      IDs: 05A 094 088 2FA 19C 014 04A 022 0A2 062 06A 2FA 3FE 3FE 3FE 0B2 0FE 06A 200 058 0A4 098 090 014 014 0B0 04C 022 0A2 3FE 140 0CC 05C 33E 01C 06C 140 0CC 060 0B0 04C 02E 05E 066 3D0
  opcode @+00F4 → +04B8 : «……ありり　 なんかンな がしたようなが…    …だろ　»
      IDs: 2AA 2AA 010 0A4 0A4 346 3FE 340 060 0B0 022 11E 14E 060 3FE 342 03C 024 03A 04A 09E 018 060 316 024 2AA 3FE 3FE 3FE 3FE 2AA 318 04C 0AA 346
  opcode @+00FC → +0502 : «うをん……えをと……     ……んないからいい‼»
      IDs: 018 092 0B0 2AA 2AA 01C 092 05C 2AA 2AA 3FE 3FE 3FE 3FE 3FE 2AA 2AA 328 0B0 060 014 022 0A2 014 014 096 2E0
  opcode @+0104 → +053C : «…なんてってるうにどうらリリでにはにあったたい‼ イヤツ‼»
      IDs: 2AA 060 0B0 058 33E 052 058 0A6 018 04E 062 05E 018 096 0A2 0CA 142 0CA 142 05A 1D0 310 062 06A 2FA 212 062 010 052 04A 08A 04A 014 2E0 3FE 0B6 136 0F4 124 0C0 2E0
  opcode @+010C → +0592 : «ントによかった‼ 日は でりだんねになるところだった»
      IDs: 124 14E 0FE 062 09E 022 052 04A 090 2E0 3FE 340 2C8 06A 3FE 160 208 212 50C 05A 1D0 310 514 0AC 0A4 04C 094 0B0 066 3CE 6A6 08A 062 060 0A6 05C 032 0AA 04C 052 04A 0AC 3D0
  opcode @+0114 → +05EC : «さあていたぉ‼     ……でがいつより かだな…だろ　»
      IDs: 036 010 058 2FA 19C 014 04A 048 01E 2E0 3FE 3FE 3FE 3FE 3FE 2AA 2AA 05A 094 2FA 1D0 310 024 2FA 014 054 094 09E 0A4 3FE 3AA 022 04C 060 2AA 318 04C 0AA 346
```
