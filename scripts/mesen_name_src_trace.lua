--[[
  Nage Libre — capture des POINTEURS SOURCE des chaînes rendues par $80:F4A7.

  $80:F4A7 → F4AB lit une chaîne d'IDs 16-bit via le pointeur 24-bit en page
  directe $09/$0A/$0B (fin = $FFFF). L'écran d'anniversaire (driver $87:EA20)
  affiche le NOM du personnage, la DATE (mois/jour) et la PIERRE via ce moteur.

  Ce script logue, pour chaque entrée du moteur, l'adresse source (dédupliquée)
  et un aperçu des IDs 16-bit (jusqu'au $FFFF). Les noms apparaîtront comme des
  chaînes de kanji (IDs élevés) à des offsets banque $87.

  Usage :
    1. nl-full-en.sfc, aller jusqu'à l'écran d'anniversaire (sélection perso).
    2. Script Window → Load → ce fichier → Run.
    3. Faire défiler les personnages (chaque portrait/nom), puis valider l'écran
       de confirmation. M'envoyer  mesen_dumps/name_src_trace.log
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/name_src_trace.log"
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
local function rd16(a) return rd(a) | (rd(a+1)<<8) end
local function rd24(a) return rd(a) | (rd(a+1)<<8) | (rd(a+2)<<16) end

-- $80:F4A7 — entrée du moteur typewriter ROM
local function onEnter()
  if fileHandle == nil then return end
  local st = emu.getState()
  local dp = (st and st.cpu and st.cpu.d) or 0
  local src = rd24(dp + 0x09)            -- pointeur source 24-bit [$09]
  local key = string.format("%06X", src)
  if seen[key] then return end
  seen[key] = true
  -- lire les IDs jusqu'au FFFF (max 24)
  local ids = {}
  for i = 0, 23 do
    local w = rd16(src + i*2)
    if w == 0xFFFF then break end
    ids[#ids+1] = string.format("%03X", w)
  end
  logline(string.format("SRC=$%06X  f=%d  n=%d  ids: %s",
    src, frame, #ids, table.concat(ids, " ")))
  count = count + 1
  if count >= MAX and fileHandle then
    logline("=== MAX ==="); fileHandle:close(); fileHandle = nil
  end
end

local function onFrame() frame = frame + 1 end

logline("=== capture source moteur $80:F4A7 (noms/dates/pierres) ===")
logline("Log: "..LOG_PATH)
emu.addMemoryCallback(onEnter, CB.exec, 0x80F4A7, 0x80F4A7)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Actif. Faire défiler les personnages sur l'écran d'anniversaire.")
