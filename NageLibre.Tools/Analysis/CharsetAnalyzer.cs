using System.Globalization;
using System.Text;
using NageLibre.Tools.Gfx;
using NageLibre.Tools.Snes;

namespace NageLibre.Tools.Analysis;

public sealed record FontBank(int RomStart, int GlyphCount);

public sealed record GlyphEntry(
    int BankIndex,
    int GlyphIndex,
    int RomOffset,
    int VramTileIndex,
    int InkPixels,
    string Category);

public static class CharsetAnalyzer
{
  public const int VramTileBias = 0xFB;
  public const int GlyphBytes = Font16x16.CharacterBytes;

  public static IReadOnlyList<FontBank> FindFontBanks(ReadOnlySpan<byte> rom, int searchStart = 0x20000, int searchEnd = 0x40000)
  {
    var banks = new List<FontBank>();
    int off = searchStart;

    while (off < searchEnd && off + GlyphBytes <= rom.Length)
    {
      if (!IsLikelyGlyph64(rom.Slice(off, GlyphBytes)))
      {
        off += 16;
        continue;
      }

      int start = off;
      int count = 0;
      while (off + GlyphBytes <= rom.Length && off < searchEnd && IsLikelyGlyph64(rom.Slice(off, GlyphBytes)))
      {
        count++;
        off += GlyphBytes;
      }

      if (count is >= 15 and <= 280)
        banks.Add(new FontBank(start, count));

      off += 16;
    }

    return banks;
  }

  public static bool IsLikelyGlyph64(ReadOnlySpan<byte> block) =>
      Compression.Decompressor.IsLikelyGlyph64(block);

  public static IEnumerable<GlyphEntry> CatalogGlyphs(SnesRom rom, IReadOnlyList<FontBank> banks)
  {
    for (int bi = 0; bi < banks.Count; bi++)
    {
      var bank = banks[bi];
      for (int gi = 0; gi < bank.GlyphCount; gi++)
      {
        int romOff = bank.RomStart + gi * GlyphBytes;
        var block = rom.AsSpan().Slice(romOff, GlyphBytes);
        int ink = CountInkPixels(block);
        int tile = gi + VramTileBias;
        yield return new GlyphEntry(bi, gi, romOff, tile, ink, ClassifyGlyph(ink));
      }
    }
  }

  public static int CountInkPixels(ReadOnlySpan<byte> glyph64)
  {
    int ink = 0;
    for (int q = 0; q < 4; q++)
    {
      var tile = glyph64.Slice(q * 16, 16);
      for (int row = 0; row < 8; row++)
      {
        for (int col = 0; col < 8; col++)
        {
          int bit = 7 - col;
          int p = ((tile[row] >> bit) & 1) | (((tile[row + 8] >> bit) & 1) << 1);
          if (p != 0) ink++;
        }
      }
    }
    return ink;
  }

  /// <summary>Heuristique grossière : syllabaires simples vs kanji denses vs ponctuation.</summary>
  public static string ClassifyGlyph(int inkPixels) => inkPixels switch
  {
    < 25 => "sparse",
    < 55 => "syllabary_latin",
    < 90 => "kana_kanji_light",
    _ => "kanji_dense",
  };

  public static void ExportCatalogCsv(string path, IEnumerable<GlyphEntry> entries)
  {
    var lines = new List<string>
    {
      "bank_index,glyph_index,rom_offset,vram_tile_hex,ink_pixels,category,notes",
    };

    foreach (var e in entries)
    {
      lines.Add(string.Join(",",
        e.BankIndex.ToString(CultureInfo.InvariantCulture),
        e.GlyphIndex.ToString(CultureInfo.InvariantCulture),
        $"0x{e.RomOffset:X6}",
        $"0x{e.VramTileIndex:X3}",
        e.InkPixels.ToString(CultureInfo.InvariantCulture),
        e.Category,
        "VRAM_tile=glyph_index+0xFB"));
    }

    File.WriteAllLines(path, lines, Encoding.UTF8);
  }

  public static void ExportSummaryCsv(string path, IReadOnlyList<FontBank> banks, IEnumerable<GlyphEntry> entries)
  {
    var list = entries.ToList();
    var byCat = list.GroupBy(e => e.Category).ToDictionary(g => g.Key, g => g.Count());
    var lines = new List<string>
    {
      "metric,value,notes",
      $"font_banks,{banks.Count},Région ROM 0x20000-0x40000",
      $"total_glyphs,{list.Count},",
      $"vram_tile_bias,0x{VramTileBias:X},tuile_VRAM = index + 0xFB",
      $"category_sparse,{byCat.GetValueOrDefault("sparse")},",
      $"category_syllabary_latin,{byCat.GetValueOrDefault("syllabary_latin")},Probable hiragana/katakana/ASCII",
      $"category_kana_kanji_light,{byCat.GetValueOrDefault("kana_kanji_light")},",
      $"category_kanji_dense,{byCat.GetValueOrDefault("kanji_dense")},Probable kanji",
      "hiragana_complete_expected,~86,Standard gojuon minus obsolete",
      "katakana_complete_expected,~86,",
      "encoding_text,byte_vram_tile_id,Texte utilise l'ID tuile (ex. 0x8D XX ou byte direct)",
    };

    for (int i = 0; i < banks.Count; i++)
    {
      var b = banks[i];
      lines.Add($"bank_{i}_start,0x{b.RomStart:X6},");
      lines.Add($"bank_{i}_count,{b.GlyphCount},");
      lines.Add($"bank_{i}_tiles,0x{VramTileBias:X}-0x{VramTileBias + b.GlyphCount - 1:X},");
    }

    File.WriteAllLines(path, lines, Encoding.UTF8);
  }

  public static void ExportAtlas(string path, SnesRom rom, IReadOnlyList<FontBank> banks, int cols = 32)
  {
    var entries = CatalogGlyphs(rom, banks).ToList();
    if (entries.Count == 0)
      return;

    int rows = (entries.Count + cols - 1) / cols;
    int width = cols * 16;
    int height = rows * 16;
    var pixels = new byte[width * height];
    var pal = new (byte R, byte G, byte B)[]
    {
      (0, 0, 0), (120, 120, 120), (200, 200, 200), (255, 255, 255),
    };

    for (int i = 0; i < entries.Count; i++)
    {
      int cx = (i % cols) * 16;
      int cy = (i / cols) * 16;
      var block = rom.AsSpan().Slice(entries[i].RomOffset, GlyphBytes);
      var glyph = Font16x16.ToIndexedBitmap16x16(block);
      for (int y = 0; y < 16; y++)
      for (int x = 0; x < 16; x++)
        pixels[(cy + y) * width + (cx + x)] = glyph[y * 16 + x];
    }

    SnesGfx.ExportIndexedBmp(path, pixels, width, height, pal);
  }
}
