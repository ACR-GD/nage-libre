using System.Globalization;
using System.Text;
using NageLibre.Tools.Gfx;
using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Analysis;

public sealed class GlyphUnicodeTable
{
    public sealed record Entry(
        byte TextByte,
        int VramTile,
        char? Unicode,
        string? Character,
        int? RomOffset,
        string Category,
        string Source,
        ulong? Fingerprint);

    private readonly Dictionary<byte, Entry> _byByte = new();

    public IReadOnlyDictionary<byte, Entry> ByByte => _byByte;

    public static GlyphUnicodeTable Build(SnesRom rom, string charsetCatalogPath)
    {
        var table = new GlyphUnicodeTable();
        var catalogRows = LoadCatalogRows(charsetCatalogPath);
        var romSpan = rom.AsSpan();

        // Regrouper par empreinte bitmap
        var byHash = new Dictionary<ulong, List<CatalogRow>>();
        foreach (var row in catalogRows)
        {
            if (row.RomOffset + Font16x16.CharacterBytes > romSpan.Length)
                continue;
            ulong hash = GlyphFingerprint.Hash64(romSpan.Slice(row.RomOffset, Font16x16.CharacterBytes));
            row.Fingerprint = hash;
            if (!byHash.TryGetValue(hash, out var list))
            {
                list = [];
                byHash[hash] = list;
            }
            list.Add(row);
        }

        // Ancre こ : ROM utilisateur 0x28540 (tolérance ±64)
        ulong? koHash = FindKoAnchorHash(romSpan, byHash);
        if (koHash != null)
        {
            table.MapFingerprintGroup(byHash[koHash.Value], JapaneseSyllabary.KnownKoTextByte,
                JapaneseSyllabary.KnownKoChar, "anchor_ko");
        }
        else
        {
            table.MapByte(JapaneseSyllabary.KnownKoTextByte, JapaneseSyllabary.KnownKoChar,
                JapaneseSyllabary.KnownKoVramTile, JapaneseSyllabary.KnownKoRomOffset,
                "kanji_dense", "anchor_ko_fallback");
        }

        // Gojuon uniquement sur petites banques syllabaires (ROM ~0x28000), pas les banques kanji.
        int[] kanaBankIds = [2, 3, 4, 5, 6, 7];
        foreach (int bankId in kanaBankIds)
        {
            var kanaGlyphs = catalogRows
                .Where(r => r.BankIndex == bankId)
                .Where(r => JapaneseSyllabary.IsKanaLikeCategory(r.Category) || r.InkPixels < 95)
                .OrderBy(r => r.GlyphIndex)
                .ToList();

            if (kanaGlyphs.Count < 8)
                continue;

            bool hiragana = bankId is 2 or 4 or 6;
            string syllabary = hiragana ? JapaneseSyllabary.HiraganaExtended : JapaneseSyllabary.KatakanaExtended;
            string source = hiragana ? $"gojuon_hira_bank{bankId}" : $"gojuon_kata_bank{bankId}";

            int si = 0;
            foreach (var g in kanaGlyphs)
            {
                if (si >= syllabary.Length)
                    break;
                byte textByte = (byte)(g.VramTile - GameTextCodec.VramTileBias);
                char ch = syllabary[si++];
                if (!table._byByte.ContainsKey(textByte))
                    table.MapByte(textByte, ch, g.VramTile, g.RomOffset, g.Category, source);
            }
        }

        // Index complet : chaque glyphe catalogue → octet texte (sans unicode si inconnu)
        foreach (var row in catalogRows)
        {
            byte tb = (byte)(row.VramTile - GameTextCodec.VramTileBias);
            if (!table._byByte.ContainsKey(tb))
                table._byByte[tb] = new Entry(tb, row.VramTile, null, null, row.RomOffset, row.Category, "catalog_index", row.Fingerprint);
        }

        // Doublons visuels : même empreinte → même caractère si déjà connu
        foreach (var (hash, rows) in byHash)
        {
            char? known = null;
            string? src = null;
            foreach (var row in rows)
            {
                byte tb = (byte)(row.VramTile - GameTextCodec.VramTileBias);
                if (table._byByte.TryGetValue(tb, out var e) && e.Unicode != null)
                {
                    known = e.Unicode;
                    src = e.Source + "_dup";
                    break;
                }
            }

            if (known == null)
                continue;

            foreach (var row in rows)
            {
                byte tb = (byte)(row.VramTile - GameTextCodec.VramTileBias);
                if (table._byByte.TryGetValue(tb, out var existing) && existing.Unicode == null)
                    table.MapByte(tb, known.Value, row.VramTile, row.RomOffset, row.Category, src ?? "fingerprint_dup");
            }
        }

        return table;
    }

    private static ulong? FindKoAnchorHash(ReadOnlySpan<byte> rom, Dictionary<ulong, List<CatalogRow>> byHash)
    {
        int[] candidates = [0x28540, 0x285B0, 0x20340];
        foreach (int off in candidates)
        {
            if (off + Font16x16.CharacterBytes > rom.Length)
                continue;
            ulong h = GlyphFingerprint.Hash64(rom.Slice(off, Font16x16.CharacterBytes));
            if (byHash.ContainsKey(h))
                return h;
        }

        ulong? bestHash = null;
        int bestHam = int.MaxValue;
        if (rom.Length > 0x28540 + 64)
        {
            ulong target = GlyphFingerprint.Hash64(rom.Slice(0x28540, Font16x16.CharacterBytes));
            foreach (var (hash, _) in byHash)
            {
                int d = GlyphFingerprint.Hamming(target, hash);
                if (d < bestHam)
                {
                    bestHam = d;
                    bestHash = hash;
                }
            }
            if (bestHam <= 8)
                return bestHash;
        }

        return null;
    }

    private void MapFingerprintGroup(List<CatalogRow> rows, byte textByte, char ch, string source)
    {
        foreach (var row in rows)
        {
            byte tb = (byte)(row.VramTile - GameTextCodec.VramTileBias);
            if (tb == textByte || !_byByte.ContainsKey(tb))
                MapByte(tb, ch, row.VramTile, row.RomOffset, row.Category, source);
        }
        MapByte(textByte, ch, JapaneseSyllabary.KnownKoVramTile, JapaneseSyllabary.KnownKoRomOffset, "kana", source);
    }

    private void MapByte(byte textByte, char ch, int vramTile, int? romOffset, string category, string source)
    {
        _byByte[textByte] = new Entry(textByte, vramTile, ch, ch.ToString(), romOffset, category, source, null);
    }

    public bool TryGetChar(byte textByte, out char ch) 
    {
        if (_byByte.TryGetValue(textByte, out var e) && e.Unicode is char c)
        {
            ch = c;
            return true;
        }
        ch = default;
        return false;
    }

    public string ToUnicode(string glyphDisplay)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < glyphDisplay.Length; i++)
        {
            if (glyphDisplay[i] == '{' && i + 2 < glyphDisplay.Length && glyphDisplay[i + 3] == '}')
            {
                if (byte.TryParse(glyphDisplay.AsSpan(i + 1, 2), NumberStyles.HexNumber, null, out byte g)
                    && TryGetChar(g, out char c))
                {
                    sb.Append(c);
                    i += 3;
                    continue;
                }
                sb.Append('〓');
                i += 3;
                continue;
            }

            if (glyphDisplay[i] == '…')
            {
                sb.Append('…');
                continue;
            }

            if (glyphDisplay[i] == '[')
            {
                int close = glyphDisplay.IndexOf(']', i);
                if (close > i)
                {
                    sb.Append(glyphDisplay.AsSpan(i, close - i + 1));
                    i = close;
                    continue;
                }
            }

            sb.Append(glyphDisplay[i]);
        }
        return sb.ToString();
    }

    public void ExportCsv(string path, bool unicodeMappedOnly = false)
    {
        var lines = new List<string>
        {
            "text_byte_hex,vram_tile_hex,unicode_hex,character,rom_offset,category,mapping_source",
        };

        IEnumerable<Entry> entries = _byByte.Values.OrderBy(x => x.TextByte);
        if (unicodeMappedOnly)
            entries = entries.Where(e => e.Unicode != null);

        foreach (var e in entries)
        {
            string uHex = e.Unicode != null ? $"U+{((int)e.Unicode):X4}" : "";
            lines.Add(string.Join(",",
                $"0x{e.TextByte:X2}",
                $"0x{e.VramTile:X3}",
                uHex,
                CsvEscape(e.Character ?? ""),
                e.RomOffset != null ? $"0x{e.RomOffset:X6}" : "",
                e.Category,
                e.Source));
        }

        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    public void ExportFullIndex(string path) => ExportCsv(path, unicodeMappedOnly: false);

    public static GlyphUnicodeTable Load(string path)
    {
        var table = new GlyphUnicodeTable();
        if (!File.Exists(path))
            return table;

        foreach (var line in File.ReadLines(path).Skip(1))
        {
            var p = ParseCsvLine(line);
            if (p.Length < 7)
                continue;

            byte tb = ParseHexByte(p[0]);
            int tile = ParseHexInt(p[1]);
            char? ch = null;
            if (p[2].StartsWith("U+", StringComparison.OrdinalIgnoreCase))
                ch = (char)int.Parse(p[2][2..], NumberStyles.HexNumber);
            else if (p[3].Length == 1)
                ch = p[3][0];

            table._byByte[tb] = new Entry(tb, tile, ch, p[3], ParseHexOptional(p[4]), p[5], p[6], null);
        }

        return table;
    }

    private sealed class CatalogRow
    {
        public int BankIndex { get; init; }
        public int GlyphIndex { get; init; }
        public int RomOffset { get; init; }
        public int VramTile { get; init; }
        public int InkPixels { get; init; }
        public string Category { get; init; } = "";
        public ulong Fingerprint { get; set; }
    }

    private static List<CatalogRow> LoadCatalogRows(string path)
    {
        var rows = new List<CatalogRow>();
        if (!File.Exists(path))
            return rows;

        foreach (var line in File.ReadLines(path))
        {
            if (line.StartsWith("bank", StringComparison.OrdinalIgnoreCase))
                continue;
            var p = line.TrimStart('\ufeff').Split(',');
            if (p.Length < 6)
                continue;

            rows.Add(new CatalogRow
            {
                BankIndex = int.Parse(p[0], CultureInfo.InvariantCulture),
                GlyphIndex = int.Parse(p[1], CultureInfo.InvariantCulture),
                RomOffset = ParseHexInt(p[2]),
                VramTile = ParseHexInt(p[3]),
                InkPixels = int.Parse(p[4], CultureInfo.InvariantCulture),
                Category = p[5],
            });
        }

        return rows;
    }

    private static string CsvEscape(string s)
    {
        if (s.Contains(',') || s.Contains('"'))
            return $"\"{s.Replace("\"", "\"\"")}\"";
        return s;
    }

    private static string[] ParseCsvLine(string line) => line.Split(',');

    private static byte ParseHexByte(string s)
    {
        s = s.Trim();
        if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            s = s[2..];
        return byte.Parse(s, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
    }

    private static int ParseHexInt(string s)
    {
        s = s.Trim();
        if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            s = s[2..];
        return int.Parse(s, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
    }

    private static int? ParseHexOptional(string s)
    {
        if (string.IsNullOrWhiteSpace(s))
            return null;
        return ParseHexInt(s);
    }
}
