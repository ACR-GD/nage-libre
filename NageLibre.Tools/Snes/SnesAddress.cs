namespace NageLibre.Tools.Snes;

/// <summary>LoROM mapping (typical for this cartridge).</summary>
public static class SnesAddress
{
    public static int? RomOffset(uint snesAddress)
    {
        int bank = (int)((snesAddress >> 16) & 0xFF);
        int offset = (int)(snesAddress & 0xFFFF);
        if (offset < 0x8000)
            return null;
        return ((bank & 0x7F) * 0x8000) + (offset - 0x8000);
    }

    public static uint FromRomOffset(int romOffset)
    {
        int bank = romOffset / 0x8000;
        int offset = (romOffset % 0x8000) + 0x8000;
        return (uint)((bank << 16) | offset);
    }

    public static uint Bank84Pointer(ushort offsetInBank)
    {
        return 0x840000u | offsetInBank;
    }

    public static ushort ParseBank84Pointer(byte lo, byte hi) =>
        (ushort)(lo | (hi << 8));
}
