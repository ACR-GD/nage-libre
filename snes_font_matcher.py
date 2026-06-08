import os

def decode_2bpp_tile(tile_bytes):
    pixels = []
    for row in range(8):
        bp0 = tile_bytes[row]
        bp1 = tile_bytes[row + 8]
        row_pixels = []
        for col in range(8):
            bit = 7 - col
            p0 = (bp0 >> bit) & 1
            p1 = (bp1 >> bit) & 1
            row_pixels.append(p0 | (p1 << 1))
        pixels.append(row_pixels)
    return pixels

def get_glyph_pixels(rom_data, top_offset, bottom_offset, index):
    top_tile = rom_data[top_offset + index * 16 : top_offset + (index + 1) * 16]
    bottom_tile = rom_data[bottom_offset + index * 16 : bottom_offset + (index + 1) * 16]
    return decode_2bpp_tile(top_tile), decode_2bpp_tile(bottom_tile)

def get_bottom_similarity(tile1, tile2):
    """
    Returns the number of matching pixels (0-64) between two 8x8 tiles.
    """
    matches = 0
    for r in range(8):
        for c in range(8):
            # Treat any ink pixel (>0) as active
            act1 = 1 if tile1[r][c] > 0 else 0
            act2 = 1 if tile2[r][c] > 0 else 0
            if act1 == act2:
                matches += 1
    return matches

def main():
    workspace = "/Users/acr/Develop/nage-libre"
    rom_path = os.path.join(workspace, "Nage Libre - Seijaku no Suishin (Japan).sfc")
    
    if not os.path.exists(rom_path):
        print("ROM not found.")
        return

    with open(rom_path, "rb") as f:
        rom_data = f.read()

    kata_top = 0x29810
    kata_bottom = 0x29E10
    
    # Standard characters mapping (Index 36 to 95)
    # We know this range maps exactly in Gojuon order matching Hiragana.
    gojuon_standard = [
        "ア", "イ", "ウ", "エ", "オ",
        "カ", "キ", "ク", "ケ", "コ",
        "サ", "シ", "ス", "セ", "ソ",
        "タ", "チ", "ツ", "テ", "ト",
        "ナ", "ニ", "ヌ", "ネ", "ノ",
        "ハ", "ヒ", "フ", "ヘ", "ホ",
        "マ", "ミ", "ム", "メ", "モ",
        "ヤ", "ユ", "ヨ",
        "ラ", "リ", "ル", "レ", "ロ",
        "ワ", "ヲ", "ン",
        "ー", "゛", "゜", "？", "！", "。", "「", "」", "・", "事", "見", "言", "思", "、"
    ]

    # Load all 96 glyphs
    glyphs = []
    for idx in range(96):
        top_tile, bottom_tile = get_glyph_pixels(rom_data, kata_top, kata_bottom, idx)
        glyphs.append({
            "index": idx,
            "top": top_tile,
            "bottom": bottom_tile
        })

    print("=== AUTOMATIC KANA BOTTOM MATCHING ===")
    
    # We will try to match the first 36 glyphs (dakuten/handakuten/small variants)
    for idx in range(36):
        bottom_tile = glyphs[idx]["bottom"]
        top_tile = glyphs[idx]["top"]
        
        # Calculate similarity with the bottom tiles of standard Gojuon characters (indices 36 to 81)
        best_score = -1
        best_match_idx = -1
        
        for std_idx in range(36, 82):
            std_bottom = glyphs[std_idx]["bottom"]
            score = get_bottom_similarity(bottom_tile, std_bottom)
            if score > best_score:
                best_score = score
                best_match_idx = std_idx
                
        # Also check if it's completely empty at the bottom (like 'ク' / 'グ' or small characters)
        ink_bottom = sum(sum(1 if p > 0 else 0 for p in row) for row in bottom_tile)
        
        # Detect accent in the top tile (rows 0 to 4)
        # Standard accent patterns:
        # Dakuten has pixels around top right.
        # Let's count ink pixels in top 4 rows
        ink_top_left = sum(sum(1 if top_tile[r][c] > 0 else 0 for c in range(4)) for r in range(4))
        ink_top_right = sum(sum(1 if top_tile[r][c] > 0 else 0 for c in range(4, 8)) for r in range(4))
        
        base_char = gojuon_standard[best_match_idx - 36]
        
        print(f"Index {idx:2d} (0x{0x88 + idx:02X}): Bottom ink: {ink_bottom:2d} | Top left ink: {ink_top_left}, Right: {ink_top_right} | Best standard match: {base_char} (score {best_score}/64)")

if __name__ == "__main__":
    main()
