--[[
  Nage Libre — capture of the 16-bit ID STRINGS rendered on screen.

  The typewriter loops read a string of 16-bit IDs (terminated by $FFFF) through the
  24-bit pointer [$09]/$0A/$0B, then draw each glyph with $80:F433:
    • $80:F4A7  : strings in ROM (bank $87: battle, menus, banners…)
    • $80:F4CA  : dialogue decompressed to $7F:64C0 (narration / pre-battle)

  For EACH string (deduplicated by source address) we log the full list
  of its IDs. IDs < $0800 are font glyphs: those are the ones the
  English pair allocator must NOT overwrite. I'll cross-check these IDs with
  our pairs to reserve exactly the Japanese glyphs that collide.

  Usage:
    1. nl-full-en.sfc, get to JUST BEFORE the pre-battle scene.
    2. Debug → Script Window → Load → this file → Run.
    3. Trigger NEW text: advance through the whole pre-battle dialogue +
       the "STAGE 1 START" banner + the victory condition.
    4. Send me  mesen_dumps/glyph_ids.log
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

logline("=== 16-bit ID strings (F4A7 ROM + F4CA dialogue) ===")
logline("Log: "..LOG_PATH)
emu.addMemoryCallback(onRom,  CB.exec, 0x80F4A7, 0x80F4A7)
emu.addMemoryCallback(onDial, CB.exec, 0x80F4CA, 0x80F4CA)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Active. Advance the pre-battle dialogue + the STAGE START banner.")
