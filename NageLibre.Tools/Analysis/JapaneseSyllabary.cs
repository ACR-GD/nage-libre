namespace NageLibre.Tools.Analysis;

/// <summary>Gojūon order, to align the font's syllabary glyphs.</summary>
public static class JapaneseSyllabary
{
    /// <summary>Basic hiragana (46) + extensions common in SNES games.</summary>
    public static readonly string HiraganaExtended =
        "あいうえお" +
        "かきくけこがぎぐげご" +
        "さしすせそざじずぜぞ" +
        "たちつてとだぢづでど" +
        "なにぬねの" +
        "はひふへほばびぶべぼぱぴぷぺぽ" +
        "まみむめも" +
        "やゆよゃゅょ" +
        "らりるれろ" +
        "わをんゎ" +
        "っー・";

    public static readonly string KatakanaExtended =
        "アイウエオ" +
        "カキクケコガギグゲゴ" +
        "サシスセソザジズゼゾ" +
        "タチツテトダヂヅデド" +
        "ナニヌネノ" +
        "ハヒフヘホバビブベボパピプペポ" +
        "マミムメモ" +
        "ヤユヨャュョ" +
        "ラリルレロ" +
        "ワヲンヮ" +
        "ッー・";

    public static bool IsKanaLikeCategory(string category) =>
        category is "syllabary_latin" or "kana_kanji_light" or "sparse";

    /// <summary>Known text byte for こ (VRAM tile $108, ROM ~0x28540).</summary>
    public const byte KnownKoTextByte = 0x0D;
    public const char KnownKoChar = 'こ';
    public const int KnownKoVramTile = 0x108;
    public const int KnownKoRomOffset = 0x28540;
}
