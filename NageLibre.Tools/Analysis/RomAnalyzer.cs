using System.Globalization;
using System.Text;
using NageLibre.Tools.Compression;
using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Analysis;

public static class RomAnalyzer
{
    public const int BankSize = 0x8000;
    public const int Bank84RomStart = 0x20000;

    public sealed record Bank84Pointer(int RomOffset, ushort Offset, uint SnesAddress);

    public sealed record ScriptRecord(int RomOffset, ushort Command, IReadOnlyList<Bank84Pointer> Pointers);

    public sealed record Text8DString(int RomOffset, IReadOnlyList<byte> CharIds, string HexPreview);

    public static double ShannonEntropy(ReadOnlySpan<byte> data)
    {
        if (data.IsEmpty) return 0;
        var freq = new int[256];
        foreach (var b in data)
            freq[b]++;
        double len = data.Length;
        double ent = 0;
        foreach (var c in freq)
        {
            if (c == 0) continue;
            double p = c / len;
            ent -= p * Math.Log2(p);
        }
        return ent;
    }

    public static IEnumerable<(int BankIndex, int RomStart, double Entropy)> BankEntropyMap(SnesRom rom)
    {
        for (int bank = 0; bank < rom.Size; bank += BankSize)
        {
            int len = Math.Min(BankSize, rom.Size - bank);
            yield return (bank / BankSize, bank, ShannonEntropy(rom.Slice(bank, len)));
        }
    }

    public static IEnumerable<Bank84Pointer> EnumerateBank84Pointers(SnesRom rom, int start, int end)
    {
        var data = rom.Data;
        end = Math.Min(end, data.Length - 3);
        for (int i = start; i < end; i++)
        {
            if (data[i + 2] != 0x84)
                continue;
            ushort off = SnesAddress.ParseBank84Pointer(data[i], data[i + 1]);
            uint snes = SnesAddress.Bank84Pointer(off);
            int? ro = SnesAddress.RomOffset(snes);
            if (ro == null)
                continue;
            yield return new Bank84Pointer(i, off, snes);
        }
    }

    public static IEnumerable<ScriptRecord> ParseScriptRecords(SnesRom rom, int start, int end)
    {
        var data = rom.Data;
        int pos = start;
        end = Math.Min(end, data.Length);
        while (pos < end)
        {
            if (data[pos] == 0)
            {
                pos++;
                continue;
            }
            int recordStart = pos;
            var ptrs = new List<Bank84Pointer>();
            if (pos + 2 <= end)
            {
                ushort cmd = (ushort)(data[pos] | (data[pos + 1] << 8));
                pos += 2;
                while (pos + 2 < end && data[pos + 2] == 0x84)
                {
                    ushort off = SnesAddress.ParseBank84Pointer(data[pos], data[pos + 1]);
                    ptrs.Add(new Bank84Pointer(pos, off, SnesAddress.Bank84Pointer(off)));
                    pos += 3;
                }
                if (pos < end && data[pos] == 0)
                    pos++;
                yield return new ScriptRecord(recordStart, cmd, ptrs);
            }
            else
            {
                pos++;
            }
        }
    }

    public static IEnumerable<Text8DString> Find8DPrefixedStrings(SnesRom rom)
    {
        var data = rom.Data;
        for (int i = 0; i < data.Length - 8; i++)
        {
            if (data[i] != 0x8D)
                continue;
            var ids = new List<byte>();
            int p = i;
            while (p + 1 < data.Length && data[p] == 0x8D)
            {
                ids.Add(data[p + 1]);
                p += 2;
            }
            if (ids.Count < 4)
                continue;
            var hex = string.Join(" ", ids.Take(24).Select(b => b.ToString("X2", CultureInfo.InvariantCulture)));
            yield return new Text8DString(i, ids, hex);
            i = p;
        }
    }

    public static IEnumerable<(int RomOffset, byte Value)> ParseFontMetricTable(SnesRom rom, int offset)
    {
        var data = rom.Data;
        int pos = offset;
        while (pos + 2 < data.Length && data[pos] == 0x81 && data[pos + 1] == 0x87)
        {
            yield return (pos, data[pos + 2]);
            pos += 3;
        }
    }

    public static string ToCsvRow(params string[] fields) =>
        string.Join(",", fields.Select(EscapeCsv));

    private static string EscapeCsv(string s)
    {
        if (s.Contains('"') || s.Contains(',') || s.Contains('\n'))
            return $"\"{s.Replace("\"", "\"\"")}\"";
        return s;
    }
}
