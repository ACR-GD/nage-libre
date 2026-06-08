namespace NageLibre.Tools.Gfx;

public static class SnesGfx
{
    /// <summary>Palette BGR555 SNES (2 octets, little endian) → RGB888.</summary>
    public static (byte R, byte G, byte B) Bgr555ToRgb(byte lo, byte hi)
    {
        int v = lo | (hi << 8);
        int b = (v & 0x1F) << 3;
        int g = ((v >> 5) & 0x1F) << 3;
        int r = ((v >> 10) & 0x1F) << 3;
        return ((byte)(r | (r >> 5)), (byte)(g | (g >> 5)), (byte)(b | (b >> 5)));
    }

    /// <summary>Tuile 2bpp 8×8 (16 octets) → 64 pixels, indices 0–3.</summary>
    public static byte[] Decode2BppTile8x8(ReadOnlySpan<byte> tile)
    {
        if (tile.Length < 16)
            throw new ArgumentException("Tuile 2bpp attendue : 16 octets.");
        var pixels = new byte[64];
        for (int row = 0; row < 8; row++)
        {
            int bp0 = tile[row];
            int bp1 = tile[row + 8];
            for (int col = 0; col < 8; col++)
            {
                int bit = 7 - col;
                int p0 = (bp0 >> bit) & 1;
                int p1 = (bp1 >> bit) & 1;
                pixels[row * 8 + col] = (byte)(p0 | (p1 << 1));
            }
        }
        return pixels;
    }

    /// <summary>Tuile 4bpp 8×8 (32 octets) → 64 pixels, indices 0–15.</summary>
    public static byte[] Decode4BppTile8x8(ReadOnlySpan<byte> tile)
    {
        if (tile.Length < 32)
            throw new ArgumentException("Tuile 4bpp attendue : 32 octets.");
        var pixels = new byte[64];
        for (int row = 0; row < 8; row++)
        {
            int planes = tile[row] | (tile[row + 8] << 8) |
                         (tile[row + 16] << 16) | (tile[row + 24] << 24);
            for (int col = 0; col < 8; col++)
            {
                int shift = 7 - col;
                int v = (planes >> (shift * 4)) & 0xF;
                pixels[row * 8 + col] = (byte)v;
            }
        }
        return pixels;
    }

    public static void ExportIndexedBmp(
        string path,
        byte[] indices,
        int width,
        int height,
        IReadOnlyList<(byte R, byte G, byte B)> paletteRgb)
    {
        using var fs = File.Create(path);
        using var bw = new BinaryWriter(fs);
        int rowSize = ((width + 3) / 4) * 4;
        int pixelBytes = rowSize * height;
        bw.Write((byte)'B');
        bw.Write((byte)'M');
        bw.Write(14 + 40 + paletteRgb.Count * 4 + pixelBytes);
        bw.Write(0);
        bw.Write(14 + 40 + paletteRgb.Count * 4);
        bw.Write(40);
        bw.Write(width);
        bw.Write(height);
        bw.Write((short)1);
        bw.Write((short)8);
        bw.Write(0);
        bw.Write(pixelBytes);
        bw.Write(2835);
        bw.Write(2835);
        bw.Write(0);
        bw.Write(paletteRgb.Count);
        foreach (var (r, g, b) in paletteRgb)
        {
            bw.Write(b);
            bw.Write(g);
            bw.Write(r);
            bw.Write((byte)0);
        }
        for (int y = height - 1; y >= 0; y--)
        {
            for (int x = 0; x < width; x++)
            {
                int idx = indices[y * width + x];
                bw.Write(idx < paletteRgb.Count ? (byte)idx : (byte)0);
            }
            for (int pad = (width % 4); pad != 0 && pad < 4; pad++)
                bw.Write((byte)0);
        }
    }
}
