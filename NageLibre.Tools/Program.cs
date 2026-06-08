using System.Text;
using NageLibre.Tools.Analysis;
using TextEncodingKind = NageLibre.Tools.Analysis.TextEncodingKind;
using NageLibre.Tools.Compression;
using NageLibre.Tools.Export;
using NageLibre.Tools.Gfx;
using NageLibre.Tools.Mesen;
using NageLibre.Tools.Snes;

string romPath = args.Length > 1 && args[0] == "--rom"
    ? args[1]
    : FindRom() ?? throw new FileNotFoundException("ROM .sfc introuvable.");

string? mssPath = args.Length > 2 && args[0] == "--rom"
    ? args[2]
    : Directory.GetFiles(Path.GetDirectoryName(romPath)!, "*.mss").FirstOrDefault();

string outDir = Path.Combine(Path.GetDirectoryName(romPath)!, "docs");
string cmd = args.Length > 0 && args[0] != "--rom" ? args[0] : "help";

switch (cmd)
{
    case "export":
        CsvExporter.ExportAll(romPath, mssPath, outDir);
        Console.WriteLine($"CSV exportés dans : {outDir}");
        break;

    case "decompress":
        if (args.Length < 2)
        {
            Console.WriteLine("Usage: decompress <romOffsetHex>");
            return;
        }
        RunDecompress(romPath, outDir, ParseHex(args[1]));
        break;

    case "decompress-scan":
        RunDecompressScan(romPath, outDir);
        break;

    case "catalog-font":
        RunFontCatalog(romPath, outDir);
        break;

    case "extract-all":
        RunExtractAll(romPath, outDir);
        break;

    case "map-glyphs":
        RunMapGlyphs(romPath, outDir);
        break;

    case "extract-mesen":
        if (mssPath == null)
        {
            Console.WriteLine("Aucun fichier .mss trouvé.");
            return;
        }
        var mss = MesenSaveState.Load(mssPath);
        var baseDir = Path.GetDirectoryName(mssPath)!;
        if (mss.WorkRam != null)
            File.WriteAllBytes(Path.Combine(baseDir, "extracted_wram.bin"), mss.WorkRam);
        if (mss.Vram != null)
            File.WriteAllBytes(Path.Combine(baseDir, "extracted_vram.bin"), mss.Vram);
        if (mss.Cgram != null)
            File.WriteAllBytes(Path.Combine(baseDir, "extracted_cgram.bin"), mss.Cgram);
        Console.WriteLine("WRAM / VRAM / CGRAM extraits.");
        break;

    case "tile":
        if (args.Length < 3)
        {
            Console.WriteLine("Usage: tile <romOffsetHex> <2|4>");
            return;
        }
        int tileOff = ParseHex(args[1]);
        int bpp = int.Parse(args[2]);
        var rom2 = SnesRom.Load(romPath);
        var tileData = rom2.AsSpan().Slice(tileOff, bpp == 2 ? 16 : 32);
        var indices = bpp == 2
            ? SnesGfx.Decode2BppTile8x8(tileData)
            : SnesGfx.Decode4BppTile8x8(tileData);
        var pal = Enumerable.Range(0, bpp == 2 ? 4 : 16)
            .Select(i => ((byte)(i * 60), (byte)(i * 60), (byte)(i * 60))).ToList();
        Directory.CreateDirectory(outDir);
        string bmp = Path.Combine(outDir, $"tile_{tileOff:X6}.bmp");
        SnesGfx.ExportIndexedBmp(bmp, indices, 8, 8, pal);
        Console.WriteLine($"Tuile → {bmp}");
        break;

    case "font-char":
        if (args.Length < 2)
        {
            Console.WriteLine("Usage: font-char <romOffsetHex>");
            return;
        }
        int charOff = ParseHex(args[1]);
        var rom3 = SnesRom.Load(romPath);
        var block = rom3.AsSpan().Slice(charOff, Font16x16.CharacterBytes);
        var px = Font16x16.ToIndexedBitmap16x16(block);
        
        Console.WriteLine($"=== ROM OFFSET 0x{charOff:X6} ===");
        for (int y = 0; y < 16; y++)
        {
            for (int x = 0; x < 16; x++)
            {
                byte pixel = px[y * 16 + x];
                Console.Write(pixel > 0 ? "█" : ".");
            }
            Console.WriteLine();
        }
        
        var pal16 = new (byte, byte, byte)[] { (0, 0, 0), (90, 90, 90), (180, 180, 180), (255, 255, 255) };
        Directory.CreateDirectory(outDir);
        string bmp16 = Path.Combine(outDir, $"font16_{charOff:X6}.bmp");
        SnesGfx.ExportIndexedBmp(bmp16, px, 16, 16, pal16);
        Console.WriteLine($"Glyphe 16×16 → {bmp16}");
        break;

    case "ascii-grid":
        RunAsciiGrid(romPath, outDir);
        break;

    case "compact-grid":
        RunCompactGrid(romPath, outDir);
        break;

    case "html-grid":
        RunHtmlGrid(romPath, outDir);
        break;

    case "vram-grid":
        RunVramGrid(Path.Combine(Path.GetDirectoryName(romPath)!, "extracted_vram.bin"), outDir);
        break;

    case "compact-vram":
        RunCompactVram(Path.Combine(Path.GetDirectoryName(romPath)!, "extracted_vram.bin"), outDir, Path.Combine(outDir, "glyph_unicode.csv"));
        break;

    case "html-vram-grid":
        RunHtmlVramGrid(Path.Combine(Path.GetDirectoryName(romPath)!, "extracted_vram.bin"), outDir, Path.Combine(outDir, "glyph_unicode.csv"));
        break;

    case "dialogue-font":
        if (args.Length < 4)
        {
            Console.WriteLine("Usage: dialogue-font <topOffsetHex> <bottomOffsetHex> <count>");
            return;
        }
        int topOff = ParseHex(args[1]);
        int bottomOff = ParseHex(args[2]);
        int count = int.Parse(args[3]);
        RunDialogueFont(romPath, outDir, topOff, bottomOff, count);
        break;

    case "find-tile":
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Usage: find-tile <vramTileHex>");
                return;
            }
            int vramTileIndex = ParseHex(args[1]);
            string vramFile = Path.Combine(Path.GetDirectoryName(romPath)!, "extracted_vram.bin");
            if (!File.Exists(vramFile))
            {
                Console.WriteLine("extracted_vram.bin introuvable.");
                return;
            }
            var vramData = File.ReadAllBytes(vramFile);
            int tilesetBaseAddr = 0x5000 * 2;
            int tileOffsetInVram = tilesetBaseAddr + vramTileIndex * 16;
            if (tileOffsetInVram + 16 > vramData.Length)
            {
                Console.WriteLine("Tile index out of VRAM bounds.");
                return;
            }
            var targetTile = vramData.AsSpan(tileOffsetInVram, 16);
            Console.WriteLine($"Recherche de la tuile VRAM 0x{vramTileIndex:X3} (offset VRAM 0x{tileOffsetInVram:X4}):");
            Console.WriteLine(string.Join(" ", targetTile.ToArray().Select(b => b.ToString("X2"))));

            var romBytes = File.ReadAllBytes(romPath);
            int matchCount = 0;
            for (int offset = 0; offset <= romBytes.Length - 16; offset++)
            {
                if (romBytes.AsSpan(offset, 16).SequenceEqual(targetTile))
                {
                    Console.WriteLine($"Match trouvé à l'offset ROM: 0x{offset:X6}");
                    matchCount++;
                }
            }
            if (matchCount == 0)
            {
                Console.WriteLine("Aucun match trouvé dans la ROM.");
            }
            break;
        }

    case "help":
    default:
        Console.WriteLine("""
            Nage Libre — outils ROM SNES (LoROM)

            export                 Génère les CSV dans docs/
            catalog-font           Catalogue glyphes + atlas BMP + résumé traduction
            extract-all            Extrait texte + script → CSV (sans jouer)
            map-glyphs             Table octet → Unicode (glyph_unicode.csv)
            decompress <hex>       Décompresse LZ01/LZ10/LZ11/LZ12 à l'offset ROM
            decompress-scan        Liste les blocs décompressables (CSV)
            extract-mesen          WRAM / VRAM / CGRAM depuis .mss
            tile <hex> <2|4>       Tuile 8×8 en BMP
            font-char <hex>        Glyphe 16×16 (64 octets ROM)
            ascii-grid             Génère docs/ascii_glyphs.txt avec les glyphes en ASCII art
            compact-grid           Génère docs/compact_glyphs.txt avec les glyphes 8x16 de façon compacte
            html-grid              Génère docs/glyph_grid.html avec tous les glyphes agrandis en SVG
            vram-grid              Génère docs/vram_ascii_glyphs.txt à partir de extracted_vram.bin
            compact-vram           Génère docs/compact_vram_glyphs.txt avec les glyphes actifs VRAM 8x16 compacts
            html-vram-grid         Génère docs/glyph_vram_grid.html avec tous les glyphes actifs et complets VRAM
            dialogue-font <t> <b>  Génère docs/dialogue_font_<offset>.txt avec la police dialogue séparée (top/bottom)

            Options : --rom <fichier.sfc> [fichier.mss]
            """);
        break;
}

static void RunDecompress(string romPath, string outDir, int off)
{
    var rom = SnesRom.Load(romPath);
    var attempt = Decompressor.TryAt(rom.AsSpan(), off);
    if (attempt == null)
    {
        Console.WriteLine("Échec — formats testés : LZ01, LZ10, LZ11, LZ12.");
        return;
    }
    Directory.CreateDirectory(outDir);
    string outPath = Path.Combine(outDir, $"decompressed_{off:X6}.bin");
    File.WriteAllBytes(outPath, attempt.Data);
    int glyphs = Decompressor.CountGlyphBlocks(attempt.Data);
    Console.WriteLine($"{attempt.Format} @ 0x{off:X} → {outPath}");
    Console.WriteLine($"  {attempt.Data.Length} octets, score={attempt.Score}, glyphes~{glyphs}");
}

static void RunDecompressScan(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    Directory.CreateDirectory(outDir);
    var path = Path.Combine(outDir, "decompression_scan.csv");
    var lines = new List<string>
    {
        "rom_offset,format,decompressed_size,score,glyph_blocks,contains_ko",
    };

    foreach (var a in Decompressor.Scan(rom.Data, minSize: 128, maxResults: 2000))
    {
        int glyphs = Decompressor.CountGlyphBlocks(a.Data);
        bool ko = Decompressor.ContainsGlyphBlock(a.Data);
        lines.Add($"0x{a.RomOffset:X6},{a.Format},{a.Data.Length},{a.Score},{glyphs},{ko}");
    }

    File.WriteAllLines(path, lines);
    Console.WriteLine($"Scan : {lines.Count - 1} blocs → {path}");
}

static void RunMapGlyphs(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    Directory.CreateDirectory(outDir);

    string catalogPath = Path.Combine(outDir, "charset_catalog.csv");
    if (!File.Exists(catalogPath))
    {
        Console.WriteLine("charset_catalog.csv absent — lancez catalog-font d'abord.");
        return;
    }

    var table = GlyphUnicodeTable.Build(rom, catalogPath);
    string outPath = Path.Combine(outDir, "glyph_unicode.csv");
    string fullPath = Path.Combine(outDir, "glyph_index.csv");
    table.ExportCsv(outPath, unicodeMappedOnly: true);
    table.ExportFullIndex(fullPath);

    int mapped = table.ByByte.Count(e => e.Value.Unicode != null);
    int total = table.ByByte.Count;
    Console.WriteLine($"Unicode : {mapped} octets avec caractère → {outPath}");
    Console.WriteLine($"Index complet : {total} octets (remplir unicode dans glyph_index.csv) → {fullPath}");
    Console.WriteLine($"  Dans game_strings.csv : 〓 = octet sans unicode encore assigné");
}

static void RunExtractAll(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    Directory.CreateDirectory(outDir);

    var catalogPath = Path.Combine(outDir, "charset_catalog.csv");
    var catalog = GlyphCatalog.Load(catalogPath);

    string unicodePath = Path.Combine(outDir, "glyph_unicode.csv");
    GlyphUnicodeTable unicode;
    if (File.Exists(unicodePath))
        unicode = GlyphUnicodeTable.Load(unicodePath);
    else if (File.Exists(catalogPath))
    {
        unicode = GlyphUnicodeTable.Build(rom, catalogPath);
        unicode.ExportCsv(unicodePath);
        Console.WriteLine($"glyph_unicode.csv généré ({unicode.ByByte.Count} entrées).");
    }
    else
    {
        unicode = new GlyphUnicodeTable();
        Console.WriteLine("Astuce : catalog-font puis map-glyphs pour plus de caractères.");
    }

    var strings = TextExtractor.ExtractAll(rom, catalog, unicode);
    var inv = TextExtractor.AnalyzeCharacters(strings);

    TranslationPlanner.ExportStringsForTranslation(
        Path.Combine(outDir, "game_strings.csv"), strings);
    TranslationPlanner.ExportCharacterAnalysis(
        Path.Combine(outDir, "character_analysis.csv"), inv, 1381);
    TranslationPlanner.ExportRomSpaceReport(
        Path.Combine(outDir, "translation_space.csv"), rom);

    var commands = ScriptExtractor.ParseScriptRegion(rom).ToList();
    ScriptExtractor.ExportScriptCsv(
        Path.Combine(outDir, "script_commands.csv"), commands, strings);

    Console.WriteLine($"Chaînes extraites : {strings.Count}");
    Console.WriteLine($"  FF-term      : {strings.Count(s => s.Encoding == TextEncodingKind.CustomGlyphFfTerminated)}");
    Console.WriteLine($"  FE-term      : {strings.Count(s => s.Encoding == TextEncodingKind.CustomGlyphFeTerminated)}");
    Console.WriteLine($"  01-control   : {strings.Count(s => s.Encoding == TextEncodingKind.CustomGlyphControl)}");
    Console.WriteLine($"  via pointer  : {strings.Count(s => s.Encoding == TextEncodingKind.CustomGlyphPointer)}");
    Console.WriteLine($"Unicode : {inv.Hiragana} hiragana, {inv.Katakana} katakana, {inv.Kanji} kanji uniques");
    Console.WriteLine($"Commandes script : {commands.Count}");
    Console.WriteLine($"→ game_strings.csv, script_commands.csv, glyph_unicode.csv, character_analysis.csv");
}

static void RunFontCatalog(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    Directory.CreateDirectory(outDir);

    var banks = CharsetAnalyzer.FindFontBanks(rom.AsSpan());
    var entries = CharsetAnalyzer.CatalogGlyphs(rom, banks).ToList();

    CharsetAnalyzer.ExportCatalogCsv(Path.Combine(outDir, "charset_catalog.csv"), entries);
    CharsetAnalyzer.ExportSummaryCsv(Path.Combine(outDir, "charset_summary.csv"), banks, entries);
    CharsetAnalyzer.ExportAtlas(Path.Combine(outDir, "charset_atlas.bmp"), rom, banks);

    Console.WriteLine($"Banques police : {banks.Count}");
    Console.WriteLine($"Glyphes catalogués : {entries.Count}");
    Console.WriteLine($"  sparse          : {entries.Count(e => e.Category == "sparse")}");
    Console.WriteLine($"  syllabary_latin : {entries.Count(e => e.Category == "syllabary_latin")}");
    Console.WriteLine($"  kana_kanji_light: {entries.Count(e => e.Category == "kana_kanji_light")}");
    Console.WriteLine($"  kanji_dense     : {entries.Count(e => e.Category == "kanji_dense")}");
    Console.WriteLine($"Fichiers : charset_catalog.csv, charset_summary.csv, charset_atlas.bmp");
}

static void RunAsciiGrid(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    string indexPath = Path.Combine(outDir, "glyph_index.csv");
    if (!File.Exists(indexPath))
    {
        Console.WriteLine("glyph_index.csv non trouvé.");
        return;
    }

    var lines = File.ReadAllLines(indexPath).Skip(1);
    var sb = new StringBuilder();
    foreach (var line in lines)
    {
        var p = line.Split(',');
        if (p.Length < 5) continue;
        string byteHex = p[0];
        string vramTile = p[1];
        string unicodeHex = p[2];
        string character = p[3];
        string romOffsetStr = p[4];
        
        if (string.IsNullOrEmpty(romOffsetStr)) continue;
        
        int offset = ParseHex(romOffsetStr);
        if (offset + Font16x16.CharacterBytes > rom.Data.Length) continue;

        var block = rom.AsSpan().Slice(offset, Font16x16.CharacterBytes);
        var pixels = Font16x16.ToIndexedBitmap16x16(block);

        sb.AppendLine($"=== BYTE {byteHex} | VRAM {vramTile} | ROM {romOffsetStr} | CHAR '{character}' ===");
        for (int y = 0; y < 16; y++)
        {
            for (int x = 0; x < 16; x++)
            {
                byte px = pixels[y * 16 + x];
                sb.Append(px > 0 ? "█" : ".");
            }
            sb.AppendLine();
        }
        sb.AppendLine();
    }

    string txtPath = Path.Combine(outDir, "ascii_glyphs.txt");
    File.WriteAllText(txtPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"Grid ASCII générée dans : {txtPath}");
}

static void RunCompactGrid(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    string indexPath = Path.Combine(outDir, "glyph_index.csv");
    if (!File.Exists(indexPath))
    {
        Console.WriteLine("glyph_index.csv non trouvé.");
        return;
    }

    var lines = File.ReadAllLines(indexPath).Skip(1).ToList();
    var glyphs = new List<(byte TextByte, string VramTile, string Character, string RomOffsetStr, byte[] Pixels)>();
    foreach (var line in lines)
    {
        var p = line.Split(',');
        if (p.Length < 5) continue;
        string byteHex = p[0];
        string vramTile = p[1];
        string character = p[3];
        string romOffsetStr = p[4];
        
        if (string.IsNullOrEmpty(romOffsetStr)) continue;
        
        int offset = ParseHex(romOffsetStr);
        if (offset + Font16x16.CharacterBytes > rom.Data.Length) continue;

        var block = rom.AsSpan().Slice(offset, Font16x16.CharacterBytes);
        var pixels = Font16x16.ToIndexedBitmap16x16(block);
        byte textByte = (byte)Convert.ToInt32(byteHex.Replace("0x", "", StringComparison.OrdinalIgnoreCase), 16);
        glyphs.Add((textByte, vramTile, character, romOffsetStr, pixels));
    }

    glyphs = glyphs.OrderBy(g => g.TextByte).ToList();

    var sb = new StringBuilder();
    int groupSize = 8;
    for (int i = 0; i < glyphs.Count; i += groupSize)
    {
        var group = glyphs.Skip(i).Take(groupSize).ToList();
        sb.AppendLine($"=== BYTES 0x{group[0].TextByte:X2} to 0x{group[^1].TextByte:X2} ===");
        
        var byteHeader = string.Join(" | ", group.Select(g => $"  0x{g.TextByte:X2}  "));
        sb.AppendLine(byteHeader);
        
        var charHeader = string.Join(" | ", group.Select(g => {
            string c = string.IsNullOrEmpty(g.Character) ? " " : g.Character;
            return $"  '{c}'   ";
        }));
        sb.AppendLine(charHeader);
        sb.AppendLine(new string('-', byteHeader.Length));

        for (int y = 0; y < 16; y++)
        {
            var rowParts = new List<string>();
            foreach (var g in group)
            {
                var rowChars = new char[8];
                for (int x = 0; x < 8; x++)
                {
                    byte px = g.Pixels[y * 16 + x];
                    rowChars[x] = px > 0 ? '█' : '.';
                }
                rowParts.Add(new string(rowChars));
            }
            sb.AppendLine(string.Join(" | ", rowParts));
        }
        sb.AppendLine();
    }

    string txtPath = Path.Combine(outDir, "compact_glyphs.txt");
    File.WriteAllText(txtPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"Grid compacte ASCII générée dans : {txtPath}");
}


static void RunHtmlGrid(string romPath, string outDir)
{
    var rom = SnesRom.Load(romPath);
    string indexPath = Path.Combine(outDir, "glyph_index.csv");
    if (!File.Exists(indexPath))
    {
        Console.WriteLine("glyph_index.csv non trouvé.");
        return;
    }

    var lines = File.ReadAllLines(indexPath).Skip(1);
    var sb = new StringBuilder();
    sb.Append("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Nage Libre Character Atlas Review</title>
<style>
body {
    background: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 20px;
}
h1 {
    text-align: center;
    color: #fff;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 15px;
    margin-top: 20px;
}
.card {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    transition: transform 0.2s, border-color 0.2s;
}
.card:hover {
    transform: scale(1.05);
    border-color: #555;
}
.glyph {
    image-rendering: pixelated;
    image-rendering: crisp-edges;
    width: 64px;
    height: 64px;
    background: #000;
    border: 1px solid #444;
    margin-bottom: 8px;
}
.info {
    font-size: 0.85em;
    text-align: center;
    width: 100%;
}
.byte {
    font-weight: bold;
    color: #4fc3f7;
}
.char {
    font-size: 1.2em;
    color: #a5d6a7;
    margin: 4px 0;
    min-height: 1.2em;
}
.offset {
    color: #888;
    font-family: monospace;
    font-size: 0.8em;
}
</style>
</head>
<body>
<h1>Nage Libre Glyph Atlas Review</h1>
<div class="grid">
""");

    foreach (var line in lines)
    {
        var p = line.Split(',');
        if (p.Length < 5) continue;
        string byteHex = p[0];
        string vramTile = p[1];
        string unicodeHex = p[2];
        string character = p[3];
        string romOffsetStr = p[4];
        
        if (string.IsNullOrEmpty(romOffsetStr)) continue;
        
        int offset = ParseHex(romOffsetStr);
        if (offset + Font16x16.CharacterBytes > rom.Data.Length) continue;

        var block = rom.AsSpan().Slice(offset, Font16x16.CharacterBytes);
        var pixels = Font16x16.ToIndexedBitmap16x16(block);

        var svgBuilder = new StringBuilder();
        svgBuilder.Append("<svg viewBox='0 0 16 16' class='glyph'>");
        svgBuilder.Append("<rect width='16' height='16' fill='#000000'/>");
        for (int y = 0; y < 16; y++)
        {
            for (int x = 0; x < 16; x++)
            {
                byte px = pixels[y * 16 + x];
                if (px > 0)
                {
                    string color = px switch
                    {
                        1 => "#555555",
                        2 => "#aaaaaa",
                        3 => "#ffffff",
                        _ => "#ffffff"
                    };
                    svgBuilder.Append($"<rect x='{x}' y='{y}' width='1' height='1' fill='{color}'/>");
                }
            }
        }
        svgBuilder.Append("</svg>");

        sb.Append($"""
  <div class="card">
    {svgBuilder.ToString()}
    <div class="info">
      <div class="byte">{byteHex} ({vramTile})</div>
      <div class="char">'{character}'</div>
      <div class="offset">{romOffsetStr}</div>
    </div>
  </div>

""");
    }

    sb.Append("""
</div>
</body>
</html>
""");

    string htmlPath = Path.Combine(outDir, "glyph_grid.html");
    File.WriteAllText(htmlPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"HTML grid généré dans : {htmlPath}");
}

static string? FindRom()
{
    foreach (var dir in new[] { Directory.GetCurrentDirectory(), Path.Combine(Directory.GetCurrentDirectory(), "..") })
    {
        if (!Directory.Exists(dir)) continue;
        var rom = Directory.GetFiles(dir, "*.sfc").FirstOrDefault();
        if (rom != null) return Path.GetFullPath(rom);
    }
    return null;
}

static int ParseHex(string s) =>
    Convert.ToInt32(s.Replace("0x", "", StringComparison.OrdinalIgnoreCase), 16);

static void RunVramGrid(string vramPath, string outDir)
{
    if (!File.Exists(vramPath))
    {
        Console.WriteLine($"Fichier VRAM introuvable : {vramPath}");
        return;
    }
    var vram = File.ReadAllBytes(vramPath);
    var sb = new StringBuilder();
    int tilesetBase = 0x5000 * 2; // 0xA000
    
    for (int idx = 0; idx < 256; idx++)
    {
        int baseTile = 0xFB + idx;
        byte[] glyph = new byte[16 * 16];
        int[] quads = { 0, 1, 16, 17 };
        
        for (int q = 0; q < 4; q++)
        {
            int qx = (q % 2) * 8;
            int qy = (q / 2) * 8;
            int tileIndex = baseTile + quads[q];
            int tileOffset = tilesetBase + tileIndex * 16;
            
            if (tileOffset + 16 <= vram.Length)
            {
                var tileSpan = vram.AsSpan(tileOffset, 16);
                var decoded = SnesGfx.Decode2BppTile8x8(tileSpan);
                for (int y = 0; y < 8; y++)
                for (int x = 0; x < 8; x++)
                    glyph[(qy + y) * 16 + (qx + x)] = decoded[y * 8 + x];
            }
        }
        
        sb.AppendLine($"=== BYTE 0x{idx:X2} | VRAM 0x{baseTile:X3} ===");
        for (int y = 0; y < 16; y++)
        {
            for (int x = 0; x < 16; x++)
            {
                byte px = glyph[y * 16 + x];
                sb.Append(px > 0 ? "█" : ".");
            }
            sb.AppendLine();
        }
        sb.AppendLine();
    }
    
    Directory.CreateDirectory(outDir);
    string txtPath = Path.Combine(outDir, "vram_ascii_glyphs.txt");
    File.WriteAllText(txtPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"Grid VRAM ASCII générée dans : {txtPath}");
}

static void RunCompactVram(string vramPath, string outDir, string unicodePath)
{
    if (!File.Exists(vramPath))
    {
        Console.WriteLine($"Fichier VRAM introuvable : {vramPath}");
        return;
    }
    var vram = File.ReadAllBytes(vramPath);
    var unicode = GlyphUnicodeTable.Load(unicodePath);
    int tilesetBase = 0x5000 * 2; // 0xA000

    var glyphs = new List<(byte TextByte, string Character, byte[] Pixels)>();
    for (int idx = 0; idx < 256; idx++)
    {
        int baseTile = 0xFB + idx;
        byte[] glyph = new byte[16 * 16];
        int[] quads = { 0, 1, 16, 17 };
        
        for (int q = 0; q < 4; q++)
        {
            int qx = (q % 2) * 8;
            int qy = (q / 2) * 8;
            int tileIndex = baseTile + quads[q];
            int tileOffset = tilesetBase + tileIndex * 16;
            
            if (tileOffset + 16 <= vram.Length)
            {
                var tileSpan = vram.AsSpan(tileOffset, 16);
                var decoded = SnesGfx.Decode2BppTile8x8(tileSpan);
                for (int y = 0; y < 8; y++)
                for (int x = 0; x < 8; x++)
                    glyph[(qy + y) * 16 + (qx + x)] = decoded[y * 8 + x];
            }
        }

        string character = "";
        if (unicode.TryGetChar((byte)idx, out char ch))
        {
            character = ch.ToString();
        }

        glyphs.Add(((byte)idx, character, glyph));
    }

    var sb = new StringBuilder();
    int groupSize = 8;
    for (int i = 0; i < glyphs.Count; i += groupSize)
    {
        var group = glyphs.Skip(i).Take(groupSize).ToList();
        sb.AppendLine($"=== BYTES 0x{group[0].TextByte:X2} to 0x{group[^1].TextByte:X2} ===");
        
        var byteHeader = string.Join(" | ", group.Select(g => $"  0x{g.TextByte:X2}  "));
        sb.AppendLine(byteHeader);
        
        var charHeader = string.Join(" | ", group.Select(g => {
            string c = string.IsNullOrEmpty(g.Character) ? " " : g.Character;
            return $"  '{c}'   ";
        }));
        sb.AppendLine(charHeader);
        sb.AppendLine(new string('-', byteHeader.Length));

        for (int y = 0; y < 16; y++)
        {
            var rowParts = new List<string>();
            foreach (var g in group)
            {
                var rowChars = new char[8];
                for (int x = 0; x < 8; x++)
                {
                    byte px = g.Pixels[y * 16 + x];
                    rowChars[x] = px > 0 ? '█' : '.';
                }
                rowParts.Add(new string(rowChars));
            }
            sb.AppendLine(string.Join(" | ", rowParts));
        }
        sb.AppendLine();
    }

    Directory.CreateDirectory(outDir);
    string txtPath = Path.Combine(outDir, "compact_vram_glyphs.txt");
    File.WriteAllText(txtPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"Grid compacte VRAM ASCII générée dans : {txtPath}");
}

static void RunHtmlVramGrid(string vramPath, string outDir, string unicodePath)
{
    if (!File.Exists(vramPath))
    {
        Console.WriteLine($"Fichier VRAM introuvable : {vramPath}");
        return;
    }
    var vram = File.ReadAllBytes(vramPath);
    var unicode = GlyphUnicodeTable.Load(unicodePath);
    int tilesetBase = 0x5000 * 2; // 0xA000
    
    var sb = new StringBuilder();
    sb.Append("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Nage Libre VRAM Character Atlas Review</title>
<style>
body {
    background: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 20px;
}
h1 {
    text-align: center;
    color: #fff;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 15px;
    margin-top: 20px;
}
.card {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    transition: transform 0.2s, border-color 0.2s;
}
.card:hover {
    transform: scale(1.05);
    border-color: #555;
}
.glyph-container {
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
}
.glyph {
    image-rendering: pixelated;
    image-rendering: crisp-edges;
    width: 32px;
    height: 64px;
    background: #000;
    border: 1px solid #444;
}
.glyph-full {
    width: 64px;
    height: 64px;
}
.info {
    font-size: 0.85em;
    text-align: center;
    width: 100%;
}
.byte {
    font-weight: bold;
    color: #4fc3f7;
}
.char {
    font-size: 1.5em;
    color: #a5d6a7;
    margin: 4px 0;
    min-height: 1.2em;
    font-family: 'Courier New', Courier, monospace;
}
</style>
</head>
<body>
<h1>Nage Libre VRAM Glyph Atlas Review (Active 8x16 & Full 16x16)</h1>
<div class="grid">
""");

    for (int idx = 0; idx < 256; idx++)
    {
        int baseTile = 0xFB + idx;
        byte[] glyph = new byte[16 * 16];
        int[] quads = { 0, 1, 16, 17 };
        
        for (int q = 0; q < 4; q++)
        {
            int qx = (q % 2) * 8;
            int qy = (q / 2) * 8;
            int tileIndex = baseTile + quads[q];
            int tileOffset = tilesetBase + tileIndex * 16;
            
            if (tileOffset + 16 <= vram.Length)
            {
                var tileSpan = vram.AsSpan(tileOffset, 16);
                var decoded = SnesGfx.Decode2BppTile8x8(tileSpan);
                for (int y = 0; y < 8; y++)
                for (int x = 0; x < 8; x++)
                    glyph[(qy + y) * 16 + (qx + x)] = decoded[y * 8 + x];
            }
        }

        string character = "";
        if (unicode.TryGetChar((byte)idx, out char ch))
        {
            character = ch.ToString();
        }

        // Generate 8x16 active glyph SVG (left 8 columns)
        var svgActive = new StringBuilder();
        svgActive.Append("<svg viewBox='0 0 8 16' class='glyph'>");
        svgActive.Append("<rect width='8' height='16' fill='#000000'/>");
        for (int y = 0; y < 16; y++)
        {
            for (int x = 0; x < 8; x++)
            {
                byte px = glyph[y * 16 + x];
                if (px > 0)
                {
                    string color = px switch
                    {
                        1 => "#555555",
                        2 => "#aaaaaa",
                        3 => "#ffffff",
                        _ => "#ffffff"
                    };
                    svgActive.Append($"<rect x='{x}' y='{y}' width='1' height='1' fill='{color}'/>");
                }
            }
        }
        svgActive.Append("</svg>");

        // Generate 16x16 full glyph SVG
        var svgFull = new StringBuilder();
        svgFull.Append("<svg viewBox='0 0 16 16' class='glyph glyph-full'>");
        svgFull.Append("<rect width='16' height='16' fill='#000000'/>");
        for (int y = 0; y < 16; y++)
        {
            for (int x = 0; x < 16; x++)
            {
                byte px = glyph[y * 16 + x];
                if (px > 0)
                {
                    string color = px switch
                    {
                        1 => "#555555",
                        2 => "#aaaaaa",
                        3 => "#ffffff",
                        _ => "#ffffff"
                    };
                    svgFull.Append($"<rect x='{x}' y='{y}' width='1' height='1' fill='{color}'/>");
                }
            }
        }
        svgFull.Append("</svg>");

        sb.Append($"""
  <div class="card">
    <div class="glyph-container">
      {svgActive.ToString()}
      {svgFull.ToString()}
    </div>
    <div class="info">
      <div class="byte">0x{idx:X2} (VRAM {baseTile:X3})</div>
      <div class="char">'{character}'</div>
    </div>
  </div>

""");
    }

    sb.Append("""
</div>
</body>
</html>
""");

    string htmlPath = Path.Combine(outDir, "glyph_vram_grid.html");
    File.WriteAllText(htmlPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"HTML grid VRAM généré dans : {htmlPath}");
}

static void RunDialogueFont(string romPath, string outDir, int topOff, int bottomOff, int count)
{
    var rom = SnesRom.Load(romPath);
    var sb = new StringBuilder();
    sb.AppendLine($"=== DIALOGUE FONT: TOP 0x{topOff:X6}, BOTTOM 0x{bottomOff:X6}, COUNT {count} ===");
    sb.AppendLine();

    for (int idx = 0; idx < count; idx++)
    {
        int tOff = topOff + idx * 16;
        int bOff = bottomOff + idx * 16;
        
        if (tOff + 16 > rom.Data.Length || bOff + 16 > rom.Data.Length)
        {
            Console.WriteLine($"Out of ROM bounds at index {idx}");
            break;
        }

        var topTile = rom.AsSpan().Slice(tOff, 16);
        var bottomTile = rom.AsSpan().Slice(bOff, 16);

        var topDecoded = SnesGfx.Decode2BppTile8x8(topTile);
        var bottomDecoded = SnesGfx.Decode2BppTile8x8(bottomTile);

        sb.AppendLine($"=== INDEX {idx} (0x{idx:X2}) | TOP 0x{tOff:X6} | BOTTOM 0x{bOff:X6} ===");
        
        // Print top half (8 rows)
        for (int y = 0; y < 8; y++)
        {
            for (int x = 0; x < 8; x++)
            {
                byte px = topDecoded[y * 8 + x];
                sb.Append(px > 0 ? "█" : ".");
            }
            sb.AppendLine();
        }
        // Print bottom half (8 rows)
        for (int y = 0; y < 8; y++)
        {
            for (int x = 0; x < 8; x++)
            {
                byte px = bottomDecoded[y * 8 + x];
                sb.Append(px > 0 ? "█" : ".");
            }
            sb.AppendLine();
        }
        sb.AppendLine();
    }

    Directory.CreateDirectory(outDir);
    string txtPath = Path.Combine(outDir, $"dialogue_font_{topOff:X6}.txt");
    File.WriteAllText(txtPath, sb.ToString(), Encoding.UTF8);
    Console.WriteLine($"Dialogue font ASCII grid generated: {txtPath}");
}
