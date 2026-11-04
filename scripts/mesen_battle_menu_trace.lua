--[[
  Nage Libre — BATTLE MENU trace v2 (Mesen2)
  Goal: find the ROUTINE + the SOURCE that build the command menu.

  What we know (from the analysed VRAM/WRAM dumps):
    - The menu is on BG3 (VRAM tilemap word $7C00). The tilemap is first
      ASSEMBLED in a WRAM shadow buffer at $7E:4000+ (the menu lines are
      at $7E:406E+), then DMA'd to VRAM.
    - The command glyphs (待機/攻撃/…) are BATTLE FONT tiles
      assembled in a WRAM shadow buffer at $7E:2000+ (tile N at $7E:2000+N*16).
      The commands use tiles ~$90..$E4. These glyphs are COPIED from
      the main kanji font (ROM), so there is a source LIST (IDs /
      offsets) that drives the copy. That list is what we're looking for.

  Method:
    - We track the current PC through an exec callback (emu.getState() doesn't work
      inside a write callback on this Mesen2).
    - We log CPU writes to:
        * the font buffer        $7E:2100..$7E:2E50  (tiles $90..$E4)
        * the BG3 tilemap shadow $7E:4040..$7E:4280  (menu lines)
      with the PC, A/X/Y/DP/DB. The source pointer shows up in X or Y.

  Usage:
    1. Load nl-full-en.sfc, enter a battle, BEFORE opening the COMMAND menu.
    2. Script Window → Load → this file → Run.
    3. Open the command menu.
    4. Send me  mesen_dumps/battle_menu_trace.log

  Performance note: tracking the PC instruments every instruction → emulation may
  slow down. That's normal; opening the menu once is enough.
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/battle_menu_trace.log"
local MAX_LINES = 6000

local CB  = emu.callbackType or emu.memCallbackType

-- WRAM ranges (24-bit CPU bus addresses) to watch for writes.
local WATCH = {
  {0x7E2100, 0x7E2E50, "FONT"},   -- battle font buffer, tiles $90..$E4
  {0x7E4040, 0x7E4280, "MAP"},    -- BG3 tilemap shadow, menu window
}

local fileHandle = io.open(LOG_PATH, "w")
local lineCount = 0
local curPC = 0          -- updated on every instruction (cheap)
local frame = 0

local function logline(s)
  if fileHandle then fileHandle:write(s.."\n"); fileHandle:flush() end
  if emu.log then emu.log(s) end
end

local function stop()
  lineCount = lineCount + 1
  if lineCount >= MAX_LINES and fileHandle then
    logline(string.format("=== MAX_LINES (%d) — stopping ===", MAX_LINES))
    fileHandle:close(); fileHandle = nil
  end
end

-- PC tracking: exec over the whole address space. We ONLY store the address
-- (no emu.getState() here, otherwise emulation slows to a crawl).
local function onExec(addr)
  curPC = addr
end

local function mkWriteCb(tag)
  return function(addr, value)
    if fileHandle == nil then return end
    -- emu.getState() can return an empty state in a write cb on this Mesen2;
    -- we try anyway, to get X/Y (= source pointer) if possible.
    local x, y, a = -1, -1, -1
    local st = emu.getState()
    if st and st.cpu then a = st.cpu.a or -1; x = st.cpu.x or -1; y = st.cpu.y or -1 end
    logline(string.format(
      "%s w $%06X = $%02X   PC=$%06X A=%04X X=%04X Y=%04X f=%d",
      tag, addr, value & 0xFF, curPC, a & 0xFFFF, x & 0xFFFF, y & 0xFFFF, frame))
    stop()
  end
end

local function onFrame() frame = frame + 1 end

logline("=== Nage Libre — BATTLE MENU trace v2 ===")
logline("Log: "..LOG_PATH)

-- global exec to capture the PC (emu.getState works here, not in a write cb)
emu.addMemoryCallback(onExec, CB.exec, 0x000000, 0xFFFFFF)

for _, w in ipairs(WATCH) do
  emu.addMemoryCallback(mkWriteCb(w[3]), CB.write, w[1], w[2])
  logline(string.format("  watch write %s  $%06X..$%06X", w[3], w[1], w[2]))
end
emu.addEventCallback(onFrame, emu.eventType.startFrame)

logline("Active. Open the COMMAND menu, then send me the log.")
