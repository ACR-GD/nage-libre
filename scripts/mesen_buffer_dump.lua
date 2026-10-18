--[[
  Nage Libre — dump de l'en-tête du buffer script $7F:64C0 (scène pré-combat).

  Le buffer est déjà chargé quand on est dans la scène. On dumpe une fois
  $7F:64C0 .. $7F:6700 (en-tête d'opcodes + début des chaînes) pour choisir une
  SIGNATURE de garde stable (comme $64C8/$64D4 pour le prologue).

  Usage :
    1. nl-full-en.sfc, ÊTRE DANS la scène pré-combat (dialogue/banderole visible).
    2. Script Window → Load → ce fichier → Run.
    3. M'envoyer  mesen_dumps/precombat_buffer.log  (dump après ~30 frames).
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/precombat_buffer.log"
local MEM = emu.memType.snesMemory or emu.memType.cpuDebug
local fileHandle = io.open(LOG_PATH, "w")
local frame = 0
local dumped = false

local function rd(a) return emu.read(a, MEM) & 0xFF end

local function onFrame()
  frame = frame + 1
  if dumped or frame < 30 then return end
  dumped = true
  fileHandle:write("=== $7F:64C0 .. $7F:6700 (mots 16-bit little-endian) ===\n")
  for base = 0x7F64C0, 0x7F66FF, 16 do
    local words = {}
    for i = 0, 14, 2 do
      words[#words+1] = string.format("%04X", rd(base+i) | (rd(base+i+1)<<8))
    end
    fileHandle:write(string.format("+%04X: %s\n", base - 0x7F64C0, table.concat(words, " ")))
  end
  fileHandle:flush(); fileHandle:close(); fileHandle = nil
  if emu.log then emu.log("dump fait : "..LOG_PATH) end
end

emu.addEventCallback(onFrame, emu.eventType.startFrame)
if emu.log then emu.log("Actif. Dump du buffer dans ~30 frames.") end
