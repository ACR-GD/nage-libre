namespace NageLibre.Tools.Snes;

public sealed class SnesRomHeader
{
    public string Title { get; init; } = "";
    public byte MapMode { get; init; }
    public byte RomType { get; init; }
    public bool HiRom => (MapMode & 1) != 0;
    public bool FastRom => (MapMode & 0x80) != 0;

    public static SnesRomHeader ReadLoRom(ReadOnlySpan<byte> rom)
    {
        const int headerOffset = 0x7FC0;
        if (rom.Length < headerOffset + 0x40)
            throw new InvalidDataException("ROM trop petite pour l'en-tête SNES.");

        var block = rom.Slice(headerOffset, 0x40);
        var title = System.Text.Encoding.ASCII.GetString(block[..21]).TrimEnd('\0', ' ');
        return new SnesRomHeader
        {
            Title = title,
            MapMode = block[0x15],
            RomType = block[0x16],
        };
    }
}
