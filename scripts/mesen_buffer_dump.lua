--[[
  Nage Libre — dump of the header of the $7F:64C0 script buffer (pre-battle scene).

  The buffer is already loaded once you're in the scene. We dump
  $7F:64C0 .. $7F:6700 once (opcode header + start of the strings) to pick a
  stable guard SIGNATURE (like $64C8/$64D4 for the prologue).

  Usage:
    1. nl-full-en.sfc, BE IN the pre-battle scene (dialogue/banner visible).
    2. Script Window → Load → this file → Run.
    3. Send me  mesen_dumps/precombat_buffer.log  (dumped after ~30 frames).
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
  fileHandle:write("=== $7F:64C0 .. $7F:6700 (16-bit little-endian words) ===\n")
  for base = 0x7F64C0, 0x7F66FF, 16 do
    local words = {}
    for i = 0, 14, 2 do
      words[#words+1] = string.format("%04X", rd(base+i) | (rd(base+i+1)<<8))
    end
    fileHandle:write(string.format("+%04X: %s\n", base - 0x7F64C0, table.concat(words, " ")))
  end
  fileHandle:flush(); fileHandle:close(); fileHandle = nil
  if emu.log then emu.log("dump done: "..LOG_PATH) end
end

emu.addEventCallback(onFrame, emu.eventType.startFrame)
if emu.log then emu.log("Active. Buffer dump in ~30 frames.") end
