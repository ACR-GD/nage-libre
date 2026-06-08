namespace NageLibre.Tools.Analysis;

public enum TextEncodingKind
{
    /// <summary>Index glyphe 1 octet, terminé FF xx (pas Shift-JIS).</summary>
    CustomGlyphFfTerminated,
    CustomGlyphFeTerminated,
    CustomGlyphControl,
    CustomGlyphPointer,
    Unknown,
}

public sealed record CharacterInventory(
    int Hiragana, int Katakana, int Kanji, int Ascii, int Other, int UniqueChars);

public sealed record DecodedString(
    int RomOffset,
    int Length,
    TextEncodingKind Encoding,
    string Japanese,
    byte[] RawBytes,
    byte TerminatorByte,
    string? Notes,
    string GlyphIds = "",
    string GlyphDisplay = "");
