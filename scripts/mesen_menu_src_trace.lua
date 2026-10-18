--[[
  Nage Libre — capture du POINTEUR SOURCE [$09] du moteur de texte $80:F8DC.

  Le menu de combat est dessiné par le moteur commun $80:F8DC, qui lit un flux
  de glyphes compressés via le pointeur 24-bit en page directe $09/$0A/$0B.
  Ce script logue, pour CHAQUE entrée du moteur, l'adresse source (dédupliquée),
  le pointeur destination $06/$07/$08 (buffer police) et un aperçu des octets
  source. Le menu apparaîtra comme une entrée distincte (dest dans $7E:2000+).

  Usage :
    1. nl-full-en.sfc, entrer en combat, AVANT d'ouvrir le menu COMMAND.
    2. Script Window → Load → ce fichier → Run.
    3. Ouvrir le menu de commandes (puis le refermer/rouvrir une fois).
    4. M'envoyer  mesen_dumps/menu_src_trace.log

  (Exec callback : emu.getState() y fonctionne, contrairement aux write cb.)
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/menu_src_trace.log"
local CB  = emu.callbackType or emu.memCallbackType
local MEM = emu.memType.snesMemory or emu.memType.cpuDebug

local fileHandle = io.open(LOG_PATH, "w")
local seen = {}
local frame = 0
local count = 0
local MAX = 400

local function logline(s)
  if fileHandle then fileHandle:write(s.."\n"); fileHandle:flush() end
  if emu.log then emu.log(s) end
end

local function rd(addr) return emu.read(addr, MEM) & 0xFF end
local function rd24(a) return rd(a) | (rd(a+1)<<8) | (rd(a+2)<<16) end

-- Entrée du moteur de texte : $80:F8DC
local function onEnter()
  if fileHandle == nil then return end
  local st = emu.getState()
  local dp = (st and st.cpu and st.cpu.d) or 0
  local src = rd24(dp + 0x09)            -- pointeur source [$09]
  local dst = rd24(dp + 0x06)            -- pointeur dest   [$06]
  local key = string.format("%06X", src)
  if seen[key] then return end
  seen[key] = true
  -- aperçu : 12 octets à la source (banque:adresse 24-bit → lecture bus)
  local preview = {}
  for i = 0, 11 do preview[#preview+1] = string.format("%02X", rd(src + i)) end
  logline(string.format("SRC=$%06X  DST=$%06X  DP=$%04X  f=%d  bytes: %s",
    src, dst, dp, frame, table.concat(preview, " ")))
  count = count + 1
  if count >= MAX and fileHandle then
    logline("=== MAX entrées ==="); fileHandle:close(); fileHandle = nil
  end
end

local function onFrame() frame = frame + 1 end

logline("=== capture source [$09] moteur $80:F8DC ===")
logline("Log: "..LOG_PATH)
emu.addMemoryCallback(onEnter, CB.exec, 0x80F8DC, 0x80F8DC)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Actif. Ouvrir/fermer le menu COMMAND, puis m'envoyer le log.")
