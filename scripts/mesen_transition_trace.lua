--[[
  Nage Libre — traceur de la transition narration → UI (bug de fin de prologue)
  Pour Mesen-S / Mesen2 (SNES).

  But : localiser PRÉCISÉMENT où le prologue se fige après l'écran 24.
  Méthode :
    1. Logue chaque passage aux points clés du hand-off (séquenceur → driver → boucle → DCCB).
    2. Échantillonne le PC à chaque frame : quand l'image se fige, le PC qui se répète
       révèle la boucle d'attente exacte (= la cause du freeze).

  Usage :
    1. Charger la ROM (nl-prologue-en.sfc), aller jusqu'au prologue.
    2. Tools → Script Window → Load Script → scripts/mesen_transition_trace.lua → Run.
    3. Laisser tourner jusqu'au freeze (écran 24 → boîte vide).
    4. Lire le log : la DERNIÈRE étape « REACHED » atteinte + le PC répété en fin de fichier.
    5. M'envoyer le fichier  mesen_dumps/transition_trace.log

  Aucune pause/breakpoint manuel requis.
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/transition_trace.log"

-- Points clés de la chaîne narration → UI (adresses CPU 24-bit)
local STEPS = {
  {0x008380D7, "NARRATION entry ($83:80D7) — lance une scène"},
  {0x008383E5, "NARRATION END   ($83:83E5) — script terminé (FFFF)"},
  {0x00809626, "SEQ scene $0136  ($80:9626)"},
  {0x0080963A, "SEQ scene $0138  ($80:963A)"},
  {0x00809390, "SEQ pre-D63B     ($80:9390  JSR $9B20)"},
  {0x00809393, "SEQ → D63B       ($80:9393  JSL $87D63B)"},
  {0x0087D63B, "DRIVER entry     ($87:D63B)"},
  {0x0087D6C0, "BIRTHDAY act     ($87:D6C0  JSR D70C)"},
  {0x0087D70C, "LOOP body        ($87:D70C)"},
  {0x0087D756, "WAIT input       ($87:D756  LDA $0214)"},
  {0x0087D6D4, "→ DCCB           ($87:D6D4  JSR DCCB)"},
  {0x0087DCCB, "TRANSITION       ($87:DCCB) — sortie prologue"},
}

-- Échantillonnage PC : 1 log toutes les N frames
local HEARTBEAT_FRAMES = 20

-- ── état ────────────────────────────────────────────────────────────────────
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
  -- variables d'état utiles au diagnostic
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
  -- regrouper le PC par tranche de 0x20 pour détecter une boucle de spin
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
logline("=== Nage Libre — trace transition narration → UI ===")
logline("Log: " .. LOG_PATH)
for _, s in ipairs(STEPS) do
  emu.addMemoryCallback(onStep, emu.memCallbackType.exec, s[1], s[1])
  logline(string.format("  watch $%06X  %s", s[1], s[2]))
end
emu.addEventCallback(onFrame, emu.eventType.startFrame)
logline("Traceur actif. Jouer jusqu'au freeze, puis m'envoyer le log.")
