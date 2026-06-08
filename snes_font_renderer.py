import os
import json

def decode_2bpp_tile(tile_bytes):
    """
    Decodes an 8x8 SNES 2bpp tile (16 bytes) into an 8x8 grid of color indices (0-3).
    """
    if len(tile_bytes) < 16:
        tile_bytes = tile_bytes + b"\x00" * (16 - len(tile_bytes))
    pixels = []
    for row in range(8):
        bp0 = tile_bytes[row]
        bp1 = tile_bytes[row + 8]
        row_pixels = []
        for col in range(8):
            bit = 7 - col
            p0 = (bp0 >> bit) & 1
            p1 = (bp1 >> bit) & 1
            color_index = p0 | (p1 << 1)
            row_pixels.append(color_index)
        pixels.append(row_pixels)
    return pixels

def get_glyph_pixels(rom_data, top_offset, bottom_offset, index):
    """
    Gets the combined 8x16 pixel grid for a character index.
    """
    top_tile = rom_data[top_offset + index * 16 : top_offset + (index + 1) * 16]
    bottom_tile = rom_data[bottom_offset + index * 16 : bottom_offset + (index + 1) * 16]
    top_pixels = decode_2bpp_tile(top_tile)
    bottom_pixels = decode_2bpp_tile(bottom_tile)
    return top_pixels + bottom_pixels

def main():
    workspace = "/Users/acr/Develop/nage-libre"
    rom_path = os.path.join(workspace, "Nage Libre - Seijaku no Suishin (Japan).sfc")
    out_dir = os.path.join(workspace, "docs")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(rom_path):
        print(f"ROM not found at {rom_path}")
        return

    with open(rom_path, "rb") as f:
        rom_data = f.read()

    # Font offsets
    hira_top = 0x28470
    hira_bottom = 0x28A70
    kata_top = 0x29810
    kata_bottom = 0x29E10
    count = 96

    # 1. Load initial table mappings from nage_libre.tbl if it exists
    tbl_mappings = {}
    tbl_path = os.path.join(workspace, "nage_libre.tbl")
    if os.path.exists(tbl_path):
        with open(tbl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    h, c = line.split("=", 1)
                    try:
                        val = int(h, 16)
                        tbl_mappings[val] = c
                    except ValueError:
                        continue

    # 2. Extract pixel data for Hiragana (0x08 - 0x67) and Katakana (0x88 - 0xE7)
    glyphs_data = []

    # Hiragana
    for idx in range(count):
        byte_val = 0x08 + idx
        pixels = get_glyph_pixels(rom_data, hira_top, hira_bottom, idx)
        glyphs_data.append({
            "byte_val": byte_val,
            "byte_hex": f"0x{byte_val:02X}",
            "font_type": "Hiragana",
            "index": idx,
            "rom_offset_top": f"0x{hira_top + idx * 16:06X}",
            "pixels": pixels,
            "mapping": tbl_mappings.get(byte_val, "")
        })

    # Katakana
    for idx in range(count):
        byte_val = 0x88 + idx
        pixels = get_glyph_pixels(rom_data, kata_top, kata_bottom, idx)
        glyphs_data.append({
            "byte_val": byte_val,
            "byte_hex": f"0x{byte_val:02X}",
            "font_type": "Katakana",
            "index": idx,
            "rom_offset_top": f"0x{kata_top + idx * 16:06X}",
            "pixels": pixels,
            "mapping": tbl_mappings.get(byte_val, "")
        })

    # 3. Generate Interactive HTML Grid
    html_path = os.path.join(out_dir, "font_grid.html")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nage Libre - SNES Font Viewer & Mapper</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 29, 49, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-color: #e2e8f0;
            --accent-color: #00f2fe;
            --accent-hover: #4facfe;
            --pixel-on: #00f2fe;
            --pixel-off: #161d31;
            --glow: 0 0 20px rgba(0, 242, 254, 0.4);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: radial-gradient(circle at top, #1e293b, var(--bg-color));
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        header {{
            text-align: center;
            margin-bottom: 2rem;
            max-width: 800px;
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }}

        header p {{
            color: #94a3b8;
            font-size: 1.1rem;
            line-height: 1.5;
        }}

        .main-container {{
            display: flex;
            gap: 2rem;
            max-width: 1400px;
            width: 100%;
            align-items: flex-start;
        }}

        .controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            background: var(--card-bg);
            padding: 0.5rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            backdrop-filter: blur(10px);
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: #94a3b8;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .tab-btn:hover {{
            color: var(--text-color);
            background: rgba(255, 255, 255, 0.05);
        }}

        .tab-btn.active {{
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            color: #0b0f19;
            box-shadow: var(--glow);
        }}

        .grid-section {{
            flex: 1;
        }}

        .font-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
            gap: 1rem;
        }}

        .glyph-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s ease;
            backdrop-filter: blur(5px);
        }}

        .glyph-card:hover, .glyph-card.selected {{
            border-color: var(--accent-color);
            box-shadow: 0 0 15px rgba(0, 242, 254, 0.2);
            transform: translateY(-2px);
        }}

        .glyph-card .hex {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }}

        .glyph-preview-mini {{
            display: grid;
            grid-template-columns: repeat(8, 4px);
            gap: 1px;
            background: #111827;
            padding: 4px;
            border-radius: 4px;
            margin-bottom: 0.5rem;
        }}

        .pixel {{
            width: 4px;
            height: 4px;
            background-color: var(--pixel-off);
        }}

        .pixel.on {{
            background-color: var(--pixel-on);
        }}

        .glyph-card .char {{
            font-size: 1.2rem;
            font-weight: 700;
            color: #fff;
        }}

        .sidebar {{
            width: 380px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(10px);
            position: sticky;
            top: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .sidebar h2 {{
            font-size: 1.4rem;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
        }}

        .large-preview-container {{
            background: #090d16;
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            justify-content: center;
            align-items: center;
            border: 1px solid var(--border-color);
        }}

        .glyph-preview-large {{
            display: grid;
            grid-template-columns: repeat(8, 20px);
            gap: 1px;
            background: #000;
            padding: 8px;
            border-radius: 6px;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        }}

        .large-pixel {{
            width: 20px;
            height: 20px;
            background-color: #111827;
            border-radius: 2px;
        }}

        .large-pixel.on {{
            background-color: var(--pixel-on);
            box-shadow: 0 0 4px var(--pixel-on);
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            font-size: 0.95rem;
            padding: 0.5rem 0;
            border-bottom: 1px dashed rgba(255,255,255,0.05);
        }}

        .info-label {{
            color: #94a3b8;
        }}

        .info-value {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }}

        .edit-section {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .edit-input {{
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #fff;
            padding: 0.75rem;
            font-size: 1.1rem;
            font-family: inherit;
            text-align: center;
            transition: border-color 0.2s ease;
        }}

        .edit-input:focus {{
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
        }}

        .tbl-output-container {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .tbl-output-textarea {{
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #94a3b8;
            padding: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            resize: none;
            height: 150px;
        }}

        .btn-group {{
            display: flex;
            gap: 0.5rem;
        }}

        .btn-copy, .btn-download {{
            flex: 1;
            border: none;
            color: #0b0f19;
            padding: 0.75rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s ease;
        }}

        .btn-copy {{
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            box-shadow: var(--glow);
        }}

        .btn-download {{
            background: linear-gradient(135deg, #34d399 0%, #059669 100%);
            color: white;
        }}

        .btn-copy:active, .btn-download:active {{
            transform: scale(0.98);
        }}
    </style>
</head>
<body>
    <header>
        <h1>Nage Libre - SNES Font Viewer & Mapper</h1>
        <p>Interactive tool to map custom dialogue character bytes to Unicode Japanese characters. Click a glyph block to see detail, edit its mapping, and export your `.tbl` file updates.</p>
    </header>

    <div class="main-container">
        <div class="grid-section">
            <div class="controls">
                <button class="tab-btn active" onclick="switchTab('Hiragana')">Hiragana Dialogue (0x08 - 0x67)</button>
                <button class="tab-btn" onclick="switchTab('Katakana')">Katakana Dialogue (0x88 - 0xE7)</button>
            </div>
            <div class="font-grid" id="grid">
                <!-- Injected by JS -->
            </div>
        </div>

        <div class="sidebar">
            <h2>Glyph details</h2>
            <div class="large-preview-container">
                <div class="glyph-preview-large" id="large-preview">
                    <!-- Injected by JS -->
                </div>
            </div>
            
            <div id="details-info">
                <div class="info-row">
                    <span class="info-label">Byte Hex</span>
                    <span class="info-value" id="info-hex">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Type</span>
                    <span class="info-value" id="info-type">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">ROM Offset (Top)</span>
                    <span class="info-value" id="info-offset">-</span>
                </div>
            </div>

            <div class="edit-section">
                <label for="char-input" style="font-weight: 600; font-size: 0.9rem; color: #94a3b8;">Assign Unicode Character:</label>
                <input type="text" id="char-input" class="edit-input" maxlength="4" placeholder="e.g. ア" oninput="updateMapping(this.value)">
            </div>

            <div class="tbl-output-container">
                <label style="font-weight: 600; font-size: 0.9rem; color: #94a3b8;">Generated .tbl entries:</label>
                <textarea id="tbl-output" class="tbl-output-textarea" readonly></textarea>
                <div class="btn-group">
                    <button class="btn-copy" onclick="copyTbl()">Copy</button>
                    <button class="btn-download" onclick="downloadTbl()">Download .tbl</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const glyphs = {json.dumps(glyphs_data)};
        let activeTab = "Hiragana";
        let selectedGlyph = null;

        function switchTab(tabName) {{
            activeTab = tabName;
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent.includes(tabName));
            }});
            renderGrid();
        }}

        function renderGrid() {{
            const grid = document.getElementById('grid');
            grid.innerHTML = '';
            
            const filtered = glyphs.filter(g => g.font_type === activeTab);
            filtered.forEach(g => {{
                const card = document.createElement('div');
                card.className = 'glyph-card';
                if (selectedGlyph && selectedGlyph.byte_val === g.byte_val) {{
                    card.classList.add('selected');
                }}
                card.onclick = () => selectGlyph(g);

                // mini preview
                const preview = document.createElement('div');
                preview.className = 'glyph-preview-mini';
                for (let r = 0; r < 16; r++) {{
                    for (let c = 0; c < 8; c++) {{
                        const px = document.createElement('div');
                        px.className = 'pixel' + (g.pixels[r][c] > 0 ? ' on' : '');
                        preview.appendChild(px);
                    }}
                }}

                const hex = document.createElement('div');
                hex.className = 'hex';
                hex.textContent = g.byte_hex;

                const charSpan = document.createElement('div');
                charSpan.className = 'char';
                charSpan.textContent = g.mapping || '?';

                card.appendChild(hex);
                card.appendChild(preview);
                card.appendChild(charSpan);
                grid.appendChild(card);
            }});
        }}

        function selectGlyph(g) {{
            selectedGlyph = g;
            
            // Highlight card
            document.querySelectorAll('.glyph-card').forEach(card => {{
                card.classList.toggle('selected', card.firstChild.textContent === g.byte_hex);
            }});

            // Render large preview
            const large = document.getElementById('large-preview');
            large.innerHTML = '';
            for (let r = 0; r < 16; r++) {{
                for (let c = 0; c < 8; c++) {{
                    const px = document.createElement('div');
                    px.className = 'large-pixel' + (g.pixels[r][c] > 0 ? ' on' : '');
                    large.appendChild(px);
                }}
            }}

            // Update info
            document.getElementById('info-hex').textContent = g.byte_hex;
            document.getElementById('info-type').textContent = g.font_type + ` (Index ${{g.index}})`;
            document.getElementById('info-offset').textContent = g.rom_offset_top;
            
            // Update input value
            const input = document.getElementById('char-input');
            input.value = g.mapping;
            input.focus();
        }}

        function updateMapping(val) {{
            if (!selectedGlyph) return;
            selectedGlyph.mapping = val;
            
            // Refresh grid cards quickly
            renderGrid();
            updateTblOutput();
        }}

        function updateTblOutput() {{
            const textarea = document.getElementById('tbl-output');
            // Format sorted by byte value
            const lines = glyphs.map(g => {{
                const cleanHex = g.byte_hex.replace('0x', '');
                const cleanVal = g.mapping || `{{${{cleanHex}}}}`;
                return `${{cleanHex}}=${{cleanVal}}`;
            }});
            textarea.value = lines.join('\\n');
        }}

        function copyTbl() {{
            const textarea = document.getElementById('tbl-output');
            textarea.select();
            document.execCommand('copy');
            alert('Copied to clipboard!');
        }}

        function downloadTbl() {{
            const textarea = document.getElementById('tbl-output');
            const blob = new Blob([textarea.value], {{type: 'text/plain;charset=utf-8'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'nage_libre.tbl';
            a.click();
        }}

        // Init
        switchTab('Hiragana');
        if (glyphs.length > 0) {{
            selectGlyph(glyphs[0]);
        }}
        updateTblOutput();
    </script>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Wrote HTML font grid to {html_path}")

if __name__ == "__main__":
    main()
