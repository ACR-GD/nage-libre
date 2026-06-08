using System.Text;
using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Analysis;

public static class TranslationPlanner
{
    public static void ExportStringsForTranslation(string path, IReadOnlyList<DecodedString> strings)
    {
        var lines = new List<string>
        {
            "id,rom_offset,rom_end,encoding,length_bytes,glyph_ids,glyph_display,japanese,english_translation,notes",
        };

        int id = 0;
        foreach (var s in strings)
        {
            id++;
            lines.Add(string.Join(",",
                id.ToString(),
                $"0x{s.RomOffset:X6}",
                $"0x{s.RomOffset + s.Length:X6}",
                s.Encoding.ToString(),
                s.Length.ToString(),
                CsvEscape(s.GlyphIds),
                CsvEscape(s.GlyphDisplay),
                CsvEscape(s.Japanese),
                "",
                CsvEscape(s.Notes ?? "")));
        }

        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    public static void ExportCharacterAnalysis(string path, CharacterInventory inv, int glyphCount)
    {
        var lines = new List<string>
        {
            "metric,value,notes",
            $"unique_unicode_chars,{inv.UniqueChars},Après mapping unicode partiel (sinon utiliser glyph_ids)",
            $"hiragana_unique,{inv.Hiragana},Attendu ~46-86 si complet",
            $"katakana_unique,{inv.Katakana},Attendu ~46-86 si complet",
            $"kanji_unique,{inv.Kanji},Sous-ensemble jeu (~{glyphCount} glyphes ROM)",
            $"ascii_unique,{inv.Ascii},Chiffres / Latin dans dialogue",
            $"font_glyphs_rom,{glyphCount},Tuiles 16x16 en ROM",
            "hiragana_complete_in_font,unknown,Vérifier charset_atlas.bmp",
            "katakana_complete_in_font,unknown,Vérifier charset_atlas.bmp",
            "repack_strategy,replace_glyph_bytes_same_length,Conserver FF/FE et longueur octets",
            "space_saving,remove_kanji_banks,Repointer scripts après suppression banques 12-19",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    public static void ExportRomSpaceReport(string path, SnesRom rom)
    {
        var lines = new List<string>
        {
            "region,rom_start,rom_end,size_bytes,freeable_for_translation,notes",
            "font_kanji_banks,0x033010,0x03E700,~45000,true,Banques 14-19 ~kanji denses",
            "font_duplicate_banks,0x050000,0x180000,variable,partial,VRAM tiles aussi en gfx — prudence",
            "script_bank84,0x020000,0x040000,131072,false,Repointer si texte déplacé",
            "rom_total,0x000000,0x180000,1572864,false,LoROM 1.5MB",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static string CsvEscape(string s)
    {
        if (s.Contains('"') || s.Contains(',') || s.Contains('\n'))
            return $"\"{s.Replace("\"", "\"\"")}\"";
        return s;
    }
}
