using System.Globalization;
using System.Text;
using NageLibre.Tools.Analysis;
using NageLibre.Tools.Compression;
using NageLibre.Tools.Gfx;
using NageLibre.Tools.Mesen;
using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Export;

public static class CsvExporter
{
    public static void ExportAll(string romPath, string? mssPath, string outputDir)
    {
        Directory.CreateDirectory(outputDir);
        var rom = SnesRom.Load(romPath);
        ExportRomInfo(rom, Path.Combine(outputDir, "rom_info.csv"));
        ExportMemoryMap(rom, Path.Combine(outputDir, "memory_map.csv"));
        ExportBankEntropy(rom, Path.Combine(outputDir, "bank_entropy.csv"));
        ExportCompressionCandidates(rom, Path.Combine(outputDir, "compression_candidates.csv"));
        ExportScriptBank04(rom, Path.Combine(outputDir, "script_events_bank04.csv"));
        ExportText8D(rom, Path.Combine(outputDir, "text_8d_encoding.csv"));
        ExportFontMetrics(rom, Path.Combine(outputDir, "font_metrics.csv"));
        ExportGfxRegions(rom, Path.Combine(outputDir, "gfx_regions.csv"));
        ExportTcrf( Path.Combine(outputDir, "tcrf_notes.csv"));
        if (mssPath != null && File.Exists(mssPath))
        {
            var mss = MesenSaveState.Load(mssPath);
            ExportMesenFields(mss, Path.Combine(outputDir, "mesen_savestate_fields.csv"));
            ExportPalettes(mss, Path.Combine(outputDir, "palettes_from_savestate.csv"));
        }
    }

    private static void ExportRomInfo(SnesRom rom, string path)
    {
        var lines = new List<string>
        {
            "key,value,notes",
            $"title,\"{rom.Header.Title}\",En-tête LoROM @ 0x7FC0",
            $"size_bytes,{rom.Size},1.5 MiB = 24 Mbit",
            $"map_mode,0x{rom.Header.MapMode:X2},Bit0=HiROM (0=LoROM)",
            $"rom_type,0x{rom.Header.RomType:X2},",
            "endianness,little,Adresses 16/24/32 bits en ROM et RAM",
            "text_encoding,custom_compressed,Pas de Shift-JIS brut ; préfixe 0x8D pour quelques chaînes",
            "script_bank,$84,Banque événements / pointeurs (octet tag 0x84)",
            "event_data_rom,0x20000-0x27FFF,Banques 4-5 : scripts et tables (faible entropie)",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportMemoryMap(SnesRom rom, string path)
    {
        var lines = new List<string>
        {
            "region,rom_start,rom_end,snes_bank,notes",
            "code_low,0x00000,0x07FFF,$00-$01,Code 65816 + vecteurs",
            "data_mid,0x20000,0x4FFFF,$04-$09,Scripts / tables (banque tag 0x84)",
            "gfx_high,0x50000,0x17FFFF,$0A-$2F,Tuiles (entropie élevée) ; police en VRAM depuis ROM",
            "header,0x7FC0,0x7FFF,$00,En-tête copie SNES",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportBankEntropy(SnesRom rom, string path)
    {
        var lines = new List<string> { "bank_index,rom_offset,entropy_bits,likely_content" };
        foreach (var (idx, start, ent) in RomAnalyzer.BankEntropyMap(rom))
        {
            string content = ent switch
            {
                < 5.5 => "tables_or_scripts",
                < 7.0 => "mixed_code_data",
                _ => "compressed_or_gfx",
            };
            lines.Add($"{idx},0x{start:X5},{ent:F2},{content}");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportCompressionCandidates(SnesRom rom, string path)
    {
        var lines = new List<string>
        {
            "rom_offset,format,decompressed_size,notes",
            "REM,Utiliser: dotnet run -- decompress <offset>",
        };
        foreach (var c in CompressionScanner.Scan(rom).Take(500))
        {
            lines.Add($"0x{c.RomOffset:X6},{c.Format},{c.DecompressedSize},{c.Notes}");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportScriptBank04(SnesRom rom, string path)
    {
        var lines = new List<string>
        {
            "rom_offset,command_hex,pointer_count,pointers_snes,notes",
        };
        foreach (var rec in RomAnalyzer.ParseScriptRecords(rom, 0x20000, 0x21000).Take(400))
        {
            string ptrs = string.Join(";", rec.Pointers.Select(p => $"${p.SnesAddress:X6}"));
            lines.Add($"0x{rec.RomOffset:X6},0x{rec.Command:X4},{rec.Pointers.Count},{ptrs},Banque $84 script/event");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportText8D(SnesRom rom, string path)
    {
        var lines = new List<string>
        {
            "rom_offset,char_count,char_ids_hex,notes",
            "REM,Format 0x8D id — encodage custom (pas SJIS)",
        };
        foreach (var s in RomAnalyzer.Find8DPrefixedStrings(rom))
        {
            lines.Add($"0x{s.RomOffset:X6},{s.CharIds.Count},{s.HexPreview},Préfixe 0x8D + ID glyphe");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportFontMetrics(SnesRom rom, string path)
    {
        const int tableOffset = 0xAFDD;
        var lines = new List<string>
        {
            "rom_offset,raw_value,notes",
            "REM,Séquence 81 87 XX — métriques police (22 entrées trouvées)",
        };
        foreach (var (off, val) in RomAnalyzer.ParseFontMetricTable(rom, tableOffset))
        {
            lines.Add($"0x{off:X6},0x{val:X2},Possible largeur glyphe ou index tuile");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportGfxRegions(SnesRom rom, string path)
    {
        var lines = new List<string>
        {
            "region,rom_start,rom_end,bpp,notes",
            "font_tiles_vram_match,0x50000,0x17FFFF,2,7445+ tuiles 2bpp 8x8 trouvées aussi en VRAM (savestate)",
            "dialog_box_tiles,VRAM,VRAM,2,Boîte de dialogue = tuiles en VRAM (voir extract)",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportTcrf(string path)
    {
        var lines = new List<string>
        {
            "feature,condition_jp,translation_en,rom_status",
            "hidden_profiles,Anniversaires personnages (voir TCRF),Character profiles,Texte probablement compressé",
            "dev_message,5× 11月25日 (25 nov),Developer birthday easter egg,Pas trouvé en SJIS brut",
            "dev_msg_1,ダメだよ…,Don't set same birthday…,Custom encoding",
            "dev_msg_2,せっかくだから…,Try various birthdays,Custom encoding",
            "dev_msg_3,ぼくの誕生日,It's my birthday,Custom encoding",
            "dev_msg_song,ハッピバースデー,Happy birthday song,Custom encoding",
            "source_url,https://tcrf.net/Nage_Libre,,",
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportMesenFields(MesenSaveState mss, string path)
    {
        var lines = new List<string> { "field_name,size_bytes,notes" };
        foreach (var kv in mss.Fields.OrderBy(k => k.Key))
        {
            string note = kv.Key switch
            {
                "memoryManager.workRam" => "128 KiB WRAM — chercher pointeurs texte",
                "ppu.vram" => "64 KiB VRAM — tuiles et tilemaps",
                "ppu.cgram" => "512 octets — 256 couleurs BGR555",
                _ => "",
            };
            lines.Add($"{kv.Key},{kv.Value.Length},{note}");
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    private static void ExportPalettes(MesenSaveState mss, string path)
    {
        var cgram = mss.Cgram ?? Array.Empty<byte>();
        var lines = new List<string>
        {
            "palette_index,color_index,r,g,b,bgr555_hex,used_in_dialog",
        };
        for (int pal = 0; pal < 16; pal++)
        {
            for (int c = 0; c < 16; c++)
            {
                int idx = (pal * 16 + c) * 2;
                if (idx + 1 >= cgram.Length) break;
                var (r, g, b) = SnesGfx.Bgr555ToRgb(cgram[idx], cgram[idx + 1]);
                int bgr = cgram[idx] | (cgram[idx + 1] << 8);
                bool dialog = pal is 0 or 7 && c is 0 or 1;
                lines.Add($"{pal},{c},{r},{g},{b},0x{bgr:X4},{dialog}");
            }
        }
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }
}
