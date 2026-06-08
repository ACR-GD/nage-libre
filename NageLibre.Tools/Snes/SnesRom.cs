namespace NageLibre.Tools.Snes;

public sealed class SnesRom
{
    public byte[] Data { get; }
    public SnesRomHeader Header { get; }

    public int Size => Data.Length;

    public SnesRom(byte[] data)
    {
        Data = data;
        Header = SnesRomHeader.ReadLoRom(data);
    }

    public static SnesRom Load(string path) => new(File.ReadAllBytes(path));

    public ReadOnlySpan<byte> AsSpan() => Data;

    public ReadOnlySpan<byte> Slice(int offset, int length) =>
        Data.AsSpan(offset, length);
}
