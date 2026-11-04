--[[
  Nage Libre — capture of the SOURCE POINTERS of the strings rendered by $80:F4A7.

  $80:F4A7 → F4AB reads a string of 16-bit IDs through the 24-bit direct-page
  pointer $09/$0A/$0B (end = $FFFF). The birthday screen (driver $87:EA20)
  shows the character's NAME, the DATE (month/day) and the BIRTHSTONE through this engine.

  For each entry into the engine, this script logs the source address (deduplicated)
  and a preview of the 16-bit IDs (up to the $FFFF). The names will show up as
  kanji strings (high IDs) at bank $87 offsets.

  Usage:
    1. nl-full-en.sfc, go to the birthday screen (character selection).
    2. Script Window → Load → this file → Run.
    3. Scroll through the characters (each portrait/name), then confirm the
       confirmation screen. Send me  mesen_dumps/name_src_trace.log
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

-- $80:F4A7 — entry of the ROM typewriter engine
local function onEnter()
  if fileHandle == nil then return end
  local st = emu.getState()
  local dp = (st and st.cpu and st.cpu.d) or 0
  local src = rd24(dp + 0x09)            -- 24-bit source pointer [$09]
  local key = string.format("%06X", src)
  if seen[key] then return end
  seen[key] = true
  -- read the IDs up to the FFFF (max 24)
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

logline("=== $80:F4A7 engine source capture (names/dates/birthstones) ===")
logline("Log: "..LOG_PATH)
emu.addMemoryCallback(onEnter, CB.exec, 0x80F4A7, 0x80F4A7)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Active. Scroll through the characters on the birthday screen.")
