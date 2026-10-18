--[[
  Nage Libre — capture des CHAÎNES d'IDs 16-bit rendues à l'écran.

  Les boucles typewriter lisent une chaîne d'IDs 16-bit (terminée $FFFF) via le
  pointeur 24-bit [$09]/$0A/$0B, puis tracent chaque glyphe avec $80:F433 :
    • $80:F4A7  : chaînes en ROM (banque $87 : combat, menus, banderoles…)
    • $80:F4CA  : dialogue décompressé en $7F:64C0 (narration / pré-combat)

  On logue, pour CHAQUE chaîne (dédupliquée par adresse source), la liste complète
  de ses IDs. Les IDs < $0800 sont les glyphes de police : ce sont eux que
  l'allocateur de paires anglaises ne doit PAS écraser. Je croiserai ces IDs avec
  nos paires pour réserver exactement les glyphes japonais en collision.

  Usage :
    1. nl-full-en.sfc, arriver JUSTE AVANT la scène pré-combat.
    2. Debug → Script Window → Load → ce fichier → Run.
    3. Déclencher du texte NEUF : avancer tout le dialogue pré-combat +
       la banderole « STAGE 1 START » + la condition de victoire.
    4. M'envoyer  mesen_dumps/glyph_ids.log
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/glyph_ids.log"
local CB  = emu.callbackType or emu.memCallbackType
local MEM = emu.memType.snesMemory or emu.memType.cpuDebug

local fileHandle = io.open(LOG_PATH, "w")
local seenSrc = {}
local seenId  = {}
local frame = 0

local function logline(s)
  if fileHandle then fileHandle:write(s.."\n"); fileHandle:flush() end
  if emu.log then emu.log(s) end
end

local function rd(addr) return emu.read(addr, MEM) & 0xFF end
local function rd16(a) return rd(a) | (rd(a+1)<<8) end
local function rd24(a) return rd(a) | (rd(a+1)<<8) | (rd(a+2)<<16) end

local function onString(tag)
  if fileHandle == nil then return end
  local st = emu.getState()
  local dp = (st and st.cpu and st.cpu.d) or 0
  local src = rd24(dp + 0x09)
  if src == 0 then return end
  local key = string.format("%s:%06X", tag, src)
  if seenSrc[key] then return end
  seenSrc[key] = true
  local ids = {}
  for i = 0, 95 do
    local v = rd16(src + i*2)
    if v == 0xFFFF then break end
    ids[#ids+1] = string.format("%04X", v)
    if v < 0x0800 then seenId[v] = true end
  end
  logline(string.format("[%s] SRC=$%06X f=%d  ids: %s", tag, src, frame, table.concat(ids, " ")))
end

local function onRom()  onString("ROM $87") end   -- $80:F4A7
local function onDial() onString("DIAL 7F") end    -- $80:F4CA
local function onFrame() frame = frame + 1 end

logline("=== chaînes d'IDs 16-bit (F4A7 ROM + F4CA dialogue) ===")
logline("Log: "..LOG_PATH)
emu.addMemoryCallback(onRom,  CB.exec, 0x80F4A7, 0x80F4A7)
emu.addMemoryCallback(onDial, CB.exec, 0x80F4CA, 0x80F4CA)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Actif. Avancer le dialogue pré-combat + la banderole STAGE START.")
