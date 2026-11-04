namespace NageLibre.Tools.Compression;

/// <summary>
/// Nintendo decompressors common on SNES (Lunar Compress / LC_LZ* formats).
/// The game hasn't been confirmed to use a single format yet — the scanner tries several headers.
/// </summary>
public static class NintendoLz
{
    public enum FormatKind
    {
        Unknown,
        Lz10,
        Lz01,
    }

    public sealed record DecompressResult(FormatKind Kind, byte[] Data, int SourceOffset);

    /// <summary>Format 0x10 — 4-byte header + LZSS stream (SMW, ALTTP, etc.).</summary>
    public static byte[]? TryDecompressLz10(ReadOnlySpan<byte> src)
    {
        if (src.Length < 4 || src[0] != 0x10)
            return null;

        int size = src[1] | (src[2] << 8) | (src[3] << 16);
        if (size <= 0 || size > 0x40000)
            return null;

        var output = new byte[size];
        int outPos = 0;
        int inPos = 4;

        while (outPos < size && inPos < src.Length)
        {
            byte flags = src[inPos++];
            for (int bit = 0; bit < 8 && outPos < size; bit++)
            {
                if ((flags & 0x80) != 0)
                {
                    if (inPos + 1 >= src.Length)
                        return null;
                    int b1 = src[inPos++];
                    int b2 = src[inPos++];
                    int count = (b1 >> 4) + 3;
                    int disp = ((b1 & 0x0F) << 8) | b2;
                    if (disp == 0)
                        disp = 0x1000;
                    int copyFrom = outPos - disp;
                    if (copyFrom < 0)
                        return null;
                    for (int i = 0; i < count && outPos < size; i++)
                        output[outPos++] = output[copyFrom++];
                }
                else
                {
                    if (inPos >= src.Length)
                        return null;
                    output[outPos++] = src[inPos++];
                }
                flags <<= 1;
            }
        }

        return outPos == size ? output : null;
    }

    /// <summary>Format 0x01 — Nintendo variant (same bit stream as LZ10, different type byte).</summary>
    public static byte[]? TryDecompressLz01(ReadOnlySpan<byte> src)
    {
        if (src.Length < 4 || src[0] != 0x01)
            return null;
        // Same algorithm; only the type byte differs.
        return TryDecompressLz10(src);
    }

    public static DecompressResult? TryAuto(ReadOnlySpan<byte> src, int offset = 0)
    {
        if (offset >= src.Length)
            return null;
        var slice = src[offset..];
        if (slice[0] == 0x10)
        {
            var data = TryDecompressLz10(slice);
            if (data != null)
                return new DecompressResult(FormatKind.Lz10, data, offset);
        }
        if (slice[0] == 0x01)
        {
            var data = TryDecompressLz01(slice);
            if (data != null)
                return new DecompressResult(FormatKind.Lz01, data, offset);
        }
        return null;
    }
}
