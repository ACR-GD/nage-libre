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
            $"unique_unicode_chars,{inv.UniqueChars},After partial Unicode mapping (otherwise use glyph_ids)",
            $"hiragana_unique,{inv.Hiragana},Expected ~46-86 if complete",
            $"katakana_unique,{inv.Katakana},Expected ~46-86 if complete",
            $"kanji_unique,{inv.Kanji},Game subset (~{glyphCount} ROM glyphs)",
            $"ascii_unique,{inv.Ascii},Digits / Latin in dialogue",
            $"font_glyphs_rom,{glyphCount},16x16 tiles in ROM",
            "hiragana_complete_in_font,unknown,Check charset_atlas.bmp",
            "katakana_complete_in_font,unknown,Check charset_atlas.bmp",
            "repack_strategy,replace_glyph_bytes_same_length,Keep FF/FE and the byte length",
            "space_saving,remove_kanji_banks,Repoint scripts after removing banks 12-19",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    public static void ExportRomSpaceReport(string path, SnesRom rom)
    {
        var lines = new List<string>
        {
            "region,rom_start,rom_end,size_bytes,freeable_for_translation,notes",
            "font_kanji_banks,0x033010,0x03E700,~45000,true,Banks 14-19 ~dense kanji",
            "font_duplicate_banks,0x050000,0x180000,variable,partial,VRAM tiles also in gfx — careful",
            "script_bank84,0x020000,0x040000,131072,false,Repoint if the text moves",
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
