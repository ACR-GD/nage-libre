using System.Text;

namespace NageLibre.Tools.Analysis;

/// <summary>
/// Décodeur du texte Nage Libre : index de glyphe (1 octet), pas Shift-JIS.
/// Contrôles : 01 début, 02 pause, 8D/20 glyphe explicite, FF xx fin, FE fin alternative.
/// </summary>
public static class GameTextCodec
{
    public const int VramTileBias = 0xFB;

    public sealed record DecodeResult(
        string Display,
        string GlyphIds,
        int ConsumedBytes,
        bool HasTerminator,
        string? Unicode = null);

    public static DecodeResult Decode(ReadOnlySpan<byte> raw, int maxBytes = 600, GlyphUnicodeTable? unicode = null)
    {
        var display = new StringBuilder();
        var ids = new StringBuilder();
        int i = 0;
        bool terminated = false;

        while (i < raw.Length && i < maxBytes)
        {
            byte b = raw[i];

            if (b == 0xFF && i + 1 < raw.Length)
            {
                display.Append($"[FF{raw[i + 1]:X2}]");
                ids.Append($" FF{raw[i + 1]:X2}");
                i += 2;
                terminated = true;
                break;
            }

            if (b == 0xFE)
            {
                display.Append("[FE]");
                ids.Append(" FE");
                i++;
                terminated = true;
                break;
            }

            if (b == 0)
                break;

            if (b == 0x01)
            {
                display.Append("[01]");
                ids.Append(" 01");
                i++;
                continue;
            }

            if (b == 0x02)
            {
                display.Append('…');
                ids.Append(" 02");
                i++;
                continue;
            }

            if (b == 0x8D && i + 1 < raw.Length)
            {
                byte g = raw[i + 1];
                AppendGlyph(display, ids, g, "8D");
                i += 2;
                continue;
            }

            if (b == 0x20 && i + 2 < raw.Length)
            {
                byte g1 = raw[i + 1];
                byte g2 = raw[i + 2];
                // Souvent 20 XX 96 / 9E : l’index utile est XX (second octet quasi constant).
                byte g = g2 is 0x96 or 0x9E ? g1 : g1;
                AppendGlyph(display, ids, g, $"20{g1:X2}{g2:X2}");
                i += 3;
                continue;
            }

            if (IsLikelyGlyphByte(b))
            {
                AppendGlyph(display, ids, b, null);
                i++;
                continue;
            }

            display.Append($"[{b:X2}]");
            ids.Append($" {b:X2}");
            i++;
        }

        string disp = display.ToString();
        string? uni = unicode?.ToUnicode(disp);
        return new DecodeResult(disp, ids.ToString().Trim(), i, terminated, uni);
    }

    public static bool IsLikelyGlyphByte(byte b) => b is >= 0x08 and not (0x8D or 0xFF or 0xFE);

    public static int ScoreAsText(ReadOnlySpan<byte> raw)
    {
        if (raw.Length < 4 || raw.Length > 400)
            return -1;

        int glyphs = 0, controls = 0, bad = 0;
        int i = 0;
        while (i < raw.Length)
        {
            byte b = raw[i];
            if (b == 0xFF) break;
            if (b is 0x01 or 0x02 or 0xFE) { controls++; i++; continue; }
            if (b == 0x8D && i + 1 < raw.Length) { glyphs++; i += 2; continue; }
            if (b == 0x20 && i + 2 < raw.Length) { glyphs++; i += 3; continue; }
            if (IsLikelyGlyphByte(b)) { glyphs++; i++; continue; }
            if (b < 0x10) bad++;
            i++;
        }

        if (glyphs < 3)
            return -1;

        // Rejeter motifs 65816 fréquents
        if (ContainsPattern(raw, [0xE9, 0x82]) || ContainsPattern(raw, [0x22, 0x65, 0xF1]))
            return -1;

        int zeros = 0;
        foreach (byte b in raw)
            if (b == 0) zeros++;
        if (zeros > 2)
            return -1;

        return glyphs * 10 - bad * 8 - controls;
    }

    private static void AppendGlyph(StringBuilder display, StringBuilder ids, byte g, string? prefix)
    {
        ids.Append(prefix == null ? $" {g:X2}" : $" {prefix}{g:X2}");
        display.Append('{').Append(g.ToString("X2")).Append('}');
    }

    private static bool ContainsPattern(ReadOnlySpan<byte> data, byte[] pat)
    {
        for (int i = 0; i <= data.Length - pat.Length; i++)
        {
            bool ok = true;
            for (int j = 0; j < pat.Length; j++)
            {
                if (data[i + j] != pat[j]) { ok = false; break; }
            }
            if (ok) return true;
        }
        return false;
    }
}
