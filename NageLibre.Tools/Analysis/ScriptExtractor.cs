using System.Text;
using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Analysis;

public sealed record ScriptCommand(
    int RomOffset,
    ushort Opcode,
    IReadOnlyList<uint> Pointers,
    string? LinkedText);

public static class ScriptExtractor
{
    public static IEnumerable<ScriptCommand> ParseScriptRegion(SnesRom rom, int start = 0x20000, int end = 0x35000)
    {
        var data = rom.Data;
        int pos = start;

        while (pos < end - 5)
        {
            if (data[pos] == 0)
            {
                pos++;
                continue;
            }

            int recordStart = pos;
            ushort opcode = (ushort)(data[pos] | (data[pos + 1] << 8));
            pos += 2;

            var ptrs = new List<uint>();
            while (pos + 2 < end)
            {
                byte bank = data[pos + 2];
                if (bank < 0x84 || bank > 0x8F)
                    break;
                ushort off = SnesAddress.ParseBank84Pointer(data[pos], data[pos + 1]);
                uint snesAddr = (uint)((bank << 16) | off);
                if (SnesAddress.RomOffset(snesAddr) == null)
                    break;
                ptrs.Add(snesAddr);
                pos += 3;
            }

            if (data[pos] == 0)
                pos++;

            if (ptrs.Count == 0)
                continue;

            if (opcode is 0xFFFF or 0x0000)
                continue;

            yield return new ScriptCommand(recordStart, opcode, ptrs, null);
        }
    }

    public static void ExportScriptCsv(string path, IEnumerable<ScriptCommand> commands, IReadOnlyList<DecodedString> strings)
    {
        var byRom = strings.ToLookup(s => s.RomOffset);
        var lines = new List<string>
        {
            "rom_offset,opcode_hex,pointer_count,pointers_snes,linked_text_preview",
        };

        foreach (var cmd in commands)
        {
            string ptrs = string.Join(";", cmd.Pointers.Select(p => $"${p:X6}"));
            string? preview = null;
            foreach (var p in cmd.Pointers)
            {
                int? ro = SnesAddress.RomOffset(p);
                if (ro == null) continue;
                var match = byRom[ro.Value].FirstOrDefault();
                if (match != null)
                {
                    preview = match.Japanese.Length > 60
                        ? match.Japanese[..60] + "…"
                        : match.Japanese;
                    break;
                }
            }

            lines.Add($"{cmd.RomOffset:X6},0x{cmd.Opcode:X4},{cmd.Pointers.Count},{ptrs},\"{Escape(preview ?? "")}\"");
        }

        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static string Escape(string s) =>
        s.Replace("\"", "\"\"").Replace("\n", "\\n");
}
