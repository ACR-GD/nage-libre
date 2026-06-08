--[[
  Nage Libre — dump mémoire prologue pour Mesen-S / Mesen2 (SNES)

  Usage:
    1. Tools → Script Window → Load Script → scripts/mesen_prologue_dump.lua
    2. Run (▶). La console affiche le dossier de sortie.
    3. Pose un breakpoint CPU OU laisse WATCH_EXEC actif (voir config).
    4. Joue jusqu'au break → un sous-dossier est créé automatiquement.

  IMPORTANT — $87:DCCB ne hit JAMAIS si le prologue freeze :
    DCCB n'est appelé qu'après 5 tours de boucle via JSR @ $87:D6D4.
    Si freeze avant la fin → utiliser Pause manuelle (F10) ou breakpoints ci-dessous.

  Sortie (par défaut): <repo>/mesen_dumps/<timestamp>_PC_<addr>/

  Fichiers produits:
    meta.txt          — PC, registres, ROM, frame
    cpu_state.txt     — dump brut getState()
    wram_7F6000.bin   — tilemap / texte prologue ($7F:6000–$7F:6FFF)
    wram_7E0000.bin   — bas WRAM ($7E:0000–$7F:FFFF, 128 KiB)
    prologue_words.txt — mots 16-bit LE aux offsets clés depuis $7F:64C0
    zp_direct.txt     — $00–$FF (direct page / $7E:0000)

  Analyse côté repo:
    python3 scripts/analyze_mesen_dump.py mesen_dumps/<dossier>
]]

-- ── Configuration ───────────────────────────────────────────────────────────

-- Chemin absolu du repo (Mac/Linux). Mesen peut aussi écrire dans getScriptDataFolder().
local OUTPUT_DIR = "/Users/acr/Develop/nage-libre/mesen_dumps"

-- true = dump à chaque breakpoint debugger (event codeBreak)
local AUTO_DUMP_ON_BREAK = true

-- Adresses CPU 24-bit : dump auto à l'exécution (sans breakpoint manuel)
-- Priorité debug freeze fin prologue :
local WATCH_EXEC = {
  0x0087D70C,  -- $87:D70C  début d'un acte (×5 max avant DCCB)
  0x0087D6D4,  -- $87:D6D4  JSR DCCB — fin prologue (rare si freeze)
  0x0087D756,  -- $87:D756  attente dialogue (LDA $0214, CMP #$0200)
  0x0080F4AB,  -- $80:F4AB  moteur typewriter (texte ROM)
  -- 0x008380FF,  -- $83:80FF  post-décompression écran 1
  -- 0x00838103,  -- $83:8103  phases tilemap écran 1
}

-- Ignorer les breaks trop rapprochés (step-in répété)
local MIN_FRAMES_BETWEEN_DUMPS = 0

-- false = skip le dump 128 KiB ($7E:0000–$7F:FFFF, ~1–2 s)
local FULL_WRAM_DUMP = true

-- ── Constantes prologue ─────────────────────────────────────────────────────

local MEM = emu.memType.cpuDebug
local TILEMAP_BASE = 0x7F64C0

local PROLOGUE_OFFSETS = {
  {0x0122, "L1 visible ($65E2)"},
  {0x0142, "signature / L2 ($6602)"},
  {0x0166, "offset $0166"},
  {0x01A2, "row2 tilemap ($6662)"},
  {0x0222, "row3 preload ($66E2)"},
  {0x02A2, "row4+ ($66E2+)"},
}

local ZP_VARS = {
  {0x06, "phase counter ($06)"},
  {0x07, "decomp ptr +1 ($07)"},
  {0x08, "decomp ptr +2 ($08)"},
  {0x09, "text ptr lo ($09)"},
  {0x0A, "text ptr hi ($0A)"},
  {0x0B, "text ptr bank ($0B)"},
  {0x214, "wait flag ($0214)"},
  {0x071, "dialogue mode ($0071)"},
}

local WRAM7E_VARS_EXTRA = {
  {0x7E17D4, "config ptr lo ($17D4)"},
  {0x7E17D5, "config ptr hi ($17D5)"},
  {0x7E17D6, "scene index ($17D6)"},
  {0x7E17D7, "scene index+1 ($17D7)"},
  {0x7E105D, "loop scratch ($105D)"},
  {0x7E101A, "loop scratch ($101A)"},
}

local WRAM7E_VARS = {
  {0x7E17D6, "scene index ($17D6)"},
  {0x7E17D4, "config ($17D4)"},
}

-- ── État interne ─────────────────────────────────────────────────────────────

local dumpCount = 0
local lastDumpFrame = -999999

-- ── Utilitaires ─────────────────────────────────────────────────────────────

local function log(msg)
  emu.log("[nl-dump] " .. msg)
end

local function mkdir_p(path)
  os.execute('mkdir -p "' .. path:gsub('"', '\\"') .. '"')
end

local function hex(n, width)
  width = width or 4
  return string.format("%0" .. width .. "X", n & ((1 << (width * 4)) - 1))
end

local function readByte(addr)
  return emu.read(addr, MEM)
end

local function readWordLE(addr)
  local lo = readByte(addr)
  local hi = readByte(addr + 1)
  return lo + hi * 256
end

local function readBlock(addr, size)
  local t = {}
  for i = 0, size - 1 do
    t[i + 1] = string.char(readByte(addr + i))
  end
  return table.concat(t)
end

local function writeBinary(path, data)
  local f = io.open(path, "wb")
  if not f then
    log("ERREUR écriture: " .. path)
    return false
  end
  f:write(data)
  f:close()
  return true
end

local function writeText(path, text)
  local f = io.open(path, "w")
  if not f then
    log("ERREUR écriture: " .. path)
    return false
  end
  f:write(text)
  f:close()
  return true
end

local function getFrameCount(state)
  if state.ppu and state.ppu.frameCount then
    return state.ppu.frameCount
  end
  if state["ppu.frameCount"] then
    return state["ppu.frameCount"]
  end
  return 0
end

local function getCpuField(state, name)
  if state.cpu and state.cpu[name] then
    return state.cpu[name]
  end
  return state["cpu." .. name]
end

local function formatPc(state)
  local pc = getCpuField(state, "pc") or 0
  local k = getCpuField(state, "k")
  if k == nil then
    k = getCpuField(state, "pb") or getCpuField(state, "bank") or 0
  end
  if k and k > 0 then
    return (k * 65536) + (pc & 0xFFFF)
  end
  return pc
end

local function stateToText(state, indent)
  indent = indent or ""
  local lines = {}
  for k, v in pairs(state) do
    if type(v) == "table" then
      lines[#lines + 1] = indent .. tostring(k) .. ":"
      lines[#lines + 1] = stateToText(v, indent .. "  ")
    else
      lines[#lines + 1] = string.format("%s%s = %s", indent, tostring(k), tostring(v))
    end
  end
  table.sort(lines)
  return table.concat(lines, "\n")
end

local function decodeWordsFromTilemap(base, startOff, count)
  local lines = {}
  for i = 0, count - 1 do
    local off = startOff + i * 2
    local addr = base + off
    local w = readWordLE(addr)
    lines[#lines + 1] = string.format(
      "  +%04X  $%06X  %04X",
      off, addr, w
    )
  end
  return table.concat(lines, "\n")
end

local function buildPrologueWordsText()
  local out = {}
  out[#out + 1] = string.format("Tilemap base $%06X\n", TILEMAP_BASE)

  for _, entry in ipairs(PROLOGUE_OFFSETS) do
    local off, label = entry[1], entry[2]
    out[#out + 1] = string.format("\n--- %s (offset +%04X) — 32 mots ---", label, off)
    out[#out + 1] = decodeWordsFromTilemap(TILEMAP_BASE, off, 32)
  end

  out[#out + 1] = "\n\n--- Signature écran 1 ---"
  local sig1 = readWordLE(0x7F6602)
  local sig2 = readWordLE(0x7F6604)
  out[#out + 1] = string.format("  $7F:6602 = %04X (attendu 075A)", sig1)
  out[#out + 1] = string.format("  $7F:6604 = %04X (attendu 002A)", sig2)

  return table.concat(out, "\n")
end

local function buildZpText()
  local lines = {"Direct page / WRAM $7E:0000\n"}
  for _, entry in ipairs(ZP_VARS) do
    local addr, label = entry[1], entry[2]
    local w = readWordLE(0x7E0000 + addr)
    local b = readByte(0x7E0000 + addr)
    lines[#lines + 1] = string.format("  $%04X  %s  byte=%02X  word=%04X", addr, label, b, w)
  end
  lines[#lines + 1] = "\nWRAM game vars:\n"
  for _, entry in ipairs(WRAM7E_VARS) do
    local addr, label = entry[1], entry[2]
    lines[#lines + 1] = string.format("  $%06X  %s  = %04X", addr, label, readWordLE(addr))
  end
  for _, entry in ipairs(WRAM7E_VARS_EXTRA) do
    local addr, label = entry[1], entry[2]
    lines[#lines + 1] = string.format("  $%06X  %s  = %04X", addr, label, readWordLE(addr))
  end
  lines[#lines + 1] = string.format("\n  $000214 (abs) wait = %04X (attendu 0200 pour continuer)", readWordLE(0x7E0214))
  return table.concat(lines, "\n")
end

-- ── Dump principal ───────────────────────────────────────────────────────────

local function doDump(reason)
  local state = emu.getState()
  local frame = getFrameCount(state)
  if frame - lastDumpFrame < MIN_FRAMES_BETWEEN_DUMPS then
    return
  end
  lastDumpFrame = frame

  dumpCount = dumpCount + 1
  local pc = formatPc(state)
  local ts = os.date("%Y%m%d_%H%M%S")
  local dir = string.format("%s/%s_PC_%s_%03d", OUTPUT_DIR, ts, hex(pc, 6), dumpCount)

  mkdir_p(dir)

  local rom = emu.getRomInfo()
  local romName = rom and rom.name or "unknown"
  local romPath = rom and rom.path or "?"

  local meta = {}
  meta[#meta + 1] = string.format("reason = %s", reason)
  meta[#meta + 1] = string.format("rom = %s", romName)
  meta[#meta + 1] = string.format("rom_path = %s", romPath)
  meta[#meta + 1] = string.format("pc = $%s", hex(pc, 6))
  meta[#meta + 1] = string.format("frame = %d", frame)
  meta[#meta + 1] = string.format("a = $%04X", getCpuField(state, "a") or 0)
  meta[#meta + 1] = string.format("x = $%04X", getCpuField(state, "x") or 0)
  meta[#meta + 1] = string.format("y = $%04X", getCpuField(state, "y") or 0)
  meta[#meta + 1] = string.format("sp = $%04X", getCpuField(state, "sp") or 0)
  meta[#meta + 1] = string.format("dump_dir = %s", dir)

  writeText(dir .. "/meta.txt", table.concat(meta, "\n") .. "\n")
  writeText(dir .. "/cpu_state.txt", stateToText(state))
  writeText(dir .. "/prologue_words.txt", buildPrologueWordsText())
  writeText(dir .. "/zp_direct.txt", buildZpText())

  -- WRAM $7F:6000–$6FFF (4 KiB — tilemap prologue)
  writeBinary(dir .. "/wram_7F6000_1000.bin", readBlock(0x7F6000, 0x1000))

  if FULL_WRAM_DUMP then
    writeBinary(dir .. "/wram_7E0000_20000.bin", readBlock(0x7E0000, 0x20000))
  end

  log(string.format("Dump #%d → %s", dumpCount, dir))
  if emu.displayMessage then
    emu.displayMessage("NL dump → " .. dir)
  end
end

-- ── Callbacks ────────────────────────────────────────────────────────────────

local function onCodeBreak()
  if AUTO_DUMP_ON_BREAK then
    doDump("codeBreak")
  end
end

local function onExec(address, value)
  for _, watch in ipairs(WATCH_EXEC) do
    if address == watch then
      doDump(string.format("exec_$%06X", address))
      return
    end
  end
end

-- ── Init ─────────────────────────────────────────────────────────────────────

mkdir_p(OUTPUT_DIR)

emu.addEventCallback(onCodeBreak, emu.eventType.codeBreak)

for _, addr in ipairs(WATCH_EXEC) do
  emu.addMemoryCallback(onExec, emu.memCallbackType.exec, addr, addr)
  log(string.format("Watch exec $%06X", addr))
end

log("Script actif.")
log("OUTPUT_DIR = " .. OUTPUT_DIR)
log("Breakpoints utiles si DCCB ne hit pas:")
log("  $87:D70C (acte), $87:D756 (attente), $80:F4AB (texte)")
log("  Au freeze: Pause (F10) → Debugger montre PC → dump manuel si besoin")
log("Analyse: python3 scripts/analyze_mesen_dump.py " .. OUTPUT_DIR .. "/<dossier>")
