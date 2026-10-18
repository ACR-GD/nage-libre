--[[
  Nage Libre — sonde du HOOK menu de combat ($80:FA80, détourné depuis $80:F902).

  Vérifie, à l'exécution, pourquoi le menu n'est pas traduit :
    1. Le hook $80:FA80 s'exécute-t-il quand le menu est ouvert ?
    2. La signature matche-t-elle ?  ($7E:2104 == $3718  ET  $7E:2356 == $7E01)
    3. Après la copie (RTS @ $80:FDB8), le buffer de tuile $7E:2100 (待→W)
       contient-il bien le bitmap de 'W' (00 00 63 00 63 00 ...) ?

  Usage :
    1. nl-full-en.sfc, entrer en COMBAT.
    2. Script Window → Load → ce fichier → Run.
    3. Ouvrir le menu de COMMANDES (待機/攻撃/...). Laisser 1-2 s, refermer.
    4. M'envoyer  mesen_dumps/hook_probe.log
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/hook_probe.log"
local CB  = emu.callbackType or emu.memCallbackType
local WRAM = emu.memType.snesWorkRam        -- 0-based, $7E:xxxx = offset xxxx

local HOOK_ENTRY = 0x80FA80
local HOOK_RTS   = 0x80FDE8                  -- dernier octet (RTS) du hook

local fileHandle = io.open(LOG_PATH, "w")
local frame = 0
local entryCount = 0
local matchCount = 0
local MAX_LOG = 80
local logged = 0

local function logline(s)
  if fileHandle then fileHandle:write(s.."\n"); fileHandle:flush() end
  if emu.log then emu.log(s) end
end

local function w8(off)  return emu.read(off, WRAM) & 0xFF end
local function w16(off) return w8(off) | (w8(off+1)<<8) end
local function hexbytes(off, n)
  local t = {}
  for i = 0, n-1 do t[#t+1] = string.format("%02X", w8(off+i)) end
  return table.concat(t, " ")
end

-- Entrée du hook : juste après reconstruction du buffer, avant copie.
local function onEntry()
  if fileHandle == nil then return end
  entryCount = entryCount + 1
  local sigA = w16(0x2104)
  local sigB = w16(0x2356)
  local match = (sigA == 0x3718) and (sigB == 0x7E01)
  if match then matchCount = matchCount + 1 end
  if logged < MAX_LOG then
    logged = logged + 1
    logline(string.format(
      "ENTRY f=%d  $7E2104=%04X  $7E2356=%04X  match=%s  tile90[pre]=%s",
      frame, sigA, sigB, tostring(match), hexbytes(0x2100, 8)))
  end
end

-- Sortie du hook (RTS) : après copie (si signature avait matché).
local function onRts()
  if fileHandle == nil then return end
  if matchCount > 0 and logged < MAX_LOG then
    logged = logged + 1
    logline(string.format(
      "RTS   f=%d  tile90[post $7E2100]=%s  tileB5[post $7E2350]=%s",
      frame, hexbytes(0x2100, 16), hexbytes(0x2350, 16)))
  end
end

local function onFrame() frame = frame + 1 end

logline("=== sonde HOOK menu de combat ($80:FA80) ===")
logline("Log: "..LOG_PATH)
logline("Cible : 'W' attendu @ $7E:2100 = 00 00 63 00 63 00 63 00 6B 00 7F 00 77 00 63 00")
emu.addMemoryCallback(onEntry, CB.exec, HOOK_ENTRY, HOOK_ENTRY)
emu.addMemoryCallback(onRts,   CB.exec, HOOK_RTS,   HOOK_RTS)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Actif. Ouvrir le menu COMMAND ~2s, puis m'envoyer le log.")
