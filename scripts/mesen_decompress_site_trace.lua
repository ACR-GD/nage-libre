--[[
  Nage Libre — when/how the pre-battle scene gets into $7F:64C0.

  1) Probes EVERY frame the 2 guard offsets of the pre-battle scene:
        $7F:6636 (expected $0214 = 勝)   and   $7F:65DC (expected $032E = 問).
     Logs every change → shows the exact moment the battle script
     fills the buffer, and the value the hook's guard would see.
  2) Logs every $80:F8D8 call whose DEST = $7F:64C0 (no dedup) + the caller.
  3) Counts the passes through $83:80FF (prologue/hook path).

  Usage:
    1. nl-full-en.sfc, just before the pre-battle scene.
    2. Script Window → Load → this file → Run.
    3. Play the WHOLE scene until the Japanese dialogue + the banner show.
    4. Send me  mesen_dumps/decompress_site.log
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/decompress_site.log"
local CB  = emu.callbackType or emu.memCallbackType
local MEM = emu.memType.snesMemory or emu.memType.cpuDebug

local fileHandle = io.open(LOG_PATH, "w")
local frame = 0
local hits80FF = 0
local last1, last2 = -1, -1

local function logline(s)
  if fileHandle then fileHandle:write(s.."\n"); fileHandle:flush() end
  if emu.log then emu.log(s) end
end

local function rd(a) return emu.read(a, MEM) & 0xFF end
local function rd16(a) return rd(a) | (rd(a+1)<<8) end
local function rd24(a) return rd(a) | (rd(a+1)<<8) | (rd(a+2)<<16) end

local function onF8D8()
  if fileHandle == nil then return end
  local st = emu.getState()
  local dp = (st and st.cpu and st.cpu.d) or 0
  local dest = rd24(dp + 0x06)
  if dest == 0x7F64C0 then
    local sp = (st and st.cpu and (st.cpu.sp or st.cpu.s)) or 0
    local caller = ((rd(sp+3)<<16) | (rd(sp+2)<<8) | rd(sp+1)) + 1
    logline(string.format(">> F8D8 DEST=$7F64C0  caller~$%06X  f=%d", caller, frame))
  end
end

local function on80FF()
  hits80FF = hits80FF + 1
  logline(string.format("   [$83:80FF] #%d  f=%d", hits80FF, frame))
end

local function onFrame()
  frame = frame + 1
  if fileHandle == nil then return end
  local w1 = rd16(0x7F6636)
  local w2 = rd16(0x7F65DC)
  if w1 ~= last1 or w2 ~= last2 then
    last1, last2 = w1, w2
    local m = (w1 == 0x0214 and w2 == 0x032E) and "  <== GUARD MATCH" or ""
    logline(string.format("buffer change f=%d : $6636=%04X  $65DC=%04X%s", frame, w1, w2, m))
  end
end

logline("=== pre-battle guard probe + $7F64C0 sites ===")
emu.addMemoryCallback(onF8D8, CB.exec, 0x80F8D8, 0x80F8D8)
emu.addMemoryCallback(on80FF, CB.exec, 0x8380FF, 0x8380FF)
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Active. Play until the Japanese dialogue + banner.")
