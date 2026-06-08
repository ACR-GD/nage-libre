namespace NageLibre.Tools.Compression;

/// <summary>Format Nintendo 0x11 (LC_LZ2 / SMW US style) — en-tête 3 octets de taille.</summary>
public static class NintendoLz11
{
    public static byte[]? TryDecompress(ReadOnlySpan<byte> src)
    {
        if (src.Length < 4 || src[0] != 0x11)
            return null;

        int size = src[1] | (src[2] << 8) | ((src[3] & 0x7F) << 16);
        if (size <= 0 || size > 0x80000)
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
}
