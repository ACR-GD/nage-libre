--[[
  Nage Libre — tracer for the narration → UI transition (end-of-prologue bug)
  For Mesen-S / Mesen2 (SNES).

  Goal: locate EXACTLY where the prologue freezes after screen 24.
  Method:
    1. Logs each pass through the key points of the hand-off (sequencer → driver → loop → DCCB).
    2. Samples the PC every frame: when the picture freezes, the PC that repeats
       reveals the exact wait loop (= the cause of the freeze).

  Usage:
    1. Load the ROM (nl-prologue-en.sfc), go up to the prologue.
    2. Tools → Script Window → Load Script → scripts/mesen_transition_trace.lua → Run.
    3. Let it run until the freeze (screen 24 → empty box).
    4. Read the log: the LAST "REACHED" step + the repeated PC at the end of the file.
    5. Send me the file  mesen_dumps/transition_trace.log

  No manual pause/breakpoint needed.
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/transition_trace.log"

-- Key points of the narration → UI chain (24-bit CPU addresses)
local STEPS = {
  {0x008380D7, "NARRATION entry ($83:80D7) — starts a scene"},
  {0x008383E5, "NARRATION END   ($83:83E5) — script finished (FFFF)"},
  {0x00809626, "SEQ scene $0136  ($80:9626)"},
  {0x0080963A, "SEQ scene $0138  ($80:963A)"},
  {0x00809390, "SEQ pre-D63B     ($80:9390  JSR $9B20)"},
  {0x00809393, "SEQ → D63B       ($80:9393  JSL $87D63B)"},
  {0x0087D63B, "DRIVER entry     ($87:D63B)"},
  {0x0087D6C0, "BIRTHDAY act     ($87:D6C0  JSR D70C)"},
  {0x0087D70C, "LOOP body        ($87:D70C)"},
  {0x0087D756, "WAIT input       ($87:D756  LDA $0214)"},
  {0x0087D6D4, "→ DCCB           ($87:D6D4  JSR DCCB)"},
  {0x0087DCCB, "TRANSITION       ($87:DCCB) — prologue exit"},
}

-- PC sampling: 1 log line every N frames
local HEARTBEAT_FRAMES = 20

-- ── state ────────────────────────────────────────────────────────────────────
local MEM = emu.memType.cpuDebug
local hitCount = {}
local fileHandle = io.open(LOG_PATH, "w")
local frame = 0
local lastPcKey = nil
local lastPcRepeat = 0

local function logline(s)
  if fileHandle then
    fileHandle:write(s .. "\n")
    fileHandle:flush()
  end
  if emu.log then emu.log(s) end
end

local function rd16(addr)
  return emu.read(addr, MEM) + emu.read(addr + 1, MEM) * 256
end

local function cpuField(state, name)
  if state.cpu and state.cpu[name] ~= nil then return state.cpu[name] end
  if state[name] ~= nil then return state[name] end
  return nil
end

local function pcOf(state)
  local pc = cpuField(state, "pc") or 0
  local k = cpuField(state, "k") or cpuField(state, "pb") or cpuField(state, "bank") or 0
  return (k * 65536) + (pc % 65536),
         cpuField(state, "a") or 0,
         cpuField(state, "x") or 0
end

local function snapshot()
  -- state variables useful for diagnosis
  return string.format("frame=%d  $1156=%04X  $0214=%04X  $17D6=%04X  $0006=%04X",
    frame, rd16(0x001156), rd16(0x000214), rd16(0x0017D6), rd16(0x000006))
end

local function onStep(address)
  for _, s in ipairs(STEPS) do
    if address == s[1] then
      hitCount[address] = (hitCount[address] or 0) + 1
      logline(string.format("REACHED #%d  %s   [%s]",
        hitCount[address], s[2], snapshot()))
      return
    end
  end
end

local function onFrame()
  frame = frame + 1
  if frame % HEARTBEAT_FRAMES ~= 0 then return end
  local state = emu.getState()
  local pc, a, x = pcOf(state)
  -- group the PC into 0x20 slices to detect a spin loop
  local key = pc - (pc % 32)
  if key == lastPcKey then
    lastPcRepeat = lastPcRepeat + 1
  else
    lastPcKey = key
    lastPcRepeat = 0
  end
  logline(string.format("PC=$%06X  A=%04X X=%04X  spin=%d   [%s]",
    pc, a, x, lastPcRepeat, snapshot()))
end

-- ── init ──────────────────────────────────────────────────────────────────
logline("=== Nage Libre — narration → UI transition trace ===")
logline("Log: " .. LOG_PATH)
for _, s in ipairs(STEPS) do
  emu.addMemoryCallback(onStep, emu.memCallbackType.exec, s[1], s[1])
  logline(string.format("  watch $%06X  %s", s[1], s[2]))
end
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Tracer active. Play until the freeze, then send me the log.")
