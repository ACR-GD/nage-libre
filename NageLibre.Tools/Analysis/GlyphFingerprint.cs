using NageLibre.Tools.Gfx;

namespace NageLibre.Tools.Analysis;

/// <summary>Empreinte 8×8 d’un glyphe 16×16 pour regrouper les doublons en ROM.</summary>
public static class GlyphFingerprint
{
    public static ulong Hash64(ReadOnlySpan<byte> romGlyph64)
    {
        var px = Font16x16.ToIndexedBitmap16x16(romGlyph64);
        ulong h = 0;
        for (int y = 0; y < 8; y++)
        for (int x = 0; x < 8; x++)
        {
            int sx = x * 2, sy = y * 2;
            int ink = 0;
            for (int dy = 0; dy < 2; dy++)
            for (int dx = 0; dx < 2; dx++)
                if (px[(sy + dy) * 16 + (sx + dx)] != 0)
                    ink++;
            if (ink >= 2)
                h |= 1UL << (y * 8 + x);
        }
        return h;
    }

    public static int Hamming(ulong a, ulong b)
    {
        ulong x = a ^ b;
        int n = 0;
        while (x != 0) { n += (int)(x & 1); x >>= 1; }
        return n;
    }
}
