--[[
  Nage Libre — capture of the SOURCE POINTER [$09] of the $80:F8DC text engine.

  The battle menu is drawn by the shared engine $80:F8DC, which reads a stream
  of compressed glyphs through the 24-bit direct-page pointer $09/$0A/$0B.
  For EACH entry into the engine, this script logs the source address (deduplicated),
  the destination pointer $06/$07/$08 (font buffer) and a preview of the source
  bytes. The menu will show up as a separate entry (dest in $7E:2000+).

  Usage:
    1. nl-full-en.sfc, enter a battle, BEFORE opening the COMMAND menu.
    2. Script Window → Load → this file → Run.
    3. Open the command menu (then close/reopen it once).
    4. Send me  mesen_dumps/menu_src_trace.log

  (Exec callback: emu.getState() works there, unlike in write callbacks.)
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

-- Text engine entry: $80:F8DC
local function onEnter()
  if fileHandle == nil then return end
  local st = emu.getState()
  local dp = (st and st.cpu and st.cpu.d) or 0
  local src = rd24(dp + 0x09)            -- source pointer [$09]
  local dst = rd24(dp + 0x06)            -- dest pointer   [$06]
  local key = string.format("%06X", src)
  if seen[key] then return end
  seen[key] = true
  -- preview: 12 bytes at the source (24-bit bank:address → bus read)
  local preview = {}
  for i = 0, 11 do preview[#preview+1] = string.format("%02X", rd(src + i)) end
  logline(string.format("SRC=$%06X  DST=$%06X  DP=$%04X  f=%d  bytes: %s",
    src, dst, dp, frame, table.concat(preview, " ")))
  count = count + 1
  if count >= MAX and fileHandle then
    logline("=== MAX entries ==="); fileHandle:close(); fileHandle = nil
  end
end

local function onFrame() frame = frame + 1 end

logline("=== $80:F8DC engine source [$09] capture ===")
logline("Log: "..LOG_PATH)
emu.addMemoryCallback(onEnter, CB.exec, 0x80F8DC, 0x80F8DC)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Active. Open/close the COMMAND menu, then send me the log.")
