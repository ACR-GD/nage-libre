namespace NageLibre.Tools.Gfx;

/// <summary>
/// Police 16×16 du jeu : 4 tuiles 2bpp 8×8 par caractère.
/// En ROM : quadrants contigus (+0, +16, +32, +48 octets).
/// En VRAM (après chargement) : indices +0, +1, +16, +17 (disposition SNES 32 tuiles de large).
/// </summary>
public static class Font16x16
{
    public const int TileBytes = 16;
    public const int CharacterBytes = 64;

    public enum Quadrant { TopLeft, TopRight, BottomLeft, BottomRight }

    /// <summary>Offsets en octets dans un bloc ROM de 64 octets (4 tuiles linéaires).</summary>
    public static int RomQuadrantOffset(Quadrant q) => (int)q * TileBytes;

    /// <summary>Index de tuile VRAM relatif au glyphe (base = index du quadrant HG).</summary>
    public static int VramTileIndexOffset(Quadrant q) => q switch
    {
        Quadrant.TopLeft => 0,
        Quadrant.TopRight => 1,
        Quadrant.BottomLeft => 0x10,
        Quadrant.BottomRight => 0x11,
        _ => throw new ArgumentOutOfRangeException(nameof(q)),
    };

    public static int VramByteOffset(Quadrant q, int baseTileIndex, int tilesetWordAddress = 0x5000)
    {
        int baseByte = tilesetWordAddress * 2 + baseTileIndex * TileBytes;
        return baseByte + VramTileIndexOffset(q) * TileBytes;
    }

    public static byte[] ReadRomCharacter(ReadOnlySpan<byte> rom, int romOffset)
    {
        var buf = new byte[CharacterBytes];
        rom.Slice(romOffset, CharacterBytes).CopyTo(buf);
        return buf;
    }

    public static byte[] ComposeVramLayout(ReadOnlySpan<byte> romLinear64)
    {
        // Réordonne ROM linéaire → ordre d'indices VRAM pour export/debug
        var ordered = new byte[CharacterBytes];
        ReadOnlySpan<int> romOff = [0, 16, 32, 48];
        ReadOnlySpan<int> vramIdx = [0, 1, 2, 3]; // slots 0,1,16,17 in 4-tile buffer
        int[] vramSlotByte = [0, 16, 32, 48]; // local buffer linear for BMP
        for (int i = 0; i < 4; i++)
            romLinear64.Slice(romOff[i], 16).CopyTo(ordered.AsSpan(vramSlotByte[i], 16));
        return ordered;
    }

    public static byte[] ToIndexedBitmap16x16(ReadOnlySpan<byte> romLinear64)
    {
        var pixels = new byte[16 * 16];
        for (int q = 0; q < 4; q++)
        {
            int qx = (q % 2) * 8;
            int qy = (q / 2) * 8;
            var tile = romLinear64.Slice(q * 16, 16);
            var decoded = SnesGfx.Decode2BppTile8x8(tile);
            for (int y = 0; y < 8; y++)
            for (int x = 0; x < 8; x++)
                pixels[(qy + y) * 16 + (qx + x)] = decoded[y * 8 + x];
        }
        return pixels;
    }
}
