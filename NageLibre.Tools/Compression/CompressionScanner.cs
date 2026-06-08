using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Compression;

public sealed record CompressionCandidate(
    int RomOffset,
    string Format,
    int CompressedSizeHint,
    int DecompressedSize,
    string Notes);

public static class CompressionScanner
{
    public static IEnumerable<CompressionCandidate> Scan(SnesRom rom, int minDecompressed = 64)
    {
        var data = rom.Data;
        for (int off = 0; off < data.Length - 4; off++)
        {
            if (data[off] is not (0x01 or 0x10 or 0x11 or 0x12))
                continue;

            var result = Decompressor.TryAt(data, off);
            if (result == null || result.Data.Length < minDecompressed)
                continue;

            int headerSize = 4;
            int compHint = Math.Min(result.Data.Length + headerSize + 64, data.Length - off);
            int glyphs = Decompressor.CountGlyphBlocks(result.Data);

            if (result.Score < 4 && glyphs == 0 && result.Data.Length < 256)
                continue;

            yield return new CompressionCandidate(
                off,
                result.Format.ToString(),
                compHint,
                result.Data.Length,
                $"score={result.Score} glyphs={glyphs}");
        }
    }

    private static int ScoreLikelyText(ReadOnlySpan<byte> data)
    {
        int score = 0;
        foreach (var b in data)
        {
            if (b == 0x8D) score += 3;
            if (b is >= 0x20 and < 0x7F) score++;
            if (b is >= 0x80 and <= 0xFC) score++;
        }
        return score;
    }
}
