using System.Globalization;

namespace NageLibre.Tools.Analysis;

/// <summary>Charge charset_catalog.csv pour résoudre index glyphe → tuile VRAM.</summary>
public sealed class GlyphCatalog
{
    private readonly Dictionary<int, GlyphInfo> _byIndex = new();
    private readonly Dictionary<int, GlyphInfo> _byVramTile = new();

    public sealed record GlyphInfo(int GlyphIndex, int VramTile, int RomOffset, string Category);

    public IEnumerable<GlyphInfo> AllGlyphs => _byVramTile.Values;

    public static GlyphCatalog Load(string csvPath)
    {
        var cat = new GlyphCatalog();
        if (!File.Exists(csvPath))
            return cat;

        foreach (var line in File.ReadLines(csvPath).Skip(1))
        {
            var p = line.Split(',');
            if (p.Length < 5)
                continue;

            int gi = int.Parse(p[1], CultureInfo.InvariantCulture);
            int rom = ParseHex(p[2]);
            int tile = ParseHex(p[3]);
            string category = p[4];

            var info = new GlyphInfo(gi, tile, rom, category);
            cat._byIndex.TryAdd(gi, info);
            cat._byVramTile.TryAdd(tile, info);
        }

        return cat;
    }

    public int? VramTileForGlyphByte(byte b) => b + GameTextCodec.VramTileBias;

    public bool TryGetByGlyphByte(byte b, out GlyphInfo? info)
    {
        int tile = b + GameTextCodec.VramTileBias;
        if (_byVramTile.TryGetValue(tile, out var v))
        {
            info = v;
            return true;
        }
        info = null;
        return false;
    }

    /// <summary>Remplace {XX} par ? si pas de table unicode (à enrichir manuellement).</summary>
    public string ApplyKnownGlyphs(string display, IReadOnlyDictionary<byte, char>? unicodeTable = null)
    {
        if (unicodeTable == null || unicodeTable.Count == 0)
            return display;

        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < display.Length; i++)
        {
            if (display[i] == '{' && i + 2 < display.Length && display[i + 3] == '}')
            {
                if (byte.TryParse(display.AsSpan(i + 1, 2), NumberStyles.HexNumber, null, out byte g)
                    && unicodeTable.TryGetValue(g, out char c))
                {
                    sb.Append(c);
                    i += 3;
                    continue;
                }
            }
            sb.Append(display[i]);
        }
        return sb.ToString();
    }

    private static int ParseHex(string s)
    {
        s = s.Trim();
        if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            s = s[2..];
        return int.Parse(s, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
    }
}
