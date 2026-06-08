namespace NageLibre.Tools.Compression;

public enum CompressionFormat
{
    Unknown,
    Lz01,
    Lz10,
    Lz11,
    Lz12,
}

public sealed record DecompressAttempt(
    CompressionFormat Format,
    int RomOffset,
    byte[] Data,
    int Score);

public static class Decompressor
{
    public static DecompressAttempt? TryAt(ReadOnlySpan<byte> rom, int offset)
    {
        if (offset >= rom.Length)
            return null;

        byte header = rom[offset];
        byte[]? data = header switch
        {
            0x01 => NintendoLz.TryDecompressLz01(rom[offset..]),
            0x10 => NintendoLz.TryDecompressLz10(rom[offset..]),
            0x11 => NintendoLz11.TryDecompress(rom[offset..]),
            0x12 => NintendoLz12.TryDecompress(rom[offset..]),
            _ => null,
        };

        if (data == null || data.Length < 16)
            return null;

        var format = header switch
        {
            0x01 => CompressionFormat.Lz01,
            0x10 => CompressionFormat.Lz10,
            0x11 => CompressionFormat.Lz11,
            0x12 => CompressionFormat.Lz12,
            _ => CompressionFormat.Unknown,
        };

        return new DecompressAttempt(format, offset, data, ScorePayload(data));
    }

    public static readonly (int Start, int End)[] DataRegions =
    [
        (0x08000, 0x180000),
    ];

    public static IEnumerable<DecompressAttempt> Scan(byte[] rom, int minSize = 128, int maxResults = 500)
    {
        int found = 0;
        foreach (var (regionStart, regionEnd) in DataRegions)
        {
        for (int off = regionStart; off < regionEnd - 4 && found < maxResults; off++)
        {
            if (rom[off] is not (0x01 or 0x10 or 0x11 or 0x12))
                continue;

            var attempt = TryAt(rom.AsSpan(), off);
            if (attempt == null || attempt.Data.Length < minSize)
                continue;

            if (attempt.Score < 8)
                continue;

            yield return attempt;
            found++;
        }
        }
    }

    /// <summary>Heuristique : texte (0x8D), glyphes 2bpp, SJIS.</summary>
    public static int ScorePayload(ReadOnlySpan<byte> data)
    {
        int score = 0;
        foreach (var b in data)
        {
            if (b == 0x8D) score += 4;
            if (b is >= 0x20 and < 0x7F) score += 1;
            if (b is >= 0x80 and <= 0xFC) score += 1;
        }

        if (ContainsGlyphBlock(data))
            score += 50;

        return score;
    }

    public static bool ContainsGlyphBlock(ReadOnlySpan<byte> data)
    {
        // Signature こ TL (hiragana)
        ReadOnlySpan<byte> ko = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 3, 3, 6, 7];
        return data.IndexOf(ko) >= 0;
    }

    public static int CountGlyphBlocks(ReadOnlySpan<byte> data)
    {
        int count = 0;
        for (int i = 0; i + 64 <= data.Length; i += 64)
        {
            if (IsLikelyGlyph64(data.Slice(i, 64)))
                count++;
        }
        return count;
    }

    public static bool IsLikelyGlyph64(ReadOnlySpan<byte> block)
    {
        if (!block.ContainsAnyExcept((byte)0))
            return false;

        for (int t = 0; t < 4; t++)
        {
            var tile = block.Slice(t * 16, 16);
            int bits = 0;
            foreach (var b in tile)
                bits += System.Numerics.BitOperations.PopCount(b);
            if (bits < 4 || bits > 100)
                return false;
        }
        return true;
    }
}
