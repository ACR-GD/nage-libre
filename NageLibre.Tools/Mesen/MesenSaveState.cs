using System.IO.Compression;

namespace NageLibre.Tools.Mesen;

/// <summary>
/// Lecteur minimal du format .mss Mesen2 (MSS + en-tête vidéo zlib + état sérialisé zlib).
/// Référence : Mesen2 Core/Shared/SaveStateManager.cpp, Utilities/Serializer.cpp
/// </summary>
public sealed class MesenSaveState
{
    public uint EmulatorVersion { get; init; }
    public uint FormatVersion { get; init; }
    public uint ConsoleType { get; init; }
    public int FrameWidth { get; init; }
    public int FrameHeight { get; init; }
    public string RomFileName { get; init; } = "";
    public IReadOnlyDictionary<string, byte[]> Fields { get; init; }
        = new Dictionary<string, byte[]>();

    public byte[]? WorkRam => Fields.GetValueOrDefault("memoryManager.workRam");
    public byte[]? Vram => Fields.GetValueOrDefault("ppu.vram");
    public byte[]? Cgram => Fields.GetValueOrDefault("ppu.cgram");

    public static MesenSaveState Load(string path)
    {
        var bytes = File.ReadAllBytes(path);
        int pos = 3;
        if (bytes.Length < 32 || System.Text.Encoding.ASCII.GetString(bytes, 0, 3) != "MSS")
            throw new InvalidDataException("Fichier MSS invalide.");

        uint emuVer = ReadU32(bytes, ref pos);
        uint fmtVer = ReadU32(bytes, ref pos);
        uint console = ReadU32(bytes, ref pos);

        uint fbSize = ReadU32(bytes, ref pos);
        int width = (int)ReadU32(bytes, ref pos);
        int height = (int)ReadU32(bytes, ref pos);
        _ = ReadU32(bytes, ref pos); // scale * 100
        uint videoCompSize = ReadU32(bytes, ref pos);
        pos += (int)videoCompSize; // skip compressed screenshot

        uint nameLen = ReadU32(bytes, ref pos);
        string romName = System.Text.Encoding.UTF8.GetString(bytes, pos, (int)nameLen);
        pos += (int)nameLen;

        if (bytes[pos++] != 1)
            throw new InvalidDataException("État Mesen non compressé (non géré).");

        uint decompSize = ReadU32(bytes, ref pos);
        uint compSize = ReadU32(bytes, ref pos);
        var compressed = bytes.AsSpan(pos, (int)compSize);
        pos += (int)compSize;

        var stateData = ZlibDecompress(compressed, (int)decompSize);
        var fields = ParseSerializerMap(stateData);

        return new MesenSaveState
        {
            EmulatorVersion = emuVer,
            FormatVersion = fmtVer,
            ConsoleType = console,
            FrameWidth = width,
            FrameHeight = height,
            RomFileName = romName,
            Fields = fields,
        };
    }

    private static Dictionary<string, byte[]> ParseSerializerMap(byte[] data)
    {
        var map = new Dictionary<string, byte[]>(StringComparer.Ordinal);
        int i = 0;
        while (i < data.Length)
        {
            int end = Array.IndexOf(data, (byte)0, i);
            if (end < 0)
                break;
            string key = System.Text.Encoding.ASCII.GetString(data, i, end - i);
            i = end + 1;
            if (i + 4 > data.Length)
                break;
            int valueSize = data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24);
            i += 4;
            if (i + valueSize > data.Length)
                break;
            var value = new byte[valueSize];
            Buffer.BlockCopy(data, i, value, 0, valueSize);
            map[key] = value;
            i += valueSize;
        }
        return map;
    }

    private static byte[] ZlibDecompress(ReadOnlySpan<byte> src, int expectedSize)
    {
        using var input = new MemoryStream(src.ToArray());
        using var zlib = new ZLibStream(input, CompressionMode.Decompress);
        using var output = new MemoryStream();
        zlib.CopyTo(output);
        var result = output.ToArray();
        if (expectedSize > 0 && result.Length != expectedSize)
        {
            // Mesen stocke la taille attendue ; tolérer léger écart.
        }
        return result;
    }

    private static uint ReadU32(byte[] data, ref int pos)
    {
        uint v = (uint)(data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16) | (data[pos + 3] << 24));
        pos += 4;
        return v;
    }
}
