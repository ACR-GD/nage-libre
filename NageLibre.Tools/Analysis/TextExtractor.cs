using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Analysis;

public static class TextExtractor
{
    /// <summary>Zones dialogue (hors table des scripts @ 0x20000).</summary>
    public static readonly (int Start, int End, string Name)[] DialogueRegions =
    [
        (0x22000, 0x38000, "bank84_dialogue"),
        (0x38000, 0x48000, "dialogue_extended"),
    ];

    /// <summary>Bytecode script : ne pas scanner les 01 ici.</summary>
    public const int ScriptTableEnd = 0x22000;

    public static readonly byte[] FfTerminators = [0x05, 0x10, 0x01, 0x02, 0x09, 0x0A];

    public static IReadOnlyList<DecodedString> ExtractAll(SnesRom rom, GlyphCatalog? catalog = null, GlyphUnicodeTable? unicode = null)
    {
        var data = rom.Data;
        var results = new List<DecodedString>();
        var seen = new HashSet<string>();
        _unicodeTable = unicode;

        foreach (var (start, end, region) in DialogueRegions)
        {
            results.AddRange(ExtractFfTerminated(data, start, end, region, seen));
            results.AddRange(ExtractFeTerminated(data, start, end, region, seen));
            results.AddRange(Extract01Prefixed(data, start, end, region, seen));
        }

        // FF/FE dans la banque script mais après la table d’opcodes
        results.AddRange(ExtractFfTerminated(data, 0x20000, ScriptTableEnd, "bank84_early", seen));

        results.AddRange(ExtractFromScriptPointers(rom, seen));
        return PruneSubstrings(results.OrderBy(r => r.RomOffset).ToList());
    }

    private static GlyphUnicodeTable? _unicodeTable;

    /// <summary>Supprime les chaînes strictement incluses dans une autre au même offset ±4.</summary>
    private static List<DecodedString> PruneSubstrings(List<DecodedString> list)
    {
        var keep = new bool[list.Count];
        Array.Fill(keep, true);
        for (int i = 0; i < list.Count; i++)
        {
            for (int j = 0; j < list.Count; j++)
            {
                if (i == j || !keep[i]) continue;
                var a = list[i]; var b = list[j];
                if (a.RomOffset >= b.RomOffset && a.RomOffset + a.Length <= b.RomOffset + b.Length
                    && a.Length < b.Length
                    && Math.Abs(a.RomOffset - b.RomOffset) < 8)
                    keep[i] = false;
            }
        }
        return list.Where((_, i) => keep[i]).ToList();
    }

    /// <summary>Chaînes terminées FF + sous-octet (dialogue script).</summary>
    public static IEnumerable<DecodedString> ExtractFfTerminated(
        byte[] rom, int start, int end, string region, HashSet<string> seen)
    {
        for (int i = start; i < end - 1; i++)
        {
            if (rom[i] != 0xFF || !FfTerminators.Contains(rom[i + 1]))
                continue;

            int termPos = i;
            byte termSub = rom[i + 1];

            int s = termPos - 1;
            while (s > start && rom[s] != 0xFF)
                s--;
            s++;

            var raw = rom.AsSpan(s, termPos - s).ToArray();
            raw = StripLeadingPadding(raw);

            if (TryAddDecoded(results: null, seen, s, raw, termSub, region, TextEncodingKind.CustomGlyphFfTerminated, out var decoded))
                yield return decoded;
        }
    }

    /// <summary>Chaînes terminées par FE (souvent avant FF 10).</summary>
    public static IEnumerable<DecodedString> ExtractFeTerminated(
        byte[] rom, int start, int end, string region, HashSet<string> seen)
    {
        for (int i = start; i < end; i++)
        {
            if (rom[i] != 0xFE)
                continue;

            int e = i;
            int s = e - 1;
            while (s > start && rom[s] is not (0xFF or 0xFE or 0))
                s--;
            s++;

            var raw = rom.AsSpan(s, e - s).ToArray();
            if (GameTextCodec.ScoreAsText(raw) < 25)
                continue;

            if (TryAddDecoded(null, seen, s, raw, 0, region, TextEncodingKind.CustomGlyphFeTerminated, out var decoded))
                yield return decoded;
        }
    }

    /// <summary>Bloc commençant par 01 (marqueur de ligne / boîte de dialogue).</summary>
    public static IEnumerable<DecodedString> Extract01Prefixed(
        byte[] rom, int start, int end, string region, HashSet<string> seen)
    {
        for (int i = start; i < end - 8; i++)
        {
            if (rom[i] != 0x01)
                continue;

            int e = i + 1;
            while (e < Math.Min(i + 400, end))
            {
                if (rom[e] == 0xFE || (rom[e] == 0xFF && e + 1 < end))
                    break;
                if (rom[e] == 0 && e > i + 6)
                    break;
                e++;
            }

            var raw = rom.AsSpan(i, e - i).ToArray();
            if (raw.Length < 8)
                continue;
            if (CountHighGlyphs(raw) < 4)
                continue;
            if (GameTextCodec.ScoreAsText(raw) < 35)
                continue;

            if (TryAddDecoded(null, seen, i, raw, 0, region, TextEncodingKind.CustomGlyphControl, out var decoded))
                yield return decoded;
        }
    }

    /// <summary>Suit les pointeurs des scripts vers les données texte.</summary>
    public static IEnumerable<DecodedString> ExtractFromScriptPointers(SnesRom rom, HashSet<string> seen)
    {
        var data = rom.Data;
        var targets = new HashSet<int>();

        for (int pos = 0x20000; pos < 0x35000 - 3; pos++)
        {
            byte bank = data[pos + 2];
            if (bank < 0x84 || bank > 0x8F)
                continue;
            ushort off = SnesAddress.ParseBank84Pointer(data[pos], data[pos + 1]);
            uint snesAddr = (uint)((bank << 16) | off);
            int? ro = SnesAddress.RomOffset(snesAddr);
            if (ro != null)
                targets.Add(ro.Value);
        }

        foreach (int ro in targets.Order())
        {
            if (ro < 0 || ro >= data.Length - 8)
                continue;

            int len = Math.Min(256, data.Length - ro);
            var span = data.AsSpan(ro, len);
            int score = GameTextCodec.ScoreAsText(span);
            if (score < 25 && CountHighGlyphs(span) < 3)
                continue;

            // Tronquer à FF/FE
            int end = len;
            for (int j = 0; j < len; j++)
            {
                if (data[ro + j] is 0xFE or 0xFF)
                {
                    end = j + (data[ro + j] == 0xFF && j + 1 < len ? 2 : 1);
                    break;
                }
            }

            var raw = data.AsSpan(ro, end).ToArray();
            if (TryAddDecoded(null, seen, ro, raw, 0, "script_pointer", TextEncodingKind.CustomGlyphPointer, out var decoded))
                yield return decoded;
        }
    }

    private static bool TryAddDecoded(
        List<DecodedString>? results,
        HashSet<string> seen,
        int offset,
        byte[] raw,
        byte termSub,
        string region,
        TextEncodingKind kind,
        out DecodedString decoded)
    {
        decoded = null!;
        if (raw.Length < 2)
            return false;

        int score = GameTextCodec.ScoreAsText(raw);
        if (score < 0 && kind != TextEncodingKind.CustomGlyphPointer)
            return false;
        if (CountHighGlyphs(raw) < 2 && kind is TextEncodingKind.CustomGlyphFfTerminated or TextEncodingKind.CustomGlyphFeTerminated)
            return false;

        var dr = GameTextCodec.Decode(raw, unicode: _unicodeTable);
        if (dr.GlyphIds.Length < 6 && kind is TextEncodingKind.CustomGlyphControl or TextEncodingKind.CustomGlyphPointer)
            return false;

        string key = $"{offset:X}:{dr.GlyphIds}";
        if (!seen.Add(key))
            return false;

        string japanese = dr.Unicode ?? dr.Display;
        decoded = new DecodedString(
            offset,
            raw.Length,
            kind,
            japanese,
            raw,
            termSub,
            region,
            dr.GlyphIds,
            dr.Display);

        results?.Add(decoded);
        return true;
    }

    public static CharacterInventory AnalyzeCharacters(IEnumerable<DecodedString> strings)
    {
        int hiragana = 0, katakana = 0, kanji = 0, ascii = 0, other = 0;
        var unique = new HashSet<char>();

        foreach (var s in strings)
        {
            foreach (char c in s.Japanese)
            {
                if (c is '{' or '}' or '…' or '[' or ']')
                    continue;
                if (!unique.Add(c))
                    continue;

                if (c >= '\u3040' && c <= '\u309F') hiragana++;
                else if (c >= '\u30A0' && c <= '\u30FF') katakana++;
                else if (c >= '\u4E00' && c <= '\u9FFF') kanji++;
                else if (c < 128) ascii++;
                else other++;
            }
        }

        return new CharacterInventory(hiragana, katakana, kanji, ascii, other, unique.Count);
    }

    private static int CountHighGlyphs(ReadOnlySpan<byte> raw)
    {
        int n = 0;
        for (int i = 0; i < raw.Length; i++)
        {
            byte b = raw[i];
            if (b is 0x8D or 0x20) { i++; if (b == 0x20) i++; continue; }
            if (b >= 0x80) n++;
        }
        return n;
    }

    private static byte[] StripLeadingPadding(byte[] raw)
    {
        int start = 0;
        while (start + 1 < raw.Length && raw[start] == 0 && raw[start + 1] == 0)
            start += 2;
        return start > 0 && start < raw.Length ? raw.AsSpan(start).ToArray() : raw;
    }
}
