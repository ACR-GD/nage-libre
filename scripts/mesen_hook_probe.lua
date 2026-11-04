--[[
  Nage Libre — probe for the battle menu HOOK ($80:FA80, redirected from $80:F902).

  Checks at run time why the menu isn't translated:
    1. Does the $80:FA80 hook run when the menu is open?
    2. Does the signature match?  ($7E:2104 == $3718  AND  $7E:2356 == $7E01)
    3. After the copy (RTS @ $80:FDB8), does the tile buffer $7E:2100 (待→W)
       really hold the 'W' bitmap (00 00 63 00 63 00 ...)?

  Usage:
    1. nl-full-en.sfc, enter a BATTLE.
    2. Script Window → Load → this file → Run.
    3. Open the COMMAND menu (待機/攻撃/...). Wait 1-2 s, close it.
    4. Send me  mesen_dumps/hook_probe.log
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/hook_probe.log"
local CB  = emu.callbackType or emu.memCallbackType
local WRAM = emu.memType.snesWorkRam        -- 0-based, $7E:xxxx = offset xxxx

local HOOK_ENTRY = 0x80FA80
local HOOK_RTS   = 0x80FDE8                  -- last byte (RTS) of the hook

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

-- Hook entry: right after the buffer is rebuilt, before the copy.
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

-- Hook exit (RTS): after the copy (if the signature matched).
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

logline("=== battle menu HOOK probe ($80:FA80) ===")
logline("Log: "..LOG_PATH)
logline("Target: 'W' expected @ $7E:2100 = 00 00 63 00 63 00 63 00 6B 00 7F 00 77 00 63 00")
emu.addMemoryCallback(onEntry, CB.exec, HOOK_ENTRY, HOOK_ENTRY)
emu.addMemoryCallback(onRts,   CB.exec, HOOK_RTS,   HOOK_RTS)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Active. Open the COMMAND menu for ~2s, then send me the log.")
